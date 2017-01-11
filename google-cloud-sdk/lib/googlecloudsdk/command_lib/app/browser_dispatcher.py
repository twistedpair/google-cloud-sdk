# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Tools for opening URL:s related to the app in the browser."""

from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import exceptions as api_lib_exceptions
from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.appengine.api import appinfo


def OpenURL(url):
  """Open a URL in the default web browser in a new tab.

  Args:
    url: The full HTTP(S) URL to open.
  """
  # Import in here for performance reasons
  # pylint: disable=g-import-not-at-top
  import webbrowser
  log.status.Print(
      'Opening [{0}] in a new tab in your default browser.'.format(url))
  webbrowser.open_new_tab(url)


def BrowseApp(project, service=None, version=None):
  """Open the app in a browser, optionally with given service and version.

  Args:
    project: str, project ID.
    service: str, (optional) specific service, defaults to 'default'
    version: str, (optional) specific version, defaults to latest

  Raises:
    MissingApplicationError: If an app does not exist.
  """
  try:
    url = deploy_command_util.GetAppHostname(
        app_id=project, service=service, version=version,
        use_ssl=appinfo.SECURE_HTTPS, deploy=False)
  except api_lib_exceptions.NotFoundError:
    log.debug('No app found:', exc_info=True)
    raise exceptions.MissingApplicationError(project)
  OpenURL(url)
