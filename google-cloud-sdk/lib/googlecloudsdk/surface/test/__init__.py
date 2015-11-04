# Copyright 2014 Google Inc. All Rights Reserved.

"""The main command group for gcloud test."""

import argparse

from googlecloudsdk.api_lib.test import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apis.storage import v1 as storage_v1
from googlecloudsdk.third_party.apis.testing import v1 as testing_v1
from googlecloudsdk.third_party.apis.toolresults import v1beta3 as toolresults_v1beta3


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Test(base.Group):
  """Interact with Google Cloud Test Lab.

  Explore devices and OS versions available as test targets, run tests, monitor
  test progress, and view detailed test results.
  """

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: {str:object}, The current context, which is a set of key-value
          pairs that can be used for common initialization among commands.
      args: argparse.Namespace: The same Namespace given to the corresponding
          .Run() invocation.

    Returns:
      The refined command context.
    """
    # Get service endpoints and ensure they are compatible with each other
    testing_url = properties.VALUES.api_endpoint_overrides.testing.Get()
    toolresults_url = properties.VALUES.api_endpoint_overrides.toolresults.Get()
    log.info('Test Service endpoint: [{0}]'.format(testing_url))
    log.info('Tool Results endpoint: [{0}]'.format(toolresults_url))
    if ((toolresults_url is None or 'apis.com/toolresults' in toolresults_url)
        != (testing_url is None or 'testing.googleapis' in testing_url)):
      raise exceptions.ToolException(
          'Service endpoints [{0}] and [{1}] are not compatible.'
          .format(testing_url, toolresults_url))

    http = self.Http()

    # Create the client for the Testing service.
    # TODO(pauldavis) Support multiple versions when they exist
    testing_client_v1 = testing_v1.TestingV1(
        get_credentials=False,
        url=testing_url,
        http=http)
    context['testing_client'] = testing_client_v1
    context['testing_messages'] = testing_v1

    # Create the client for the Tool Results service.
    toolresults_client_v1 = toolresults_v1beta3.ToolresultsV1beta3(
        get_credentials=False,
        url=toolresults_url,
        http=http)
    context['toolresults_client'] = toolresults_client_v1
    context['toolresults_messages'] = toolresults_v1beta3

    # Create the client for the Storage service.
    storage_client_v1 = storage_v1.StorageV1(get_credentials=False, http=http)
    context['storage_client'] = storage_client_v1

    # TODO(pauldavis): remove this message for general release.
    log.status.Print(
        '\nHave questions, feedback, or issues? Please let us know by using '
        'this Google Group:\n  https://groups.google.com/forum/#!forum'
        '/google-cloud-test-lab-external\n')

    return context
