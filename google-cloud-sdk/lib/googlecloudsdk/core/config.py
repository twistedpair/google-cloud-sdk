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

"""Config for Google Cloud Platform CLIs."""

import json
import os
import time

import googlecloudsdk
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import pkg_resources
from googlecloudsdk.core.util import platforms


class Error(exceptions.Error):
  """Exceptions for the cli module."""


# Environment variable for the directory containing Cloud SDK configuration.
CLOUDSDK_CONFIG = 'CLOUDSDK_CONFIG'

# Environment variable for overriding the Cloud SDK active named config
CLOUDSDK_ACTIVE_CONFIG_NAME = 'CLOUDSDK_ACTIVE_CONFIG_NAME'

# Common shell script preamble for ${CLOUDSDK_SH_PREAMBLE} templates.
CLOUDSDK_SH_PREAMBLE = r"""
# <cloud-sdk-sh-preamble>
#
#  CLOUDSDK_ROOT_DIR            (a)  installation root dir
#  CLOUDSDK_PYTHON              (u)  python interpreter path
#  CLOUDSDK_PYTHON_ARGS         (u)  python interpreter arguments
#  CLOUDSDK_PYTHON_SITEPACKAGES (u)  use python site packages
#
# (a) always defined by the preamble
# (u) user definition overrides preamble

# Determines the real cloud sdk root dir given the script path.
# Would be easier with a portable "readlink -f".
_cloudsdk_root_dir() {
  case $1 in
  /*)   _cloudsdk_path=$1
        ;;
  */*)  _cloudsdk_path=$PWD/$1
        ;;
  *)    _cloudsdk_path=$(which "$1")
        case $_cloudsdk_path in
        /*) ;;
        *)  _cloudsdk_path=$PWD/$_cloudsdk_path ;;
        esac
        ;;
  esac
  _cloudsdk_dir=0
  while :
  do
    while _cloudsdk_link=$(readlink "$_cloudsdk_path")
    do
      case $_cloudsdk_link in
      /*) _cloudsdk_path=$_cloudsdk_link ;;
      *)  _cloudsdk_path=$(dirname "$_cloudsdk_path")/$_cloudsdk_link ;;
      esac
    done
    case $_cloudsdk_dir in
    1)  break ;;
    esac
    _cloudsdk_dir=1
    _cloudsdk_path=$(dirname "$_cloudsdk_path")
  done
  while :
  do  case $_cloudsdk_path in
      */.)    _cloudsdk_path=$(dirname "$_cloudsdk_path")
              ;;
      */bin)  dirname "$_cloudsdk_path"
              break
              ;;
      *)      echo "$_cloudsdk_path"
              break
              ;;
      esac
  done
}
CLOUDSDK_ROOT_DIR=$(_cloudsdk_root_dir "$0")

# Cloud SDK requires python 2 (2.6 or 2.7)
case $CLOUDSDK_PYTHON in
*python2*)
  ;;
*python[0-9]*)
  CLOUDSDK_PYTHON=
  ;;
esac
# if CLOUDSDK_PYTHON is empty
if [ -z "$CLOUDSDK_PYTHON" ]; then
  # if python2 exists then plain python may point to a version != 2
  if which python2 >/dev/null; then
    CLOUDSDK_PYTHON=python2
  elif which python2.7 >/dev/null; then
    # this is what some OS X versions call their built-in Python
    CLOUDSDK_PYTHON=python2.7
  else
    CLOUDSDK_PYTHON=python
  fi
fi

# if CLOUDSDK_PYTHON_SITEPACKAGES and VIRTUAL_ENV are empty
case :$CLOUDSDK_PYTHON_SITEPACKAGES:$VIRTUAL_ENV: in
:::)  # add -S to CLOUDSDK_PYTHON_ARGS if not already there
      case " $CLOUDSDK_PYTHON_ARGS " in
      *" -S "*) ;;
      "  ")     CLOUDSDK_PYTHON_ARGS="-S"
                ;;
      *)        CLOUDSDK_PYTHON_ARGS="$CLOUDSDK_PYTHON_ARGS -S"
                ;;
      esac
      unset CLOUDSDK_PYTHON_SITEPACKAGES
      ;;
*)    # remove -S from CLOUDSDK_PYTHON_ARGS if already there
      while :; do
        case " $CLOUDSDK_PYTHON_ARGS " in
        *" -S "*) CLOUDSDK_PYTHON_ARGS=${CLOUDSDK_PYTHON_ARGS%%-S*}' '${CLOUDSDK_PYTHON_ARGS#*-S} ;;
        *) break ;;
        esac
      done
      # if CLOUDSDK_PYTHON_SITEPACKAGES is empty
      [ -z "$CLOUDSDK_PYTHON_SITEPACKAGES" ] &&
        CLOUDSDK_PYTHON_SITEPACKAGES=1
      export CLOUDSDK_PYTHON_SITEPACKAGES
      ;;
esac

export CLOUDSDK_ROOT_DIR CLOUDSDK_PYTHON_ARGS

# </cloud-sdk-sh-preamble>
"""

# Common cmd.exe script preamble for ${CLOUDSDK_CMD_PREAMBLE} templates.
CLOUDSDK_CMD_PREAMBLE = r"""
rem <cloud-sdk-cmd-preamble>
rem
rem  CLOUDSDK_ROOT_DIR            (a)  installation root dir
rem  CLOUDSDK_PYTHON              (u)  python interpreter path
rem  CLOUDSDK_PYTHON_ARGS         (u)  python interpreter arguments
rem  CLOUDSDK_PYTHON_SITEPACKAGES (u)  use python site packages
rem
rem (a) always defined by the preamble
rem (u) user definition overrides preamble

rem This command lives in google-cloud-sdk\bin so its parent directory is the
rem root.
SET CLOUDSDK_ROOT_DIR=%~dp0..
SET PATH=%CLOUDSDK_ROOT_DIR%\bin\sdk;%PATH%

IF "%CLOUDSDK_PYTHON%"=="" (
  SET BUNDLED_PYTHON=!CLOUDSDK_ROOT_DIR!\platform\bundledpython\python.exe
  IF EXIST !BUNDLED_PYTHON! (
    SET CLOUDSDK_PYTHON=!BUNDLED_PYTHON!
  ) ELSE (
    SET CLOUDSDK_PYTHON=python.exe
  )
)

IF "%CLOUDSDK_PYTHON_SITEPACKAGES%" == "" (
  IF "!VIRTUAL_ENV!" == "" (
    SET CLOUDSDK_PYTHON_SITEPACKAGES=
  ) ELSE (
    SET CLOUDSDK_PYTHON_SITEPACKAGES=1
  )
)
SET CLOUDSDK_PYTHON_ARGS_NO_S=%CLOUDSDK_PYTHON_ARGS:-S=%
IF "%CLOUDSDK_PYTHON_SITEPACKAGES%" == "" (
  IF "!CLOUDSDK_PYTHON_ARGS!" == "" (
    SET CLOUDSDK_PYTHON_ARGS=-S
  ) ELSE (
    SET CLOUDSDK_PYTHON_ARGS=!CLOUDSDK_PYTHON_ARGS_NO_S! -S
  )
) ELSE IF "%CLOUDSDK_PYTHON_ARGS%" == "" (
  SET CLOUDSDK_PYTHON_ARGS=
) ELSE (
  SET CLOUDSDK_PYTHON_ARGS=!CLOUDSDK_PYTHON_ARGS_NO_S!
)

rem </cloud-sdk-cmd-preamble>
"""


# Common powershell.exe script preamble for ${CLOUDSDK_PS1_PREAMBLE} templates.
CLOUDSDK_PS1_PREAMBLE = r"""
# <cloud-sdk-ps1-preamble>
#
#  CLOUDSDK_ROOT_DIR            (a)  installation root dir
#  CLOUDSDK_PYTHON              (u)  python interpreter path
#  CLOUDSDK_PYTHON_ARGS         (u)  python interpreter arguments
#  CLOUDSDK_PYTHON_SITEPACKAGES (u)  use python site packages
#
# (a) always defined by the preamble
# (u) user definition overrides preamble


function Restore-Environment([System.Collections.DictionaryEntry[]] $origEnv) {
  # Remove any added variables.
  compare-object $origEnv $(get-childitem Env:) -property Key -passthru |
      where-object { $_.SideIndicator -eq "=>" } |
          foreach-object { remove-item -path ("Env:" + $_.Name); }
  # Revert any changed variables to original values.
  compare-object $origEnv $(get-childitem Env:) -property Value -passthru |
      where-object { $_.SideIndicator -eq "<=" } |
          foreach-object { set-item -path ("Env:" + $_.Name) -value $_.Value }
}

# Save the original environmental variables so we can restore them at the end.
$origEnv = get-childitem Env:

$current_dir = Split-Path $script:MyInvocation.MyCommand.Path
$cloudsdk_root_dir = (Resolve-Path (Join-Path $current_dir '..')).Path
$env:PATH = (Join-Path $cloudsdk_root_dir 'bin\sdk') + ';' + $env:PATH

if (!$cloudsdk_python) {
  $cloudsdk_python = $env:CLOUDSDK_PYTHON
}
if (!$cloudsdk_python) {
  $bundled_python = Join-Path $cloudsdk_root_dir 'platform\bundledpython\python.exe'
  if (Test-Path $bundled_python) {
    $cloudsdk_python = $bundled_python
  } else {
    $cloudsdk_python = 'python.exe'
  }
}

if (!$cloudsdk_python_sitepackages) {
  $cloudsdk_python_sitepackages = $env:CLOUDSDK_PYTHON_SITEPACKAGES
}
if (!$cloudsdk_python_sitepackages) {
  if (!(Test-Path env:\VIRTUAL_ENV)) {
    $cloudsdk_python_sitepackages = ''
  } else {
    $cloudsdk_python_sitepackages = 1
  }
}

if (!$cloudsdk_python_args) {
  $cloudsdk_python_args = $env:CLOUDSDK_PYTHON_ARGS
}
$cloudsdk_python_args_no_s = ''
if ($cloudsdk_python_args) {
  $args_array_no_s = ($cloudsdk_python_args.split(' ') | ? {$_ -cne '-S'})
  if ($args_array_no_s) {
    $cloudsdk_python_args_no_s = [string]::join(' ', $args_array_no_s)
  }
}
if (!$cloudsdk_python_sitepackages) {
  $cloudsdk_python_args = $cloudsdk_python_args_no_s + ' -S'
} else {
  $cloudsdk_python_args = $cloudsdk_python_args_no_s
}

$env:CLOUDSDK_ROOT_DIR = $cloudsdk_root_dir
$env:CLOUDSDK_PYTHON_ARGS = $cloudsdk_python_args

# </cloud-sdk-ps1-preamble>
"""


class InstallationConfig(object):
  """Loads configuration constants from the core config file.

  Attributes:
    version: str, The version of the core component.
    revision: long, A revision number from a component snapshot.  This is a
      long int but formatted as an actual date in seconds (i.e 20151009132504).
      It is *NOT* seconds since the epoch.
    user_agent: str, The base string of the user agent to use when making API
      calls.
    documentation_url: str, The URL where we can redirect people when they need
      more information.
    release_notes_url: str, The URL where we host a nice looking version of our
      release notes.
    snapshot_url: str, The url for the component manager to look at for
      updates.
    disable_updater: bool, True to disable the component manager for this
      installation.  We do this for distributions through another type of
      package manager like apt-get.
    disable_usage_reporting: bool, True to disable the sending of usage data by
      default.
    snapshot_schema_version: int, The version of the snapshot schema this code
      understands.
    release_channel: str, The release channel for this Cloud SDK distribution.
    config_suffix: str, A string to add to the end of the configuration
      directory name so that different release channels can have separate
      config.
  """

  REVISION_FORMAT_STRING = '%Y%m%d%H%M%S'

  @staticmethod
  def Load():
    """Initializes the object with values from the config file.

    Returns:
      InstallationSpecificData: The loaded data.
    """
    data = json.loads(pkg_resources.GetResource(__name__, 'config.json'))

    # Python versions prior to 2.6.5 do not allow the keys in a kwargs dict to
    # be unicode strings.  The json module parses files as unicode.  We are not
    # using any unicode in the keys for our config properties so a simple
    # conversion to str is safe.
    non_unicode_data = dict([(str(k), v) for k, v in data.iteritems()])
    return InstallationConfig(**non_unicode_data)

  @staticmethod
  def FormatRevision(time_struct):
    """Formats a given time as a revision string for a component snapshot.

    Args:
      time_struct: time.struct_time, The time you want to format.

    Returns:
      long, A revision number from a component snapshot.  This is a long int but
      formatted as an actual date in seconds (i.e 20151009132504).  It is *NOT*
      seconds since the epoch.
    """
    return long(time.strftime(InstallationConfig.REVISION_FORMAT_STRING,
                              time_struct))

  @staticmethod
  def ParseRevision(revision):
    """Parse the given revision into a time.struct_time.

    Args:
      revision: long, A revision number from a component snapshot.  This is a
        long int but formatted as an actual date in seconds
        (i.e 20151009132504). It is *NOT* seconds since the epoch.

    Returns:
      time.struct_time, The parsed time.
    """
    return time.strptime(str(revision),
                         InstallationConfig.REVISION_FORMAT_STRING)

  @staticmethod
  def ParseRevisionAsSeconds(revision):
    """Parse the given revision into seconds since the epoch.

    Args:
      revision: long, A revision number from a component snapshot.  This is a
        long int but formatted as an actual date in seconds
        (i.e 20151009132504). It is *NOT* seconds since the epoch.

    Returns:
      int, The number of seconds since the epoch that this revision represents.
    """
    return time.mktime(InstallationConfig.ParseRevision(revision))

  def __init__(self, version, revision, user_agent, documentation_url,
               release_notes_url, snapshot_url, disable_updater,
               disable_usage_reporting, snapshot_schema_version,
               release_channel, config_suffix):
    # JSON returns all unicode.  We know these are regular strings and using
    # unicode in environment variables on Windows doesn't work.
    self.version = str(version)
    self.revision = revision
    self.user_agent = str(user_agent)
    self.documentation_url = str(documentation_url)
    self.release_notes_url = str(release_notes_url)
    self.snapshot_url = str(snapshot_url)
    self.disable_updater = disable_updater
    self.disable_usage_reporting = disable_usage_reporting
    # This one is an int, no need to convert
    self.snapshot_schema_version = snapshot_schema_version
    self.release_channel = str(release_channel)
    self.config_suffix = str(config_suffix)

  def IsAlternateReleaseChannel(self):
    """Determines if this distribution is using an alternate release channel.

    Returns:
      True if this distribution is not one of the 'stable' release channels,
      False otherwise.
    """
    return self.release_channel != 'rapid'


INSTALLATION_CONFIG = InstallationConfig.Load()

CLOUD_SDK_VERSION = INSTALLATION_CONFIG.version
# TODO(user): Distribute a clientsecrets.json to avoid putting this in code.
CLOUDSDK_CLIENT_ID = '32555940559.apps.googleusercontent.com'
CLOUDSDK_CLIENT_NOTSOSECRET = 'ZmssLNjJy2998hD4CTg2ejr2'

CLOUDSDK_USER_AGENT = INSTALLATION_CONFIG.user_agent

# Do not add more scopes here, see http://b/19019218.
CLOUDSDK_SCOPES = (
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/cloud-platform',
    # TODO(user): remove the following once 'cloud-platform' is sufficient.
    'https://www.googleapis.com/auth/appengine.admin',
    'https://www.googleapis.com/auth/compute',  # needed by autoscaler
)


def EnsureSDKWriteAccess(sdk_root_override=None):
  """Error if the current user does not have write access to the sdk root.

  Args:
    sdk_root_override: str, The full path to the sdk root to use instead of
      using config.Paths().sdk_root.

  Raises:
    exceptions.RequiresAdminRightsError: If the sdk root is defined and the user
      does not have write access.
  """
  sdk_root = sdk_root_override or Paths().sdk_root
  if sdk_root and not file_utils.HasWriteAccessInDir(sdk_root):
    raise exceptions.RequiresAdminRightsError(sdk_root)


def GcloudPath():
  """Gets the path the main gcloud entrypoint.

  Returns:
    str: The path to gcloud.py
  """
  return os.path.join(
      os.path.dirname(os.path.dirname(googlecloudsdk.__file__)), 'gcloud.py')


class Paths(object):
  """Class to encapsulate the various directory paths of the Cloud SDK.

  Attributes:
    global_config_dir: str, The path to the user's global config area.
    workspace_dir: str, The path of the current workspace or None if not in a
      workspace.
    workspace_config_dir: str, The path to the config directory under the
      current workspace, or None if not in a workspace.
  """
  # Name of the directory that roots a cloud SDK workspace.
  _CLOUDSDK_GLOBAL_CONFIG_DIR_NAME = ('gcloud' +
                                      INSTALLATION_CONFIG.config_suffix)

  CLOUDSDK_STATE_DIR = '.install'
  CLOUDSDK_PROPERTIES_NAME = 'properties'

  def __init__(self):
    if platforms.OperatingSystem.Current() == platforms.OperatingSystem.WINDOWS:
      try:
        default_config_path = os.path.join(
            os.environ['APPDATA'], Paths._CLOUDSDK_GLOBAL_CONFIG_DIR_NAME)
      except KeyError:
        # This should never happen unless someone is really messing with things.
        drive = os.environ.get('SystemDrive', 'C:')
        default_config_path = os.path.join(
            drive, '\\', Paths._CLOUDSDK_GLOBAL_CONFIG_DIR_NAME)
    else:
      default_config_path = os.path.join(
          os.path.expanduser('~'), '.config',
          Paths._CLOUDSDK_GLOBAL_CONFIG_DIR_NAME)
    self.global_config_dir = os.getenv(CLOUDSDK_CONFIG, default_config_path)

  @property
  def sdk_root(self):
    """Searches for the Cloud SDK root directory.

    Returns:
      str, The path to the root of the Cloud SDK or None if it could not be
      found.
    """
    return file_utils.FindDirectoryContaining(os.path.dirname(__file__),
                                              Paths.CLOUDSDK_STATE_DIR)

  @property
  def sdk_bin_path(self):
    """Forms a path to bin directory by using sdk_root.

    Returns:
      str, The path to the bin directory of the Cloud SDK or None if it could
      not be found.
    """
    sdk_root = self.sdk_root
    return os.path.join(sdk_root, 'bin') if sdk_root else None

  @property
  def completion_cache_dir(self):
    return os.path.join(self.global_config_dir, 'completion_cache')

  @property
  def credentials_path(self):
    """Gets the path to the file to store credentials in.

    Credentials are always stored in global config, never the local workspace.
    This is due to the fact that local workspaces are likely to be stored whole
    in source control, and we don't want to accidentally publish credential
    information.  We also want user credentials to be shared across workspaces
    if they are for the same user.

    Returns:
      str, The path to the credential file.
    """
    return os.path.join(self.global_config_dir, 'credentials')

  @property
  def logs_dir(self):
    """Gets the path to the directory to put logs in for calliope commands.

    Returns:
      str, The path to the directory to put logs in.
    """
    return os.path.join(self.global_config_dir, 'logs')

  @property
  def analytics_cid_path(self):
    """Gets the path to the file to store the client id for analytics.

    This is always stored in the global location because it is per install.

    Returns:
      str, The path to the file.
    """
    return os.path.join(self.global_config_dir, '.metricsUUID')

  @property
  def update_check_cache_path(self):
    """Gets the path to the file to cache information about update checks.

    This is stored in the config directory instead of the installation state
    because if the SDK is installed as root, it will fail to persist the cache
    when you are running gcloud as a normal user.

    Returns:
      str, The path to the file.
    """
    return os.path.join(self.global_config_dir, '.last_update_check.json')

  @property
  def installation_properties_path(self):
    """Gets the path to the installation-wide properties file.

    Returns:
      str, The path to the file.
    """
    sdk_root = self.sdk_root
    if not sdk_root:
      return None
    return os.path.join(sdk_root, self.CLOUDSDK_PROPERTIES_NAME)

  @property
  def user_properties_path(self):
    """Gets the path to the properties file in the user's global config dir.

    Returns:
      str, The path to the file.
    """
    return os.path.join(self.global_config_dir, self.CLOUDSDK_PROPERTIES_NAME)

  @property
  def named_config_activator_path(self):
    """Gets the path to the file pointing at the user's active named config.

    This is the file that stores the name of the user's active named config,
    not the path to the configuration file itself.

    Returns:
      str, The path to the file.
    """
    return os.path.join(self.global_config_dir, 'active_config')

  @property
  def named_config_directory(self):
    """Gets the path to the directory that stores the named configs.

    Returns:
      str, The path to the directory.
    """
    return os.path.join(self.global_config_dir, 'configurations')

  @property
  def container_config_path(self):
    return os.path.join(self.global_config_dir, 'kubernetes')

  def LegacyCredentialsDir(self, account):
    """Gets the path to store legacy multistore credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the multistore credentials file.
    """
    if not account:
      account = 'default'
    return os.path.join(self.global_config_dir, 'legacy_credentials', account)

  def LegacyCredentialsMultistorePath(self, account):
    """Gets the path to store legacy multistore credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the multistore credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'multistore.json')

  def LegacyCredentialsJSONPath(self, account):
    """Gets the path to store legacy JSON credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the JSON credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'singlestore.json')

  def LegacyCredentialsGAEJavaPath(self, account):
    """Gets the path to store legacy GAE for Java credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the  GAE for Java credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'gaejava.txt')

  def LegacyCredentialsGSUtilPath(self, account):
    """Gets the path to store legacy gsutil credentials in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the gsutil credentials file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), '.boto')

  def LegacyCredentialsKeyPath(self, account):
    """Gets the path to store legacy key file in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the key file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'private_key.p12')

  def LegacyCredentialsJSONKeyPath(self, account):
    """Gets the path to store legacy JSON key file in.

    Args:
      account: str, Email account tied to the authorizing credentials.

    Returns:
      str, The path to the key file.
    """
    return os.path.join(self.LegacyCredentialsDir(account), 'private_key.json')

  def GCECachePath(self):
    """Get the path to cache whether or not we're on a GCE machine.

    Returns:
      str, The path to the GCE cache.
    """
    return os.path.join(self.global_config_dir, 'gce')
