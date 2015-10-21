# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for cloud dataproc."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apis.dataproc.v1beta1 import dataproc_v1beta1_client
from googlecloudsdk.third_party.apis.dataproc.v1beta1 import dataproc_v1beta1_messages



@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Dataproc(base.Group):
  """Create and manage Google Cloud Dataproc clusters and jobs."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see how to create and manage clusters, run:

            $ {command} clusters

          To see how to submit and manage jobs, run:

            $ {command} jobs
          """,
  }

  def Filter(self, context, args):
    context['http'] = self.Http()
    context['dataproc_endpoint'] = (
        properties.VALUES.api_endpoint_overrides.dataproc.Get())
    context['dataproc_messages'] = dataproc_v1beta1_messages
    context['resources'] = resources

    context['dataproc_client'] = dataproc_v1beta1_client.DataprocV1beta1(
        get_credentials=False,
        http=context['http'],
        url=context['dataproc_endpoint'])

    resources.SetParamDefault(
        api='dataproc',
        collection=None,
        param='projectId',
        resolver=resolvers.FromProperty(properties.VALUES.core.project))

    return context
