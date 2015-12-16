# Copyright 2015 Google Inc. All Rights Reserved.

"""Diagnose cluster command."""

from googlecloudsdk.api_lib.dataproc import storage_helpers
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base.py import encoding
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


class Diagnose(base.Command):
  """Run a detailed diagnostic on a cluster."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'name',
        help='The name of the cluster to diagnose.')

  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    cluster_ref = util.ParseCluster(args.name, self.context)

    request = messages.DataprocProjectsClustersDiagnoseRequest(
        clusterName=cluster_ref.clusterName,
        projectId=cluster_ref.projectId)

    try:
      operation = client.projects_clusters.Diagnose(request)
      operation = util.WaitForOperation(
          operation, self.context,
          message='Waiting for cluster diagnose operation')
      response = operation.response
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.FormatHttpError(error))

    if not response:
      raise exceptions.ToolException('Operation is missing response')

    properties = encoding.MessageToDict(response)
    output_uri = properties['outputUri']

    if not output_uri:
      raise exceptions.ToolException('Response is missing outputUri')

    log.err.Print('Output from diagnostic:')
    log.err.Print('-----------------------------------------------')
    driver_log_stream = storage_helpers.StorageObjectSeriesStream(
        output_uri)
    driver_log_stream.ReadIntoWritable(log.err)
    log.err.Print('-----------------------------------------------')
    return output_uri

  def Display(self, args, result):
    self.format(result)
