# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow metrics tail command.
"""

from googlecloudsdk.api_lib.dataflow import dataflow_util
from googlecloudsdk.api_lib.dataflow import job_utils
from googlecloudsdk.api_lib.dataflow import time_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.surface import dataflow as commands
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Tail(base.Command):
  """Retrieves the metrics from a specific job.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    job_utils.ArgsForJobRef(parser)

    parser.add_argument(
        '--changed-after', type=time_util.ParseTimeArg,
        help='Only display metrics that have changed after the given time')
    parser.add_argument(
        '--hide-committed', default=False, action='store_true',
        help='If true, hide committed values.')
    parser.add_argument(
        '--tentative', default=False, action='store_true',
        help='If true, display tentative values.')

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: all the arguments that were provided to this command invocation.

    Returns:
      None on success, or a string containing the error message.
    """
    apitools_client = self.context[commands.DATAFLOW_APITOOLS_CLIENT_KEY]
    dataflow_messages = self.context[commands.DATAFLOW_MESSAGES_MODULE_KEY]
    job_ref = job_utils.ExtractJobRef(self.context, args)

    start_time = args.changed_after and time_util.Strftime(args.changed_after)
    request = dataflow_messages.DataflowProjectsJobsGetMetricsRequest(
        projectId=job_ref.projectId,
        jobId=job_ref.jobId,
        startTime=start_time)

    preds = []
    if not args.tentative and args.hide_committed:
      raise calliope_exceptions.ToolException(
          'Cannot exclude both tentative and committed metrics.')
    elif not args.tentative and not args.hide_committed:
      preds.append(lambda m: self._GetContextValue(m, 'tentative') != 'true')
    elif args.tentative and args.hide_committed:
      preds.append(lambda m: self._GetContextValue(m, 'tentative') == 'true')

    if args.changed_after:
      parsed_time = time_util.ParseTimeArg(args.changed_after)
      preds.append(lambda m: time_util.ParseTimeArg(m.updateTime) > parsed_time)

    try:
      response = apitools_client.projects_jobs.GetMetrics(request)
    except apitools_base.HttpError as error:
      raise calliope_exceptions.HttpException(
          'Failed to get metrics for job with ID [{0}] in project [{1}]: {2}'
          .format(job_ref.jobId, job_ref.projectId,
                  dataflow_util.GetErrorMessage(error)))

    return [m for m in response.metrics if all([pred(m) for pred in preds])]

  def _GetContextValue(self, metric, key):
    if metric.name.context:
      for prop in metric.name.context.additionalProperties:
        if prop.key == key:
          return prop.value
    return None

  def Display(self, args, metrics):
    """This method is called to print the result of the Run() method.

    Args:
      args: all the arguments that were provided to this command invocation.
      metrics: The JobMetrics returned from the Run() method.
    """
    self.format(metrics)
