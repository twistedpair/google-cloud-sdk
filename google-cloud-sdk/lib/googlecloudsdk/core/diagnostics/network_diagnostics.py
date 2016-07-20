# Copyright 2016 Google Inc. All Rights Reserved.
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

"""A module for diagnosing common network and proxy problems."""

import httplib
import socket
import ssl
import urlparse

from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import http
from googlecloudsdk.core.diagnostics import check_base
from googlecloudsdk.core.diagnostics import diagnostic_base
from googlecloudsdk.core.diagnostics import http_proxy_setup
import httplib2


class NetworkDiagnostic(diagnostic_base.Diagnostic):
  """Diagnose and fix local network connection issues."""

  def __init__(self):
    intro = ('Network diagnostic detects and fixes local network connection '
             'issues.')
    super(NetworkDiagnostic, self).__init__(
        intro=intro, title='Network diagnostic',
        checklist=[ReachabilityChecker()])


def DefaultUrls():
  """Returns a list of hosts whose reachability is essential for the Cloud SDK.

  Returns:
    list(str): The urls to check reachability for.
  """
  urls = ['http://www.google.com', 'https://www.google.com',
          'https://accounts.google.com',
          'https://cloudresourcemanager.googleapis.com/v1beta1/projects',
          'https://www.googleapis.com/auth/cloud-platform']

  download_urls = (properties.VALUES.component_manager.snapshot_url.Get() or
                   config.INSTALLATION_CONFIG.snapshot_url)
  if download_urls:
    for url in download_urls.split(','):
      url_scheme = urlparse.urlparse(url).scheme
      if url_scheme in ('http', 'https'):
        urls.append(url)
  return urls


class ReachabilityChecker(check_base.Checker):
  """Checks whether the hosts of given urls are reachable."""

  @property
  def issue(self):
    return 'network connection'

  def Check(self, urls=None, first_run=True):
    """Run reachability check.

    Args:
      urls: iterable(str), The list of urls to check connection to. Defaults to
        DefaultUrls() (above) if not supplied.
      first_run: bool, True if first time this has been run this invocation.

    Returns:
      check_base.CheckResult, Callable:  A tuple in which the first element is
        the result of the check and the second is a function that can be used to
        fix the error or None.
    """
    if urls is None:
      urls = DefaultUrls()

    failures = filter(None, [self._CheckURL(url) for url in urls])
    if failures:
      fail_message = self._ConstructMessageFromFailures(failures, first_run)
      result = check_base.CheckResult(passed=False, message=fail_message,
                                      failures=failures)
      fixer = http_proxy_setup.ChangeGcloudProxySettings
      return result, fixer

    pass_message = 'Reachability Check {0}.'.format('passed' if first_run else
                                                    'now passes')
    result = check_base.CheckResult(passed=True, message='No URLs to check.'
                                    if not urls else pass_message)
    return result, None

  def _CheckURL(self, url):
    try:
      _, _ = http.Http(auth=False).request(url, method='GET')
    # TODO(b/29218762): Investigate other possible exceptions.
    except (httplib.HTTPException, socket.error, ssl.SSLError,
            httplib2.HttpLib2Error) as err:
      msg = 'Cannot reach {0} ({1})'.format(url, type(err).__name__)
      return check_base.Failure(message=msg, exception=err)

  def _ConstructMessageFromFailures(self, failures, first_run):
    message = 'Reachability Check {0}.\n'.format('failed' if first_run else
                                                 'still does not pass')
    for failure in failures:
      message += '    {0}\n'.format(failure.message)
    if first_run:
      message += ('Network connection problems may be due to proxy or '
                  'firewall settings.\n')
    return message
