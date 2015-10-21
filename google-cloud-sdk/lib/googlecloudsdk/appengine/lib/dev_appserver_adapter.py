# Copyright 2014 Google Inc. All Rights Reserved.

"""Package to help the shelling out to the dev_appserver."""

import os
import subprocess
import sys

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

from googlecloudsdk.appengine.lib import util


class Error(exceptions.Error):
  """Exceptions for the dev_appserver_adapter module."""
  pass


class DevappserverExecutionError(Error):
  """An error when devappserver fails."""

  def __init__(self, error_code, argv):
    self.error_code = error_code
    log.debug('Error [{code}] while running DevAppSever with: [{cmd}]'.format(
        code=error_code, cmd=' '.join(argv)))
    msg = 'DevAppSever failed with error code [{code}]'.format(code=error_code)
    super(DevappserverExecutionError, self).__init__(msg)


class DevAppServerAdapter(object):
  """Wrapper for the dev_appserver command line.

  Only use in the context of a "with" statement, since entering messes with
  sys.path.
  """

  def __init__(self, **global_flags):
    """Creates an object to call dev_appserver.py.

    Args:
      **global_flags: {str:str}, A dictionary of global flags to pass to
        dev_appserver on each invocation.

    Raises:
      NoAppengineSDKError, If the App Engine SDK cannot be located.
    """
    self._global_flags = dict(global_flags)
    self.__executable_path = os.path.join(util.GetAppEngineSDKRoot(),
                                          'dev_appserver.py')

    verbosity_string = self.__GetVerbosityString()
    verbosity = log.VALID_VERBOSITY_STRINGS.get(verbosity_string.lower())
    if verbosity is not None:
      log.SetVerbosity(verbosity)
      # This does nothing without the above statement (since we are not
      # shelling out).
      self.AddGlobalFlagIfSet('dev_appserver_log_level', verbosity_string)
      # Set this as a default.  Will be overridden later if the flag is given.
      self.AddGlobalFlagIfSet('log_level', verbosity_string)

  def AddGlobalFlagIfSet(self, name, value):
    """Adds the given flag as a global flag to the dev_appserver call (if set).

    Args:
      name: str, The dev_appserver flag name.
      value: str, The value of the flag.  If None, it will not be passed.
    """
    if value is not None:
      self._global_flags[name] = value

  def _GenerateFlags(self, flag_dict):
    """Turns the dictionary into a list of args for the command line.

    Args:
      flag_dict: {str}, A dictionary of flag names to values.  Any flag that has
        a value of None will be considered a boolean flag.

    Returns:
      [str], The list of arguments for the command line.
    """
    flags = []
    for flag_name, value in sorted(flag_dict.iteritems()):
      value_list = value if isinstance(value, list) else [value]
      for v in value_list:
        flag = '--{flag}{equals_value}'.format(
            flag=flag_name, equals_value='=' + str(v) if v is not None else '')
        flags.append(flag)
    return flags

  def __GetVerbosityString(self):
    """Gets the value for the dev_appserver_log_level flag.

    Returns:
      str, The value to use for the current verbosity setting.  Defaults to
        info.
    """
    verbosity = properties.VALUES.core.verbosity.Get()
    # devappserver does not support higher than critical.
    if verbosity == 'none':
      verbosity = 'critical'
    # TODO(user): This is wrong.  We should not have a different default
    # verbosity for this one command, but there is no good way to get the
    # important INFO level output from devappserver right now.
    # Will default to info if not set.
    return verbosity if verbosity else 'info'

  def Start(self, *positional, **flags):
    """Start the dev_appserver.

    Args:
      *positional: str, The positional arguments to be passed to dev_appserver.
      **flags: str, The flags to be passed to dev_appserver.

    Raises:
      DevappserverExecutionError: If devappserver execution returns an error.
    """
    all_flags = dict(self._global_flags)
    all_flags.update(flags)
    # Don't include the script name in argv because we are hijacking the parse
    # method.
    argv = (self._GenerateFlags(all_flags) +
            [arg for arg in positional if arg is not None])
    log.debug('Running [dev_appserver.py] with: {cmd}'.format(
        cmd=' '.join(argv)))
    run_args = execution_utils.ArgsForPythonTool(self.__executable_path, *argv)
    # TODO(user): Take this out (b/19485297).  This is because the
    # devappserver is depending on our pythonpath right now (it should not in
    # the future (b/19443812).  We need to do this because if something invokes
    # gcloud.py directly, the sys.path is updated but is never put in the env.
    # If you call gcloud.sh then it does put it in the env so this is not
    # required.
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    return_code = subprocess.call(run_args, env=env)
    if return_code != 0:
      raise DevappserverExecutionError(return_code, argv)
