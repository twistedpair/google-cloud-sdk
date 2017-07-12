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
"""Code to provide a hook for staging.

Some App Engine runtimes require an additional staging step before deployment
(e.g. when deploying compiled artifacts, or vendoring code that normally lives
outside of the app directory). This module contains (1) a registry mapping
runtime/environment combinations to staging commands, and (2) code to run said
commands.

The interface is defined as follows:

- A staging command is an executable (binary or script) that takes two
  positional parameters: the path of the `<service>.yaml` in the directory
  containing the unstaged application code, and the path of an empty directory
  in which to stage the application code.
- On success, the STDOUT and STDERR of the staging command are logged at the
  INFO level. On failure, a StagingCommandFailedError is raised containing the
  STDOUT and STDERR of the staging command (which are surfaced to the user as an
  ERROR message).
"""
import cStringIO
import os
import tempfile

from googlecloudsdk.api_lib.app import util
from googlecloudsdk.command_lib.util import java
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms


_JAVA_APPCFG_ENTRY_POINT = 'com.google.appengine.tools.admin.AppCfg'

_JAVA_APPCFG_STAGE_FLAGS = [
    '--enable_jar_splitting',
    '--enable_jar_classes']

_STAGING_COMMAND_OUTPUT_TEMPLATE = """\
------------------------------------ STDOUT ------------------------------------
{out}\
------------------------------------ STDERR ------------------------------------
{err}\
--------------------------------------------------------------------------------
"""


class NoSdkRootError(exceptions.Error):

  def __init__(self):
    super(NoSdkRootError, self).__init__(
        'No SDK root could be found. Please check your installation.')


class StagingCommandFailedError(exceptions.Error):

  def __init__(self, args, return_code, output_message):
    super(StagingCommandFailedError, self).__init__(
        'Staging command [{0}] failed with return code [{1}].\n\n{2}'.format(
            ' '.join(args), return_code, output_message))


def _StagingProtocolMapper(command_path, descriptor, app_dir, staging_dir):
  return [command_path, descriptor, app_dir, staging_dir]


def _JavaStagingMapper(command_path, descriptor, app_dir, staging_dir):
  """Map a java staging request to the right args.

  Args:
    command_path: str, path to the jar tool file.
    descriptor: str, path to the `appengine-web.xml`
    app_dir: str, path to the unstaged app directory
    staging_dir: str, path to the empty staging dir

  Raises:
    java.JavaError, if Java is not installed.

  Returns:
    [str], args for executable invocation.
  """
  del descriptor  # Unused, app_dir is sufficient
  java.CheckIfJavaIsInstalled('local staging for java')
  java_bin = files.FindExecutableOnPath('java')
  args = ([java_bin, '-classpath', command_path, _JAVA_APPCFG_ENTRY_POINT] +
          _JAVA_APPCFG_STAGE_FLAGS + ['stage', app_dir, staging_dir])
  return args


class _Command(object):
  """Represents a cross-platform command.

  Paths are relative to the Cloud SDK Root directory.

  Attributes:
    nix_path: str, the path to the executable on Linux and OS X
    windows_path: str, the path to the executable on Windows
    component: str or None, the name of the Cloud SDK component which contains
      the executable
    mapper: fn or None, function that maps a staging invocation to a command.
  """

  def __init__(self, nix_path, windows_path, component=None, mapper=None):
    self.nix_path = nix_path
    self.windows_path = windows_path
    self.component = component
    self.mapper = mapper or _StagingProtocolMapper

  @property
  def name(self):
    if platforms.OperatingSystem.Current() is platforms.OperatingSystem.WINDOWS:
      return self.windows_path
    else:
      return self.nix_path

  def GetPath(self):
    """Returns the path to the command.

    Returns:
      str, the path to the command

    Raises:
       NoSdkRootError: if no Cloud SDK root could be found (and therefore the
       command is not installed).
    """
    sdk_root = config.Paths().sdk_root
    if not sdk_root:
      raise NoSdkRootError()
    return os.path.join(sdk_root, self.name)

  def EnsureInstalled(self):
    if self.component is None:
      return
    msg = ('The component [{component}] is required for staging this '
           'application.').format(component=self.component)
    update_manager.UpdateManager.EnsureInstalledAndRestart([self.component],
                                                           msg=msg)

  def Run(self, staging_area, descriptor, app_dir):
    """Invokes a staging command with a given <service>.yaml and temp dir.

    Args:
      staging_area: str, path to the staging area.
      descriptor: str, path to the unstaged <service>.yaml or appengine-web.xml
      app_dir: str, path to the unstaged app directory

    Returns:
      str, the path to the staged directory.

    Raises:
      StagingCommandFailedError: if the staging command process exited non-zero.
    """
    staging_dir = tempfile.mkdtemp(dir=staging_area)
    args = self.mapper(self.GetPath(), descriptor, app_dir, staging_dir)
    log.info('Executing staging command: [{0}]\n\n'.format(' '.join(args)))
    out = cStringIO.StringIO()
    err = cStringIO.StringIO()
    return_code = execution_utils.Exec(args, no_exit=True, out_func=out.write,
                                       err_func=err.write)
    message = _STAGING_COMMAND_OUTPUT_TEMPLATE.format(out=out.getvalue(),
                                                      err=err.getvalue())
    log.info(message)
    if return_code:
      raise StagingCommandFailedError(args, return_code, message)
    return staging_dir


# Path to the go-app-stager binary
_GO_APP_STAGER_DIR = os.path.join('platform', 'google_appengine')

# Path to the jar which contains the staging command
_APPENGINE_TOOLS_JAR = os.path.join(
    'platform', 'google_appengine', 'google', 'appengine', 'tools', 'java',
    'lib', 'appengine-tools-api.jar')

# STAGING_REGISTRY is a map of (runtime, app-engine-environment) to executable
# path relative to Cloud SDK Root; it should look something like the following:
#
#     from googlecloudsdk.api_lib.app import util
#     STAGING_REGISTRY = {
#       ('intercal', util.Environment.FLEX):
#           _Command(
#               os.path.join('command_dir', 'stage-intercal-flex.sh'),
#               os.path.join('command_dir', 'stage-intercal-flex.exe'),
#               component='app-engine-intercal'),
#       ('x86-asm', util.Environment.STANDARD):
#           _Command(
#               os.path.join('command_dir', 'stage-x86-asm-standard'),
#               os.path.join('command_dir', 'stage-x86-asm-standard.exe'),
#               component='app-engine-intercal'),
#     }
_STAGING_REGISTRY = {
    ('go', util.Environment.STANDARD):
        _Command(
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager'),
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
    ('go', util.Environment.MANAGED_VMS):
        _Command(
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager'),
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
    ('go', util.Environment.FLEX):
        _Command(
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager'),
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
}

# _STAGING_REGISTRY_BETA extends _STAGING_REGISTRY, overriding entries if the
# same key is used.
_STAGING_REGISTRY_BETA = {
    ('java-xml', util.Environment.STANDARD):
        _Command(
            _APPENGINE_TOOLS_JAR,
            _APPENGINE_TOOLS_JAR,
            component='app-engine-java',
            mapper=_JavaStagingMapper)
}


class Stager(object):

  def __init__(self, registry, staging_area):
    self.registry = registry
    self.staging_area = staging_area

  def Stage(self, descriptor, app_dir, runtime, environment):
    """Stage the given deployable or do nothing if N/A.

    Args:
      descriptor: str, path to the unstaged <service>.yaml or appengine-web.xml
      app_dir: str, path to the unstaged app directory
      runtime: str, the name of the runtime for the application to stage
      environment: api_lib.app.util.Environment, the environment for the
          application to stage

    Returns:
      str, the path to the staged directory or None if no corresponding staging
          command was found.

    Raises:
      NoSdkRootError: if no Cloud SDK installation root could be found.
      StagingCommandFailedError: if the staging command process exited non-zero.
    """
    command = self.registry.get((runtime, environment))

    if not command:
      # Many runtimes do not require a staging step; this isn't a problem.
      log.debug(('No staging command found for runtime [%s] and environment '
                 '[%s].'), runtime, environment.name)
      return

    command.EnsureInstalled()
    return command.Run(self.staging_area, descriptor, app_dir)


def GetStager(staging_area):
  """Get the default stager."""
  return Stager(_STAGING_REGISTRY, staging_area)


def GetBetaStager(staging_area):
  """Get the beta stager, used for `gcloud beta *` commands."""
  registry = _STAGING_REGISTRY.copy()
  registry.update(_STAGING_REGISTRY_BETA)
  return Stager(registry, staging_area)


def GetNoopStager(staging_area):
  """Get a stager with an empty registry."""
  return Stager({}, staging_area)
