# Copyright 2015 Google Inc. All Rights Reserved.

"""Support functions for handling of named configurations."""


import errno
import logging
import os
import re
import sys

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import files as file_utils


# The special configuration named NONE contains no properties
RESERVED_NAMED_CONFIG_NAME_NONE = 'NONE'
_RESERVED_NAMED_CONFIG_NAMES = (RESERVED_NAMED_CONFIG_NAME_NONE,)

_USER_NAMED_CONFIG_NAME_REGEX = r'[a-z][-a-z0-9]*'


AUTO_UPGRADE_NEW_CONFIG_NAME = 'default'


def _MakeExpectedNamedConfigFilesRegex():
  if not hasattr(_MakeExpectedNamedConfigFilesRegex, 're'):
    _MakeExpectedNamedConfigFilesRegex.re = re.compile(
        r'^{0}({1})$'.format(config.Paths().CLOUDSDK_NAMED_CONFIG_FILE_PREFIX,
                             _USER_NAMED_CONFIG_NAME_REGEX))

  return _MakeExpectedNamedConfigFilesRegex.re


def _WarnOnce(msg):
  """Warn, but only once per unique message."""

  if not hasattr(_WarnOnce, 'messages_already_emited'):
    _WarnOnce.messages_already_emited = set()

  if msg in _WarnOnce.messages_already_emited:
    return

  logging.warning(msg)
  _WarnOnce.messages_already_emited.add(msg)


def _OSErrorReason(exp):
  """Provide a "pretty" explanation of an OSError even if strerror unset.

  Args:
    exp: OSError, an exception object to explain

  Returns:
    str, a string explaing exp, 'unknown' when we can't do better.
  """
  return getattr(exp, 'strerror', None) or 'unknown'


class NamedConfigError(config.Error):
  """Base class for errors handling named configurations."""


class NamedConfigLoadError(NamedConfigError):
  """Raise for errors finding or reading the user's active named config."""


class NamedConfigWriteError(NamedConfigError):
  """Raise for errors creating or updating a named config."""


class InvalidNameConfigName(NamedConfigError):
  """Raise to indicate an invalid named config name."""

  def __init__(self, bad_name):
    super(InvalidNameConfigName, self).__init__(
        'Invalid name [{0}] for a configuration.  Except for special cases '
        '({1}), configuration names start with a lower case letter and '
        'contain only lower case letters a-z, digits 0-9, '
        'and hyphens \'-\'.'.format(bad_name,
                                    ','.join(_RESERVED_NAMED_CONFIG_NAMES)))


def IsNamedConfigNameValid(name):
  """Returns True if name is a valid config name; False otherwise."""

  if type(name) is not str:
    raise ValueError('IsNamedConfigNameValid got argument of type [{0}]. '
                     'str expected.'.format(name))

  if name in _RESERVED_NAMED_CONFIG_NAMES:
    return True

  return re.match(_USER_NAMED_CONFIG_NAME_REGEX, name) is not None


def _ValidateWarnAndRecoverConfigName(name):
  """Return name if well-formed, otherwise warn and return 'NONE'."""

  if IsNamedConfigNameValid(name):
    return name

  _WarnOnce('Invalid configuration name [{0}]. '
            'Using empty configuration.'.format(name))

  return RESERVED_NAMED_CONFIG_NAME_NONE


def _ValidateConfigNameOrRaise(name):
  """Noop if name is well-formed, otherwise raise InvalidNameConfigName."""

  if IsNamedConfigNameValid(name):
    return

  raise InvalidNameConfigName(name)


class _ConfigurationFlagOverrideStack(object):
  """Class representing a stack of configuration flag values or `None`s.

  This is lax in the following sense.  You can push invalid configuration names
  into stack, and bad ones will be ignored on lookup (GetEffectiveFlag).  This
  is intended to allow the following control flow:
    1. Do an initial, ad-hoc scan of sys.args for --configuration flags
    2. Use the configuration flag (if any) in resolving properties
    3. Use the properties module to init logging
    4. Have logging correctly set up before argparse runs
    5. Report errors, including with --configuration, using correctly
         configured gcloud log module.
  """

  def __init__(self):
    self._contents = []
    self._on_update = None

  def AllocateFrame(self):
    self._contents.append(None)

  def Push(self, config_flag, on_update=None):
    self.AllocateFrame()
    self.ReplaceTop(config_flag, on_update)

  def ReplaceTop(self, config_flag, on_update=None):
    old_effective_flag = self.GetEffectiveFlag()
    self._contents[-1] = config_flag
    new_effective_flag = self.GetEffectiveFlag()
    if (old_effective_flag != new_effective_flag) and on_update:
      on_update()

  def Peek(self):
    return self._contents[-1]

  def Pop(self):
    return self._contents.pop()

  def GetEffectiveFlag(self):
    flag = next((c for c in reversed(self._contents) if c is not None), None)
    eflag = (_ValidateWarnAndRecoverConfigName(flag) if flag else None)
    return eflag


FLAG_OVERRIDE_STACK = _ConfigurationFlagOverrideStack()


def AdhocConfigFlagParse(args=None):
  """Quick and dirty parsing --configuration flag.

  This method is a hack to bookstrap the following:
    - Argument parsing uses logging for output.
    - Logging is configured by properties.
    - Properties may be set by the --configuration flag.

  The intended use of the this method is to get a quick and dirty value to
  use to bring properties.  It never fails.  Bogus or unparsable args
  are ignored.

  Args:
    args: The arguments from the command line or None to use sys.argv

  Returns:
    str, CowboyParse([..., '--configuration', s, ...rhs...]) = s and
         CowboyParse([..., '--configuration=s', ...rhs...]) = s
         when rhs doesn't contain the string '--configuration' or a string
         starting with '--configuration='
    None, otherwise
  """

  args = args or sys.argv

  flag = '--configuration'
  flag_eq = flag + '='

  successor = None
  config_flag = None

  # Try to parse arguments going right to left(!).  This is so that if
  # if a user runs someone does
  #    $ alias g=gcloud --configuration foo compute
  #    $ g --configuration bar ssh
  # we'll pick up configuration bar instead of foo.
  for arg in reversed(args):
    if arg == flag:
      config_flag = successor
      break
    if arg.startswith(flag_eq):
      _, config_flag = arg.split('=', 1)
      break
    successor = arg

  return config_flag


def GetNameOfActiveNamedConfig():
  """The (validated) name of the active named config, or else None."""

  flag_setting = FLAG_OVERRIDE_STACK.GetEffectiveFlag()
  if flag_setting:
    return flag_setting

  maybe_named_config_name_from_env = os.getenv(
      config.CLOUDSDK_ACTIVE_CONFIG_NAME)
  if maybe_named_config_name_from_env is not None:
    return _ValidateWarnAndRecoverConfigName(maybe_named_config_name_from_env)

  return ReadActivatorFile()


def GetNamedConfigDirectory():
  return os.path.join(config.Paths().global_config_dir,
                      config.Paths().CLOUDSDK_NAMED_CONFIG_DIRECTORY)


def GetPathForConfigName(config_name):

  _ValidateConfigNameOrRaise(config_name)

  if config_name == RESERVED_NAMED_CONFIG_NAME_NONE:
    return os.devnull

  return os.path.join(
      GetNamedConfigDirectory(),
      config.Paths().CLOUDSDK_NAMED_CONFIG_FILE_PREFIX + config_name)


def GetFileForActiveNamedConfig():
  """The path to the active named config.

  Returns:
    str, a file name for the currently active config setting.  Note that if
    if the config active is not set (or set to NONE) this returns os.devnull
    instead of a separate sentinal value so that clients don't need to handle
    that case specially.
  """

  config_name = GetNameOfActiveNamedConfig()

  if config_name is None:
    return os.devnull

  return GetPathForConfigName(config_name)


def ReadActivatorFile(silent=False):
  """Gets the name of the user's active named config or returns None.

  Args:
    silent: boolean, suppress all warnings

  Returns:
    str, The path to the file.
    None, If there is no active named configuration
  """

  path = config.Paths().named_config_activator_path

  try:
    with open(path, 'r') as f:
      potential_named_config_name = f.read()
      return _ValidateWarnAndRecoverConfigName(potential_named_config_name)
  except IOError as err:
    if err.errno != errno.ENOENT and not silent:
      # something's gone wrong, report it
      _WarnOnce(
          'Failed to open configuration file [{0}] because [{1}].'.format(
              path, _OSErrorReason(err)))

  # The active named config pointer file is missing, return None
  return None


def GetEffectiveNamedConfigFile():
  """The path to the named config with fallback for legacy-mode clients.

  Returns:
    str, a file name for the currently active config setting.  Possible options
    include the legacy global configuration, a named configuration file,
    or os.devnull.  (N.B.  Returning /dev/null (or NUL on Windows) allows
    clients to handle config files without considering special sentinel values.
  """
  if not GetNameOfActiveNamedConfig():
    # If the active named config isn't set return the legacy global
    # properties file path, whether or not a file there exists.
    return config.Paths().user_properties_path

  return GetFileForActiveNamedConfig()


def _TryInterpretFnameAsNamedConfig(fname, warn):
  """Get the name of the config corresponding to fname.

  Args:
    fname: str, a file name
    warn: bool, True to log warnings

  Returns:
    str, the name of named config corresponding to fname -or-
    None, if fname is a filename correspoding to a valid named configurations
  """

  named_config_dir = GetNamedConfigDirectory()
  path = os.path.join(named_config_dir, fname)
  if not os.path.isfile(path):
    if warn:
      logging.warn('Unexpected non-file object [%s] in [%s].',
                   fname, named_config_dir)
    return None

  match = re.match(_MakeExpectedNamedConfigFilesRegex(), fname)

  if match is None:
    if warn:
      logging.warn('Unexpected file [%s] in [%s].', fname, named_config_dir)
    return None

  return match.group(1)


def _ListDirIfExists(path):
  try:
    return os.listdir(path)
  except OSError as exp:
    if exp.errno != errno.ENOENT:
      raise

  return []


class NamedConfig(object):

  def __init__(self, name, is_active):
    self.name = name
    self.is_active = is_active


def ListNamedConfigs(log_warnings=False):
  """Finds the current set of named configurations.

  Args:
    log_warnings: bool, print warings to logging.warn

  Returns:
    A tuple of NamedConfigs
  """
  config_dir = GetNamedConfigDirectory()

  try:
    config_files = _ListDirIfExists(config_dir)
  except OSError as exp:
    if log_warnings:
      logging.warning('Unexpectedly can\'t list [%s]: [%s].',
                      config_dir, _OSErrorReason(exp))
    return tuple()

  l = [_TryInterpretFnameAsNamedConfig(f, log_warnings) for f in config_files]
  configs = (x for x in l if x is not None)

  active_config = GetNameOfActiveNamedConfig()
  configs_formatted = tuple(NamedConfig(c, active_config == c) for c in configs)

  return configs_formatted


def IsPathReadable(path):
  """Check if a path is readable, avoiding os.access (buggy on windows)."""

  try:
    with open(path, 'r'):
      pass
  except IOError:
    return False

  return True


def _EnsureDir(dir_name):
  msg_template = ('Config directory [{0}] missing and '
                  'cannot be created because [{1}].')
  try:
    file_utils.MakeDir(dir_name)
  except OSError as exp:
    raise NamedConfigWriteError(
        msg_template.format(dir_name, _OSErrorReason(exp)))
  except file_utils.Error as exp:
    raise NamedConfigWriteError(msg_template.format(dir_name, exp.message))


def CreateNamedConfig(name):
  """Creates a named config."""

  _ValidateConfigNameOrRaise(name)

  if name in _RESERVED_NAMED_CONFIG_NAMES:
    raise NamedConfigWriteError(
        'Cannot create configuration with reserved name [{0}]'.format(name))

  if name in [c.name for c in ListNamedConfigs()]:
    raise NamedConfigWriteError(
        'Cannot create configuration with name [{0}] because a configuration '
        'with that name already exists.'.format(name))

  _EnsureDir(GetNamedConfigDirectory())
  new_fname = GetPathForConfigName(name)

  f = None
  flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
  try:
    f = os.open(new_fname, flags)
  except OSError as exp:
    raise NamedConfigWriteError(
        'Could not create new named configuration '
        'file [{0}] because [{1}]'.format(new_fname, _OSErrorReason(exp)))
  finally:
    if f:
      os.close(f)


def ActivateNamedConfig(name):
  """Activates an existing named configuration."""

  _ValidateConfigNameOrRaise(name)

  configs = tuple(c.name for c in ListNamedConfigs())
  if name not in configs + _RESERVED_NAMED_CONFIG_NAMES:
    raise NamedConfigWriteError(
        'Activating named configuration failed because configuration '
        '[{0}] cannot be found.'.format(name))

  config_path = GetPathForConfigName(name)
  if not IsPathReadable(config_path):
    raise NamedConfigWriteError(
        'Activating named configuration failed because configuration '
        'file [{0}] is missing or cannot be read.'.format(config_path))

  _EnsureDir(config.Paths().global_config_dir)
  activator_path = config.Paths().named_config_activator_path

  try:
    with open(activator_path, 'w') as f:
      f.write(name)
  except IOError as exp:
    raise NamedConfigWriteError(
        'Activating named configuration failed when writing '
        'file [{0}] because [{1}]'.format(activator_path, _OSErrorReason(exp)))

  if ReadActivatorFile(silent=True) != name:
    # Fail rather than erronously report success.  Should be dead code.
    raise exceptions.InternalError('Configuration creation or activation '
                                   'failed for an unknown reason.')


def DeleteNamedConfig(name):
  """Deletes an existing named configuration.

  Args:
    name: str, the name of the configuration to delete

  Returns:
    None

  Raises:
    NamedConfigWriteError: on delete failure
    InvalidNameConfigName: if name is not a valid configuration name
  """

  _ValidateConfigNameOrRaise(name)

  # Fail the delete operation when we're attempting to delete the
  # active config.
  if GetNameOfActiveNamedConfig() == name:
    raise NamedConfigWriteError(
        'Deleting named configuration failed because configuration '
        '[{0}] is set as active.  Use `gcloud config configurations '
        'activate` to change the active configuration.'.format(name))

  # Also fail if we're attempting to delete the configuration that the file
  # system thinks is active, even if that's overriden by a flag or
  # environment variable.  This avoids leaving gcloud in an invalid state.
  if ReadActivatorFile(silent=True) == name:
    raise NamedConfigWriteError(
        'Deleting named configuration failed because configuration '
        '[{0}] is set as active in your persistent gcloud properties. '
        'Use `gcloud config configurations '
        'activate` to change the active configuration.'.format(name))

  config_path = GetPathForConfigName(name)
  try:
    os.remove(config_path)
  except OSError as exp:
    if exp.errno == errno.ENOENT:
      raise NamedConfigWriteError(
          'Deleting named configuration failed because configuration '
          '[{0}] cannot be found.'.format(name))
    else:
      raise NamedConfigWriteError(
          'Deleting named configuration failed when deleting '
          'file [{0}] because [{1}]'.format(config_path, _OSErrorReason(exp)))


def WarnOnActiveNamedConfigMissing():
  """Perform a quick and dirty check to warn on missing config file."""

  name = GetNameOfActiveNamedConfig()
  if not name:
    return

  fname = GetFileForActiveNamedConfig()

  if IsPathReadable(fname):
    return

  _WarnOnce(
      'File [{0}] missing or unreadable for configuration [{1}].'.format(
          fname, name))


def TryEnsureWriteableNamedConfig():
  """Create a named config for new/legacy users.

  Returns: None

  Raises:
      IOError, if there's a problem creating a new configuration.
  """

  # Don't try to update if the user has named configs.  LHS side of the `or`
  # helps if an otherwise new user has --configuration NONE.  The RHS if a
  # user has named configs but has deleted their activator file.  (Let's not
  # mess with their state any more in the latter case.)
  if GetNameOfActiveNamedConfig() or ListNamedConfigs():
    return

  logging.warn('Creating and activating new configuration [%s].',
               AUTO_UPGRADE_NEW_CONFIG_NAME)

  CreateNamedConfig(AUTO_UPGRADE_NEW_CONFIG_NAME)

  legacy_properties = None
  try:
    with open(config.Paths().user_properties_path, 'r+') as f:
      legacy_properties = f.read()
      f.truncate(0)
      f.seek(0)
      f.write('# This properties file has been superseded by named\n'
              '# configurations.  Editing it will have no effect.\n\n')
      f.write(legacy_properties)
  except IOError:
    # Best effort read and update of old properties file.
    pass

  if legacy_properties is not None:
    logging.warn('Importing legacy user properties.')
    with open(GetPathForConfigName(AUTO_UPGRADE_NEW_CONFIG_NAME), 'w') as ff:
      ff.write(legacy_properties)

  ActivateNamedConfig(AUTO_UPGRADE_NEW_CONFIG_NAME)
