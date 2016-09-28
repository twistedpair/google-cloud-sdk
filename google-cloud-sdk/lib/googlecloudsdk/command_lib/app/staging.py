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
  in which to stage the application code. On success, the sole output of the
  staging command is the path to the `<service>.yaml` file of the staged
  service.
- On success, the STDOUT and STDERR of the staging command are logged at the
  INFO level. On failure, a StagingCommandFailedError is raised containing the
  STDOUT and STDERR of the staging command (which are surfaced to the user as an
  ERROR message).
"""
import contextlib
import cStringIO
import os

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

  Attributes:
    nix_name: str, the name of the executable on Linux
    windows_name: str, the name of the executable on Windows
    component: str or None, the name of the Cloud SDK component which contains
      the executable
  """

  def __init__(self, nix_name, windows_name, component=None):
    self.nix_name = nix_name
    self.windows_name = windows_name
    self.component = component

  @property
  def name(self):
    if platforms.OperatingSystem.Current() is platforms.OperatingSystem.WINDOWS:
      return self.windows_name
    else:
      return self.nix_name

  def GetPath(self):
    """Returns the path to the command.

    Returns:
      str, the path to the command

    Raises:
       NoSdkRootError: if no Cloud SDK root could be found (and therefore the
       command is not installed).
    """
    try:
      sdk_bin_path = config.Paths().sdk_bin_path
    except AttributeError:
      raise NoSdkRootError()
    if not sdk_bin_path:
      raise NoSdkRootError()
    return os.path.join(sdk_bin_path, self.name)

  def EnsureInstalled(self):
    if self.component is None:
      return
    msg = ('The component [{component}] is required for staging this '
           'application.').format(component=self.component)
    update_manager.UpdateManager.EnsureInstalledAndRestart([self.component],
                                                           msg=msg)


# STAGING_REGISTRY is a map of (runtime, app-engine-environment) to executable
# name; it should look something like the following:
#
#     from googlecloudsdk.api_lib.app import util
#     STAGING_REGISTRY = {
#       ('intercal', util.Environment.FLEXIBLE):
#           _Command('stage-intercal-flex.sh', 'stage-intercal-flex.cmd',
#                    component='app-engine-intercal'),
#       ('x86-asm', util.Environment.STANDARD):
#           _Command('stage-x86-asm-standard', 'stage-x86-asm-standard.exe')
#     }
_STAGING_REGISTRY = {}


_STAGING_COMMAND_OUTPUT_TEMPLATE = """\
------------------------------------ STDOUT ------------------------------------
{out}\
------------------------------------ STDERR ------------------------------------
{err}\
--------------------------------------------------------------------------------
"""


def _StageUsingGivenCommand(command_path, service_yaml):
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
    yield out.getvalue().strip('\r\n')


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
      str, the path to the `app.yaml` file or None if no corresponding staging
          command was found.

    Raises:
      NoSdkRootError: if no Cloud SDK installation root could be found. The
          staging command binaries are kept in the bin directory of the Cloud
          SDK installation directory.
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
    for app_yaml in _StageUsingGivenCommand(command_path, service_yaml):
      yield app_yaml


def GetStager():
  return Stager(_STAGING_REGISTRY)


def GetNoopStager():
  return Stager({})
