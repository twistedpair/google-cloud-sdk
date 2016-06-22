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
"""A library to support auth commands."""

import json
import os

from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import log
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms
from oauth2client import client
from oauth2client import clientsecrets

# Client ID from project "usable-auth-library", configured for
# general purpose API testing
# pylint: disable=g-line-too-long
DEFAULT_CREDENTIALS_DEFAULT_CLIENT_ID = '764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com'
DEFAULT_CREDENTIALS_DEFAULT_CLIENT_SECRET = 'd-FL95Q19q7MQmFpd7hHD0Ty'
CLOUD_PLATFORM_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
GOOGLE_DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'

# A list of results for webbrowser.get().name that indicate we should not
# attempt to open a web browser for the user.
_WEBBROWSER_NAMES_BLACKLIST = [
    'www-browser',
]

# These are environment variables that can indicate a running compositor on
# Linux.
_DISPLAY_VARIABLES = ['DISPLAY', 'WAYLAND_DISPLAY', 'MIR_SOCKET']


def ShouldLaunchBrowser(launch_browser):
  """Determines if a browser can be launched."""
  # pylint:disable=g-import-not-at-top, Import when needed for performance.
  import webbrowser
  # Sometimes it's not possible to launch the web browser. This often
  # happens when people ssh into other machines.
  if launch_browser:
    if c_gce.Metadata().connected:
      launch_browser = False
    current_os = platforms.OperatingSystem.Current()
    if (current_os is platforms.OperatingSystem.LINUX and
        not any(os.getenv(var) for var in _DISPLAY_VARIABLES)):
      launch_browser = False
    try:
      browser = webbrowser.get()
      if (hasattr(browser, 'name')
          and browser.name in _WEBBROWSER_NAMES_BLACKLIST):
        launch_browser = False
    except webbrowser.Error:
      launch_browser = False

  return launch_browser


def DoInstalledAppBrowserFlow(client_id_file, scopes, launch_browser):
  """Launches a browser to get credentials."""
  try:
    if client_id_file is not None:
      client_type = GetClientSecretsType(client_id_file)
      if client_type != clientsecrets.TYPE_INSTALLED:
        raise c_exc.ToolException(
            'Only client IDs of type \'%s\' are allowed, but encountered '
            'type \'%s\'' % (clientsecrets.TYPE_INSTALLED, client_type))
      return c_store.AcquireFromWebFlowAndClientIdFile(
          client_id_file=client_id_file,
          scopes=scopes,
          launch_browser=launch_browser)
    else:
      return c_store.AcquireFromWebFlow(
          launch_browser=launch_browser,
          scopes=scopes,
          client_id=DEFAULT_CREDENTIALS_DEFAULT_CLIENT_ID,
          client_secret=DEFAULT_CREDENTIALS_DEFAULT_CLIENT_SECRET)
  except c_store.FlowError:
    msg = 'There was a problem with web authentication.'
    if launch_browser:
      msg += ' Try running again with --no-launch-browser.'
    log.error(msg)
    raise


# TODO(b/29157057) make this information accessible through oauth2client
# instead of duplicating internal code from clientsecrets
def GetClientSecretsType(client_id_file):
  """Get the type of the client secrets file (web or installed)."""
  invalid_file_format_msg = (
      'Invalid file format. See '
      'https://developers.google.com/api-client-library/'
      'python/guide/aaa_client_secrets')

  try:
    with open(client_id_file, 'r') as fp:
      obj = json.load(fp)
  except IOError:
    raise clientsecrets.InvalidClientSecretsError(
        'Cannot read file: "%s"' % client_id_file)
  if obj is None:
    raise clientsecrets.InvalidClientSecretsError(invalid_file_format_msg)
  if len(obj) != 1:
    raise clientsecrets.InvalidClientSecretsError(
        invalid_file_format_msg + ' '
        'Expected a JSON object with a single property for a "web" or '
        '"installed" application')
  return tuple(obj)[0]


# TODO(b/29157057) refactor so that access to private functions in
# oauth2client is not necessary
def RevokeCredsInWellKnownFile(brief):
  """Revoke the credentials in ADC's well-known file."""
  # pylint:disable=protected-access, refactor as per TODO above
  credentials_filename = client._get_well_known_file()
  if not os.path.isfile(credentials_filename):
    if not brief:
      log.status.write(
          '\nApplication Default Credentials have not been\n'
          'set up by a tool, so nothing was revoked.\n')
    return

  # We only want to get the credentials from the well-known file, because
  # no other credentials can be revoked.
  # pylint:disable=protected-access, refactor as per TODO above
  creds = client._get_application_default_credential_from_file(
      credentials_filename)
  if creds.serialization_data['type'] != 'authorized_user':
    if not brief:
      log.status.write(
          '\nThe credentials set up for Application Default Credentials\n'
          'through the Google Cloud SDK are service account credentials,\n'
          'so they were not revoked.\n')
  else:
    c_store.RevokeCredentials(creds)
    if not brief:
      log.status.write(
          '\nThe credentials set up for Application Default Credentials\n'
          'through the Google Cloud SDK have been revoked.\n')

  os.remove(credentials_filename)

  if not brief:
    log.status.write(
        '\nThe file storing the Application Default Credentials\n'
        'has been removed.\n')


def AdcEnvVariableIsSet():
  adc_filename = os.environ.get(client.GOOGLE_APPLICATION_CREDENTIALS, None)
  return adc_filename is not None


# TODO(b/29157057) refactor so that access to private functions in
# oauth2client is not necessary
def CreateWellKnownFileDir():
  """Create the directory for ADC's well-known file."""
  # pylint:disable=protected-access, refactor as per TODO above
  credentials_filename = client._get_well_known_file()
  files.MakeDir(os.path.dirname(credentials_filename))
