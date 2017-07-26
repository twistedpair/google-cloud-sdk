# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A utility library to support interaction with the Tool Results service."""

import collections
import time
import urlparse

from googlecloudsdk.api_lib.firebase.test import exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import progress_tracker

import uritemplate


_STATUS_INTERVAL_SECS = 3


class ToolResultsIds(
    collections.namedtuple('ToolResultsIds', ['history_id', 'execution_id'])):
  """A tuple to hold the history & execution IDs returned from Tool Results.

  Fields:
    history_id: a string with the Tool Results history ID to publish to.
    execution_id: a string with the ID of the Tool Results execution.
  """


def CreateToolResultsUiUrl(project_id, tool_results_ids):
  """Create the URL for a test's Tool Results UI in the Firebase App Manager.

  Args:
    project_id: string containing the user's GCE project ID.
    tool_results_ids: a ToolResultsIds object holding history & execution IDs.

  Returns:
    A url to the Tool Results UI.
  """
  url_base = properties.VALUES.test.results_base_url.Get()
  if not url_base:
    url_base = 'https://console.firebase.google.com'

  url_end = uritemplate.expand(
      'project/{project}/testlab/histories/{history}/matrices/{execution}',
      {'project': project_id,
       'history': tool_results_ids.history_id,
       'execution': tool_results_ids.execution_id})
  return urlparse.urljoin(url_base, url_end)


def GetToolResultsIds(matrix, matrix_monitor,
                      status_interval=_STATUS_INTERVAL_SECS):
  """Gets the Tool Results history ID and execution ID for a test matrix.

  Sometimes the IDs are available immediately after a test matrix is created.
  If not, we keep checking the matrix until the Testing and Tool Results
  services have had enough time to create/assign the IDs, giving the user
  continuous feedback using gcloud core's ProgressTracker class.

  Args:
    matrix: a TestMatrix which was just created by the Testing service.
    matrix_monitor: a MatrixMonitor object.
    status_interval: float, number of seconds to sleep between status checks.

  Returns:
    A ToolResultsIds tuple containing the history ID and execution ID, which
    are shared by all TestExecutions in the TestMatrix.

  Raises:
    BadMatrixError: if the matrix finishes without both ToolResults IDs.
  """
  history_id = None
  execution_id = None
  msg = 'Creating individual test executions'
  with progress_tracker.ProgressTracker(msg, autotick=True):
    while True:
      if matrix.resultStorage.toolResultsExecution:
        history_id = matrix.resultStorage.toolResultsExecution.historyId
        execution_id = matrix.resultStorage.toolResultsExecution.executionId
        if history_id and execution_id:
          break

      if matrix.state in matrix_monitor.completed_matrix_states:
        raise exceptions.BadMatrixError(_ErrorFromInvalidMatrix(matrix))

      time.sleep(status_interval)
      matrix = matrix_monitor.GetTestMatrixStatus()

  return ToolResultsIds(history_id=history_id, execution_id=execution_id)


def _ErrorFromInvalidMatrix(matrix):
  """Produces a human-readable error message from an invalid matrix."""
  messages = apis.GetMessagesModule('testing', 'v1')
  enum_values = messages.TestMatrix.InvalidMatrixDetailsValueValuesEnum
  error_dict = {
      enum_values.MALFORMED_APK:
          'The app APK is not a valid Android application',
      enum_values.MALFORMED_TEST_APK:
          'The test APK is not a valid Android instrumentation test',
      enum_values.NO_MANIFEST:
          'The app APK is missing the manifest file',
      enum_values.NO_PACKAGE_NAME:
          'The APK manifest file is missing the package name',
      enum_values.TEST_SAME_AS_APP:
          'The test APK is the same as the app APK',
      enum_values.NO_INSTRUMENTATION:
          'The test APK declares no instrumentation tags in the manifest',
      enum_values.NO_LAUNCHER_ACTIVITY:
          'The app APK does not specify a main launcher activity',
      enum_values.FORBIDDEN_PERMISSIONS:
          'The app declares one or more permissions that are not allowed',
      enum_values.INVALID_ROBO_DIRECTIVES:
          'Cannot have multiple robo-directives with the same resource name',
      enum_values.TEST_LOOP_INTENT_FILTER_NOT_FOUND:
          'The app does not have a correctly formatted game-loop intent filter',
      enum_values.SCENARIO_LABEL_NOT_DECLARED:
          'A scenario-label was not declared in the manifest file',
      enum_values.SCENARIO_LABEL_MALFORMED:
          'A scenario-label in the manifest includes invalid numbers or ranges',
      enum_values.SCENARIO_NOT_DECLARED:
          'A scenario-number was not declared in the manifest file'
  }
  details_enum = matrix.invalidMatrixDetails
  if details_enum in error_dict:
    return ('\nMatrix [{m}] failed during validation: {e}.'.format(
        m=matrix.testMatrixId, e=error_dict[details_enum]))
  # Use a generic message if the enum is unknown or unspecified/unavailable.
  return (
      '\nMatrix [{m}] unexpectedly reached final status {s} without returning '
      'a URL to any test results in the Firebase console. Please re-check the '
      'validity of your APK file(s) and test parameters and try again.'.format(
          m=matrix.testMatrixId, s=matrix.state))
