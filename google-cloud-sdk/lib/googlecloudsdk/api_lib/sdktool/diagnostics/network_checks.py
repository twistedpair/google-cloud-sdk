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

"""A library for diagnosing common network and proxy problems."""

import httplib
import socket
import ssl

from googlecloudsdk.core import http_proxy
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import http
from googlecloudsdk.core.util import http_proxy_types
import httplib2

# TODO(b/29217446): Investigate other URLs to check.
_DEFAULT_URLS_TO_CHECK = [
    'http://www.google.com',
    'https://www.google.com',
    'https://accounts.google.com',
    'https://cloudresourcemanager.googleapis.com/v1beta1/projects']


class Failure(object):
  """Result of a failed network diagnostic check."""

  def __init__(self, message='', exception=None, response=None):
    self.message = message
    self.exception = exception
    self.response = response


def DiagnoseNetworkConnection(urls=None):
  """Diagnose and fix local network connection issues.

  Checks reachability of passed in urls. If any are unreachable, asks user to
  change or update Cloud SDK proxy properties. If user makes proxy settings
  changes, then reachability check is run one more time.

  Args:
    urls: iterable(str), The list of urls to check connection to. Defaults to
      _DEFAULT_URLS_TO_CHECK (above).

  Returns:
    bool: Whether the network connection check ultimately passed.
  """
  if not urls:
    urls = _DEFAULT_URLS_TO_CHECK

  if _CheckNetworkConnection(urls, http.Http(auth=False), first_run=True):
    return True

  log.status.Print(
      'Network connection problems may be due to proxy or firewall settings.')
  while True:
    if not _ChangeGcloudProxySettings():
      return False
    if _CheckNetworkConnection(urls, http.Http(auth=False), first_run=False):
      return True


def _CheckNetworkConnection(urls, http_client, first_run=True):
  """Checks network connection to urls and prints status to console.

  Args:
    urls: iterable(str), The list of urls to check connection to.
    http_client: httplib2.Http, an object used by gcloud to make http and https
      connections.
    first_run: bool, Whether this is the first time checking network connections
      on this invocation. Affects the message presented to the user.

  Returns:
    bool: Whether the network connection check passed.
  """
  with console_io.ProgressTracker('{0} network connection'.format(
      'Checking' if first_run else 'Rechecking')):
    network_issues = CheckReachability(urls, http_client)
  log.status.Print()  # newline to separate progress tracker from results

  if not network_issues:
    log.status.Print('Network diagnostic {0}.\n'.format(
        'passed' if first_run else 'now passes'))
    return True

  log.status.Print('Network diagnostic {0}.'.format(
      'failed' if first_run else 'still does not pass'))
  if first_run:
    for issue in network_issues:
      log.status.Print('    {0}'.format(issue.message))
  log.status.Print()  # newline to separate results from proxy setup prompts
  return False


def CheckReachability(urls, http_client=None):
  """Checks whether the hosts of given urls are reachable.

  Args:
    urls: iterable(str), The list of urls to check connection to.
    http_client: httplib2.Http, an object used by gcloud to make http and https
      connections. Defaults to an non-authenticated Http object from the
      googlecloudsdk.core.credentials.http module.

  Returns:
    list(Failure): Reasons for why any urls were unreachable. The list will be
    empty if all urls are reachable.
  """
  if not http_client:
    http_client = http.Http(auth=False)

  failures = []
  for url in urls:
    try:
      response, _ = http_client.request(url, method='GET')
    # TODO(b/29218762): Investigate other possible exceptions.
    except (httplib.HTTPException, socket.error, ssl.SSLError,
            httplib2.HttpLib2Error) as err:
      message = 'Cannot reach {0} ({1})'.format(url, type(err).__name__)
      failures.append(Failure(message=message, exception=err))
    else:
      # Accepting "UNAUTHORIZED" response since check done with unauthenticated
      # http client by default.
      if response.status not in (httplib.OK, httplib.UNAUTHORIZED):
        message = 'Cannot reach {0} ([{1}] {2})'.format(url, response.status,
                                                        response.reason)
        failures.append(Failure(message=message, response=response))
  return failures


def _ChangeGcloudProxySettings():
  """Walks user through setting up gcloud proxy properties.

  Returns:
    bool: Whether properties were successfully changed.
  """
  try:
    proxy_info, is_existing_proxy = _CheckGcloudProxyInfo()
  except properties.InvalidValueError:
    log.status.Print(
        'Cloud SDK network proxy settings appear to be invalid. Proxy type, '
        'address, and port must be specified. Run [gcloud info] for more '
        'details.\n')
    is_existing_proxy = True
  else:
    _DisplayGcloudProxyInfo(proxy_info, is_existing_proxy)

  if is_existing_proxy:
    options = ['Change Cloud SDK network proxy properties',
               'Clear all gcloud proxy properties',
               'Exit']
    existing_proxy_idx = console_io.PromptChoice(
        options, message='What would you like to do?')
    if existing_proxy_idx == 1:
      _SetGcloudProxyProperties()
      log.status.Print('Cloud SDK proxy properties cleared.\n')
      return True
    if existing_proxy_idx == 2 or existing_proxy_idx is None:
      return False
  else:
    from_scratch_prompt = (
        'Do you have a network proxy you would like to set in gcloud')
    if not console_io.PromptContinue(prompt_string=from_scratch_prompt):
      return False

  proxy_type_options = sorted(
      [t.upper() for t in http_proxy_types.GetProxyTypeMap()])
  proxy_type_idx = console_io.PromptChoice(
      proxy_type_options, message='Select the proxy type:')
  if proxy_type_idx is None:
    return False
  proxy_type = proxy_type_options[proxy_type_idx].lower()

  address = console_io.PromptResponse('Enter the proxy host address: ')
  log.status.Print()
  if not address:
    return False

  port = console_io.PromptResponse('Enter the proxy port: ')
  log.status.Print()
  if not port:
    return False

  username, password = None, None
  authenticated = console_io.PromptContinue(
      prompt_string='Is your proxy authenticated', default=False)
  if authenticated:
    username = console_io.PromptResponse('Enter the proxy username: ')
    log.status.Print()
    if not username:
      return False
    password = console_io.PromptResponse('Enter the proxy password: ')
    log.status.Print()
    if not password:
      return False

  _SetGcloudProxyProperties(proxy_type=proxy_type, address=address, port=port,
                            username=username, password=password)
  log.status.Print('Cloud SDK proxy properties set.\n')
  return True


def _CheckGcloudProxyInfo():
  """Gets ProxyInfo effective in gcloud and whether it is from gloud properties.

  Returns:
    tuple of (httplib2.ProxyInfo, bool): First entry is proxy information, and
      second is whether that proxy information came from previously set Cloud
      SDK proxy properties.

  Raises:
    properties.InvalidValueError: If the properties did not include a valid set.
      "Valid" means all three of these attributes are present: proxy type, host,
      and port.
  """
  proxy_info = http_proxy.GetHttpProxyInfo()  # raises InvalidValueError
  if not proxy_info:
    return None, False

  # googlecloudsdk.core.http_proxy.GetHttpProxyInfo() will return a function
  # if there are no valid proxy settings in gcloud properties. Otherwise, it
  # will return an instantiated httplib2.ProxyInfo object.
  from_gcloud_properties = True
  if callable(proxy_info):
    from_gcloud_properties = False
    # All Google Cloud SDK network calls use https.
    proxy_info = proxy_info('https')

  return proxy_info, from_gcloud_properties


def _DisplayGcloudProxyInfo(proxy_info, from_gcloud):
  """Displays effective Cloud SDK proxy information to status output stream."""
  if not proxy_info:
    log.status.Print()
    return

  log.status.Print('Current effective Cloud SDK network proxy settings:')
  if not from_gcloud:
    log.status.Print('(These settings are from your machine\'s environment, '
                     'not gcloud properties.)')
  proxy_type_name = http_proxy_types.GetReverseProxyTypeMap().get(
      proxy_info.proxy_type, 'UNKNOWN PROXY TYPE')
  log.status.Print('    type = {0}'.format(proxy_type_name))
  log.status.Print('    host = {0}'.format(proxy_info.proxy_host))
  log.status.Print('    port = {0}'.format(proxy_info.proxy_port))
  log.status.Print('    username = {0}'.format(proxy_info.proxy_user))
  log.status.Print('    password = {0}'.format(proxy_info.proxy_pass))
  log.status.Print()


def _SetGcloudProxyProperties(proxy_type=None, address=None, port=None,
                              username=None, password=None):
  """Sets proxy group properties; clears any property not explicitly passed."""
  properties.PersistProperty(properties.VALUES.proxy.proxy_type, proxy_type)
  properties.PersistProperty(properties.VALUES.proxy.address, address)
  properties.PersistProperty(properties.VALUES.proxy.port, port)
  properties.PersistProperty(properties.VALUES.proxy.username, username)
  properties.PersistProperty(properties.VALUES.proxy.password, password)
