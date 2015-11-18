# Copyright 2014 Google Inc. All Rights Reserved.

"""The 'gcloud test android run' command."""

import datetime
import os
import random
import string

from googlecloudsdk.api_lib.test import arg_util
from googlecloudsdk.api_lib.test import ctrl_c_handler
from googlecloudsdk.api_lib.test import exit_code
from googlecloudsdk.api_lib.test import history_picker
from googlecloudsdk.api_lib.test import matrix_ops
from googlecloudsdk.api_lib.test import results_bucket
from googlecloudsdk.api_lib.test import results_summary
from googlecloudsdk.api_lib.test import tool_results
from googlecloudsdk.api_lib.test import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Run(base.ListCommand):
  """Invoke an Android test in Google Cloud Test Lab and view test results."""

  detailed_help = {
      'DESCRIPTION': """\
          *{command}* invokes and monitors tests in Google Cloud Test Lab.

          Three main types of tests are currently supported:
          - *robo*: runs a smart, automated exploration of the activities in
            your Android app which records any installation failures or crashes
            and builds an activity map with associated screenshots and video.
          - *instrumentation*: runs automated unit or integration tests written
            using a testing framework. Google Cloud Test Lab initially supports
            the Espresso and Robotium testing frameworks for Android.
          - *monkey*: runs an Android UI/Application Exerciser Monkey test.

          The type of test to run can be specified with the *--type* flag,
          although the type can often be inferred from other flags.
          Specifically, if the *--test* flag is present, the test *--type* will
          default to `instrumentation`. If *--test* is not present, then
          *--type* defaults to `robo`.

          All arguments for *{command}* may be specified on the command line
          and/or within an argument file. Run *$ gcloud topic arg-files* for
          more information about argument files.
          """,

      'EXAMPLES': """\
          To invoke a robo test lasting 100 seconds against the default device
          environment, run:

            $ {command} --app APP_APK --timeout 100s

          To invoke a monkey test against a virtual Nexus9 device in
          landscape orientation, run:

            $ {command} --type monkey --app APP_APK --device-id Nexus9\
 --orientation landscape

          To invoke an instrumentation test (Espresso or Robotium) against a
          physical Nexus 4 device (DEVICE_ID: mako) which is running Android API
          level 18 in French, run:

            $ {command} --app APP_APK --test TEST_APK --device-id mako\
 --os-version-id 18 --locale fr --orientation portrait

          To run the same test as above using short flags, run:

            $ {command} -a APP_APK -t TEST_APK -d mako -v 18 -l fr -o portrait

          To run a series of 5-minute robo tests against a comprehensive matrix
          of virtual and physical devices, OS versions and locales, run:

            $ {command} --app APP_APK --timeout 5m\
 --device-ids mako,shamu,Nexus5,Nexus6,k3g --os-version-ids 17,18,19,21,22\
 --locales de,en_US,en_GB,es,fr,it,ru,zh

          To run an instrumentation test against the default test environment,
          but using a specific Google Cloud Storage bucket to hold the raw test
          results and specifying the name under which the history of your tests
          will be collected and displayed in the Google Developers Console, run:

            $ {command} -a APP_APK -t TEST_APK\
 --results-bucket excelsior-app-results-bucket\
 --results-history-name 'Excelsior App Test History'

          All test arguments for a given test may alternatively be stored in an
          argument group within a YAML-formatted argument file. The _ARG_FILE_
          may contain one or more named argument groups, and argument groups may
          be combined using the `include:` attribute (Run *$ gcloud topic
          arg-files* for more information). The ARG_FILE can easily be shared
          with colleagues or placed under source control to ensure consistent
          test executions.

          To run a test using arguments loaded from an ARG_FILE named
          *excelsior_args*, which contains an argument group named *robo-args:*,
          use the following syntax:

            $ {command} path/to/excelsior_args:robo-args
          """,
  }

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags for this command.

    Args:
      parser: An argparse parser used to add arguments that follow this
          command in the CLI. Positional arguments are allowed.
    """
    arg_util.AddCommonTestRunArgs(parser)
    arg_util.AddSharedCommandArgs(parser)
    arg_util.AddMatrixArgs(parser)
    arg_util.AddInstrumentationTestArgs(parser)
    arg_util.AddMonkeyTestArgs(parser)
    arg_util.AddRoboTestArgs(parser)

  def Run(self, args):
    """Run the 'gcloud test run' command to invoke a Google Cloud Test Lab test.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation (i.e. group and command arguments combined).

    Returns:
      One of:
        - a list of TestOutcome tuples (if ToolResults are available).
        - a URL string pointing to the user's results in ToolResults or GCS.
    """
    _EnsureUserAcceptsTermsOfService()
    arg_util.Prepare(args, util.GetAndroidCatalog(self.context))

    project = util.GetProject()
    tr_client = self.context['toolresults_client']
    tr_messages = self.context['toolresults_messages']
    storage_client = self.context['storage_client']

    # The Testing back-end needs a unique GCS object name within the results
    # bucket to prevent race conditions while processing test results. This
    # client uses the current time down to the microsecond in ISO format plus a
    # random 4-letter suffix. The format is: "YYYY-MM-DD_hh:mm:ss.ssssss_rrrr"
    unique_object = '{0}_{1}'.format(datetime.datetime.now().isoformat('_'),
                                     ''.join(random.sample(string.letters, 4)))
    bucket_ops = results_bucket.ResultsBucketOps(
        project, args.results_bucket, unique_object,
        tr_client, tr_messages, storage_client)
    bucket_ops.UploadFileToGcs(args.app)
    if args.test:
      bucket_ops.UploadFileToGcs(args.test)
    for obb_file in (args.obb_files or []):
      bucket_ops.UploadFileToGcs(obb_file)
    bucket_ops.LogGcsResultsUrl()

    tr_history_picker = history_picker.ToolResultsHistoryPicker(
        project, tr_client, tr_messages)
    history_id = tr_history_picker.FindToolResultsHistoryId(args)
    matrix = matrix_ops.CreateMatrix(
        args, self.context, history_id, bucket_ops.gcs_results_root)
    matrix_id = matrix.testMatrixId
    monitor = matrix_ops.MatrixMonitor(matrix_id, args.type, self.context)

    with ctrl_c_handler.CancellableTestSection(monitor):
      supported_executions = monitor.HandleUnsupportedExecutions(matrix)
      tr_ids = tool_results.GetToolResultsIds(matrix, monitor)

      url = tool_results.CreateToolResultsUiUrl(project, tr_ids)
      log.status.Print('')
      if args.async:
        return url
      log.status.Print('Test results will be streamed to [{0}].'.format(url))

      # If we have exactly one testExecution, show detailed progress info.
      if len(supported_executions) == 1:
        monitor.MonitorTestExecutionProgress(supported_executions[0].id)
      else:
        monitor.MonitorTestMatrixProgress()

    log.status.Print('\nMore details are available at [{0}].'.format(url))
    # Fetch the per-dimension test outcomes list, and also the "rolled-up"
    # matrix outcome from the Tool Results service.
    summary_fetcher = results_summary.ToolResultsSummaryFetcher(
        project, tr_client, tr_messages, tr_ids)
    self.exit_code = exit_code.ExitCodeFromRollupOutcome(
        summary_fetcher.FetchMatrixRollupOutcome(),
        tr_messages.Outcome.SummaryValueValuesEnum)
    return summary_fetcher.CreateMatrixOutcomeSummary()

  def Collection(self, args):
    """Choose the default resource collection key used to format test outcomes.

    Args:
      args: The arguments that command was run with.

    Returns:
      A collection string used as a key to select the default ResourceInfo
      from core.resources.resource_registry.RESOURCE_REGISTRY.
    """
    log.debug('gcloud test command exit_code is: {0}'.format(self.exit_code))
    return 'test.android.run.url' if args.async else 'test.android.run.outcomes'


def _EnsureUserAcceptsTermsOfService():
  """Don't allow GCTL tests to run until user accepts the Terms of Service."""
  tos_file = os.path.join(config.Paths().global_config_dir, 'GCTL_ToS_Accepted')
  if not os.path.isfile(tos_file):
    if properties.VALUES.core.disable_prompts.GetBool():
      log.error('Trusted Tester Agreement has not been accepted. Please run '
                'gcloud with prompts enabled to accept the Terms of Service.')
      raise console_io.OperationCancelledError()
    console_io.PromptContinue(
        message='The Google Cloud Platform Terms of Service notwithstanding, '
        'your use of Google Cloud Test Lab is governed by the Trusted Tester '
        'Agreement and by using Google Cloud Test Lab, you agree to its '
        'terms.\n\nTrusted Tester Agreement: https://goo.gl/K109WG',
        prompt_string='Proceed',
        default=False,
        throw_if_unattended=True,
        cancel_on_no=True)  # Abort unless user explicitly answers 'y'
    log.info('User has accepted Trusted Tester Agreement.')
    # Create an empty tos_file to mark user acceptance and avoid future prompts.
    open(tos_file, 'w').close()
