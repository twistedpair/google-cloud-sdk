# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Error Reporting Handler."""

import sys
import traceback
import urllib
import urlparse

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.error_reporting import util
from googlecloudsdk.calliope import backend
from googlecloudsdk.command_lib import error_reporting_util
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import config
from googlecloudsdk.core import http
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_attr


def _IsInstallationCorruption(err):
  """Determines if the error may be from installation corruption.

  Args:
    err: Exception err.

  Returns:
    bool, True if installation error, False otherwise
  """
  return (isinstance(err, backend.CommandLoadFailure) and
          isinstance(err.root_exception, ImportError))


def _PrintInstallationAction(err, err_string):
  """Prompts installation error action.

  Args:
    err: Exception err.
    err_string: Exception err string.
  """
  # This usually indicates installation corruption.
  # We do want to suggest `gcloud components reinstall` here (ex. as opposed
  # to the similar message in gcloud.py), because there's a good chance it'll
  # work (rather than a manual reinstall).
  # Don't suggest `gcloud feedback`, because this is probably an
  # installation problem.
  log.error(
      ('gcloud failed to load ({0}): {1}\n\n'
       'This usually indicates corruption in your gcloud installation or '
       'problems with your Python interpreter.\n\n'
       'Please verify that the following is the path to a working Python 2.7 '
       'executable:\n'
       '    {2}\n'
       'If it is not, please set the CLOUDSDK_PYTHON environment variable to '
       'point to a working Python 2.7 executable.\n\n'
       'If you are still experiencing problems, please run the following '
       'command to reinstall:\n'
       '    $ gcloud components reinstall\n\n'
       'If that command fails, please reinstall the Cloud SDK using the '
       'instructions here:\n'
       '    https://cloud.google.com/sdk/'
      ).format(err.command, err_string, sys.executable))


CRASH_SERVICE = 'gcloud'
CRASH_PROJECT = 'cloud-sdk-errors'
CRASH_API_KEY = 'AIzaSyA45D7bA0Y1vyLmQ_Gl10G149M8jiwwK-s'


def _GetReportingClient():
  """Returns a client that uses an API key for Cloud SDK crash reports.

  Returns:
    An error reporting client that uses an API key for Cloud SDK crash reports.
  """
  http_client = http.Http()
  orig_request = http_client.request

  def RequestWithAPIKey(*args, **kwargs):
    """Wrap request for request/response logging.

    Args:
      *args: Positional arguments.
      **kwargs: Keyword arguments.

    Returns:
      Original returned response of this wrapped request.
    """
    # Modify request url to enable API key based authentication.
    url_parts = urlparse.urlsplit(args[0])
    query_params = urlparse.parse_qs(url_parts.query)
    query_params['key'] = CRASH_API_KEY

    modified_url_parts = list(url_parts)
    modified_url_parts[3] = urllib.urlencode(query_params, doseq=True)
    modified_args = list(args)
    modified_args[0] = urlparse.urlunsplit(modified_url_parts)

    return orig_request(*modified_args, **kwargs)

  http_client.request = RequestWithAPIKey

  client_class = core_apis.GetClientClass(util.API_NAME, util.API_VERSION)
  return client_class(get_credentials=False, http=http_client)


def _ReportCrash(err):
  """Report the anonymous crash information to the Error Reporting service.

  Args:
    err: Exception, the error that caused the crash.
  """
  stacktrace = traceback.format_exc(err)
  stacktrace = error_reporting_util.RemovePrivateInformationFromTraceback(
      stacktrace)
  command = properties.VALUES.metrics.command_name.Get()
  cid = metrics.GetCIDIfMetricsEnabled()

  client = _GetReportingClient()
  reporter = util.ErrorReporting(client)
  try:
    reporter.ReportEvent(error_message=stacktrace,
                         service=CRASH_SERVICE,
                         version=config.CLOUD_SDK_VERSION,
                         project=CRASH_PROJECT,
                         request_url=command,
                         user=cid)
  except apitools_exceptions.HttpError as http_err:
    log.file_only_logger.error(
        'Unable to report crash stacktrace:\n{0}'.format(
            console_attr.EncodeForOutput(http_err)))


def HandleGcloudCrash(err):
  """Checks if installation error occurred, then proceeds with Error Reporting.

  Args:
    err: Exception err.
  """
  err_string = console_attr.EncodeForOutput(err)
  log.file_only_logger.exception('BEGIN CRASH STACKTRACE')
  if _IsInstallationCorruption(err):
    _PrintInstallationAction(err, err_string)
  else:
    log.error(u'gcloud crashed ({0}): {1}'.format(
        getattr(err, 'error_name', type(err).__name__), err_string))
    if not properties.VALUES.core.disable_usage_reporting.GetBool():
      _ReportCrash(err)
    log.err.Print('\nIf you would like to report this issue, please run the '
                  'following command:')
    log.err.Print('  gcloud feedback')
    log.err.Print('\nTo check gcloud for common problems, please run the '
                  'following command:')
    log.err.Print('  gcloud info --run-diagnostics')
