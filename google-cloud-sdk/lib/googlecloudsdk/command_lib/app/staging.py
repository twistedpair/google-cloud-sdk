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
import contextlib
import cStringIO
import os

from googlecloudsdk.api_lib.app import util
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms


class NoSdkRootError(exceptions.Error):

  def __init__(self):
    super(NoSdkRootError, self).__init__(
        'No SDK root could be found. Please check your installation.')


class StagingCommandFailedError(exceptions.Error):

  def __init__(self, args, return_code, output_message):
    super(StagingCommandFailedError, self).__init__(
        'Staging command [{0}] failed with return code [{1}].\n\n{2}'.format(
            ' '.join(args), return_code, output_message))


class _Command(object):
  """Represents a cross-platform command.

  Paths are relative to the Cloud SDK Root directory.

  Attributes:
    nix_path: str, the path to the executable on Linux and OS X
    windows_path: str, the path to the executable on Windows
    component: str or None, the name of the Cloud SDK component which contains
      the executable
  """

  def __init__(self, nix_path, windows_path, component=None):
    self.nix_path = nix_path
    self.windows_path = windows_path
    self.component = component

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

# Path to the go-app-stager binary
_GO_BIN_DIR = os.path.join('platform', 'google_appengine', 'goroot', 'bin')

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
_STAGING_REGISTRY = {}

# _STAGING_REGISTRY_BETA extends _STAGING_REGISTRY, overriding entries if the
# same key is used.
_STAGING_REGISTRY_BETA = {
    ('go', util.Environment.STANDARD):
        _Command(
            os.path.join(_GO_BIN_DIR, 'go-app-stager'),
            os.path.join(_GO_BIN_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
    ('go', util.Environment.MANAGED_VMS):
        _Command(
            os.path.join(_GO_BIN_DIR, 'go-app-stager'),
            os.path.join(_GO_BIN_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
    ('go', util.Environment.FLEX):
        _Command(
            os.path.join(_GO_BIN_DIR, 'go-app-stager'),
            os.path.join(_GO_BIN_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
}


_STAGING_COMMAND_OUTPUT_TEMPLATE = """\
------------------------------------ STDOUT ------------------------------------
{out}\
------------------------------------ STDERR ------------------------------------
{err}\
--------------------------------------------------------------------------------
"""


@contextlib.contextmanager
def _StageUsingGivenCommand(command_path, service_yaml):
  """Invokes a staging command with a given <service>.yaml and temp dir.

  This is a context manager because the temporary staging directory should
  always be deleted, independent of potential errors.

  Args:
    command_path: str, path to the staging command
    service_yaml: str, path to the unstaged <service>.yaml

  Yields:
    str, the path to the staged directory.

  Raises:
    StagingCommandFailedError: if the staging command process exited non-zero.
  """
  with files.TemporaryDirectory() as temp_directory:
    args = [command_path, service_yaml, temp_directory]
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
    yield temp_directory


class Stager(object):

  def __init__(self, registry):
    self.registry = registry

  @contextlib.contextmanager
  def Stage(self, service_yaml, runtime, environment):
    """Stage the given command.

    This method is a context manager that

    >>> with stager.Stage('python', util.Environment.STANDARD):
    ...   pass  # perform deployment steps

    Args:
      service_yaml: str, path to the unstaged <service>.yaml
      runtime: str, the name of the runtime for the application to stage
      environment: api_lib.app.util.Environment, the environment for the
          application to stage

    Yields:
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
      yield None
      return

    command.EnsureInstalled()

    command_path = command.GetPath()
    with _StageUsingGivenCommand(command_path, service_yaml) as app_dir:
      yield app_dir


def GetStager():
  """Get the default stager."""
  return Stager(_STAGING_REGISTRY)


def GetBetaStager():
  """Get the beta stager, used for `gcloud beta *` commands."""
  registry = _STAGING_REGISTRY.copy()
  registry.update(_STAGING_REGISTRY_BETA)
  return Stager(registry)


def GetNoopStager():
  """Get a stager with an empty registry."""
  return Stager({})
