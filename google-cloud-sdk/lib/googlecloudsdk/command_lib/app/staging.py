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
import abc
import cStringIO
import os
import re
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


class StagingCommandNotFoundError(exceptions.Error):
  """Base error indicating that a staging command could not be found."""


class NoSdkRootError(StagingCommandNotFoundError):

  def __init__(self):
    super(NoSdkRootError, self).__init__(
        'No SDK root could be found. Please check your installation.')


class StagingCommandFailedError(exceptions.Error):

  def __init__(self, args, return_code, output_message):
    super(StagingCommandFailedError, self).__init__(
        'Staging command [{0}] failed with return code [{1}].\n\n{2}'.format(
            ' '.join(args), return_code, output_message))


# TODO(b/65026284): eliminate "mappers" entirely by making a shim command
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
  java_bin = java.RequireJavaInstalled('local staging for java')
  args = ([java_bin, '-classpath', command_path, _JAVA_APPCFG_ENTRY_POINT] +
          _JAVA_APPCFG_STAGE_FLAGS + ['stage', app_dir, staging_dir])
  return args


class _Command(object):
  """Interface for a staging command to be invoked on the user source.

  This abstract class facilitates running an executable command that conforms to
  the "staging command" interface outlined in the module docstring.

  It implements the parts that are common to any such command while allowing
  interface implementors to swap out how the command is created.
  """

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def EnsureInstalled(self):
    """Ensure that the command is installed and available.

    May result in a command restart if installation is required.
    """
    raise NotImplementedError()

  @abc.abstractmethod
  def GetPath(self):
    """Returns the path to the command.

    Returns:
      str, the path to the command

    Raises:
      StagingCommandNotFoundError: if the staging command could not be found.
    """
    raise NotImplementedError()

  def GetArgs(self, descriptor, app_dir, staging_dir):
    """Get the args for the command to execute.

    Args:
      descriptor: str, path to the unstaged <service>.yaml or appengine-web.xml
      app_dir: str, path to the unstaged app directory
      staging_dir: str, path to the directory to stage in.

    Returns:
      list of str, the args for the command to run
    """
    return [self.GetPath(), descriptor, app_dir, staging_dir]

  def Run(self, staging_area, descriptor, app_dir):
    """Invokes a staging command with a given <service>.yaml and temp dir.

    Args:
      staging_area: str, path to the staging area.
      descriptor: str, path to the unstaged <service>.yaml or appengine-web.xml
      app_dir: str, path to the unstaged app directory

    Returns:
      str, the path to the staged directory or None if staging was not required.

    Raises:
      StagingCommandFailedError: if the staging command process exited non-zero.
    """
    staging_dir = tempfile.mkdtemp(dir=staging_area)
    args = self.GetArgs(descriptor, app_dir, staging_dir)
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


class NoopCommand(_Command):
  """A command that does nothing.

  Many runtimes do not require a staging step; this isn't a problem.
  """

  def EnsureInstalled(self):
    pass

  def GetPath(self):
    return None

  def GetArgs(self, descriptor, app_dir, staging_dir):
    return None

  def Run(self, staging_area, descriptor, app_dir):
    """Does nothing."""
    pass

  def __eq__(self, other):
    return isinstance(other, NoopCommand)


class _BundledCommand(_Command):
  """Represents a cross-platform command.

  Paths are relative to the Cloud SDK Root directory.

  Attributes:
    _nix_path: str, the path to the executable on Linux and OS X
    _windows_path: str, the path to the executable on Windows
    _component: str or None, the name of the Cloud SDK component which contains
      the executable
    _mapper: fn or None, function that maps a staging invocation to a command.
  """

  def __init__(self, nix_path, windows_path, component=None, mapper=None):
    self._nix_path = nix_path
    self._windows_path = windows_path
    self._component = component
    self._mapper = mapper or None

  @property
  def name(self):
    if platforms.OperatingSystem.Current() is platforms.OperatingSystem.WINDOWS:
      return self._windows_path
    else:
      return self._nix_path

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

  def GetArgs(self, descriptor, app_dir, staging_dir):
    if self._mapper:
      return self._mapper(self.GetPath(), descriptor, app_dir, staging_dir)
    else:
      return super(_BundledCommand, self).GetArgs(descriptor, app_dir,
                                                  staging_dir)

  def EnsureInstalled(self):
    if self._component is None:
      return
    msg = ('The component [{component}] is required for staging this '
           'application.').format(component=self._component)
    update_manager.UpdateManager.EnsureInstalledAndRestart([self._component],
                                                           msg=msg)


class ExecutableCommand(_Command):
  """Represents a command that the user supplies.

  Attributes:
    _path: str, full path to the executable.
  """

  def __init__(self, path):
    self._path = path

  @property
  def name(self):
    os.path.basename(self._path)

  def GetPath(self):
    return self._path

  def EnsureInstalled(self):
    pass

  def GetArgs(self, descriptor, app_dir, staging_dir):
    return [self.GetPath(), descriptor, app_dir, staging_dir]

  @classmethod
  def FromInput(cls, executable):
    """Returns the command corresponding to the user input.

    Could be either of:
    - command on the $PATH or %PATH%
    - full path to executable (absolute or relative)

    Args:
      executable: str, the user-specified staging exectuable to use

    Returns:
      _Command corresponding to the executable

    Raises:
      StagingCommandNotFoundError: if the executable couldn't be found
    """
    try:
      path = files.FindExecutableOnPath(executable)
    except ValueError:
      # If this is a path (e.g. with os.path.sep in the string),
      # FindExecutableOnPath throws an exception
      path = None
    if path:
      return cls(path)

    if os.path.exists(executable):
      return cls(executable)

    raise StagingCommandNotFoundError('The provided staging command [{}] could '
                                      'not be found.'.format(executable))


# Path to the go-app-stager binary
_GO_APP_STAGER_DIR = os.path.join('platform', 'google_appengine')

# Path to the jar which contains the staging command
_APPENGINE_TOOLS_JAR = os.path.join(
    'platform', 'google_appengine', 'google', 'appengine', 'tools', 'java',
    'lib', 'appengine-tools-api.jar')


class RegistryEntry(object):
  """An entry in the Registry.

  Attributes:
    runtime: str or re.RegexObject, the runtime to be staged
    envs: set(util.Environment), the environments to be staged
  """

  def __init__(self, runtime, envs):
    self.runtime = runtime
    self.envs = envs

  def _RuntimeMatches(self, runtime):
    try:
      return self.runtime.match(runtime)
    except AttributeError:
      return self.runtime == runtime

  def _EnvMatches(self, env):
    return env in self.envs

  def Matches(self, runtime, env):
    """Returns True iff the given runtime and environmt match this entry.

    The runtime matches if it is an exact string match.

    The environment matches if it is an exact Enum match or if this entry has a
    "wildcard" (that is, None) for the environment.

    Args:
      runtime: str, the runtime to match
      env: util.Environment, the environment to match

    Returns:
      bool, whether the given runtime and environment match.
    """
    return self._RuntimeMatches(runtime) and self._EnvMatches(env)

  def __hash__(self):
    # Sets are unhashable; Environments are unorderable
    return hash((self.runtime, sum(sorted(map(hash, self.envs)))))

  def __eq__(self, other):
    return self.runtime == other.runtime and self.envs == other.envs

  def __ne__(self, other):
    return not self.__eq__(other)


class Registry(object):
  """A registry of stagers for various runtimes.

  The registry is a map of (runtime, app-engine-environment) to _Command object;
  it should look something like the following:

  STAGING_REGISTRY = {
    RegistryEntry('intercal', {util.Environment.FLEX}):
        _BundledCommand(
            os.path.join('command_dir', 'stage-intercal-flex.sh'),
            os.path.join('command_dir', 'stage-intercal-flex.exe'),
            component='app-engine-intercal'),
    RegistryEntry('x86-asm', {util.Environment.STANDARD}):
        _BundledCommand(
            os.path.join('command_dir', 'stage-x86-asm-standard'),
            os.path.join('command_dir', 'stage-x86-asm-standard.exe'),
            component='app-engine-intercal'),
  }

  Attributes:
    mappings: dict of {RegistryEntry: _Command}, the stagers to use
      per runtime/environment.
    override: _Command or None, if given the registry *always* uses this command
      rather than checking the registry.
  """

  def __init__(self, mappings=None, override=None):
    self.mappings = mappings or {}
    self.override = override

  def Get(self, runtime, env):
    """Return the command to use for the given runtime/environment.

    Args:
      runtime: str, the runtime to get a stager for
      env: util.Environment, the environment to get a stager for

    Returns:
      _Command, the command to use. May be a NoopCommand if no command is
        registered.
    """
    if self.override:
      return self.override

    for entry, command in self.mappings.items():
      if entry.Matches(runtime, env):
        return command
    log.debug(('No staging command found for runtime [%s] and environment '
               '[%s].'), runtime, env.name)
    return NoopCommand()

_STAGING_REGISTRY = {
    RegistryEntry(re.compile(r'(go|go1\..+)$'),
                  {util.Environment.FLEX, util.Environment.STANDARD,
                   util.Environment.MANAGED_VMS}):
        _BundledCommand(
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager'),
            os.path.join(_GO_APP_STAGER_DIR, 'go-app-stager.exe'),
            component='app-engine-go'),
}

# _STAGING_REGISTRY_BETA extends _STAGING_REGISTRY, overriding entries if the
# same key is used.
_STAGING_REGISTRY_BETA = {
    RegistryEntry('java-xml', {util.Environment.STANDARD}):
        _BundledCommand(
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
    command = self.registry.Get(runtime, environment)
    command.EnsureInstalled()
    return command.Run(self.staging_area, descriptor, app_dir)


def GetRegistry():
  return Registry(_STAGING_REGISTRY)


def GetBetaRegistry():
  mappings = _STAGING_REGISTRY.copy()
  mappings.update(_STAGING_REGISTRY_BETA)
  return Registry(mappings)


def GetStager(staging_area):
  """Get the default stager."""
  return Stager(GetRegistry(), staging_area)


def GetBetaStager(staging_area):
  """Get the beta stager, used for `gcloud beta *` commands."""
  return Stager(GetBetaRegistry(), staging_area)


def GetNoopStager(staging_area):
  """Get a stager with an empty registry."""
  return Stager(Registry({}), staging_area)


def GetOverrideStager(command, staging_area):
  """Get a stager with a registry that always calls the given command."""
  return Stager(Registry(None, command), staging_area)
