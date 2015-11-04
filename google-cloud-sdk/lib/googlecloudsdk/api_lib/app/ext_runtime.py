# Copyright 2015 Google Inc. All Rights Reserved.
"""Support for externalized runtimes."""

import json
import os
import subprocess
import sys
import threading
import yaml

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log


class PluginInvocationFailed(exceptions.Error):
  """Raised when a plugin invocation returns a non-zero result code."""
  # It's not clear whether this class should be derived from Error or not.  In
  # cases of the canned runtimes, failures of this sort are arguably internal
  # errors, but in the case of externally supported runtimes the correct
  # course of action is "report the error to the owner of the plugin."
  pass


class ExternalRuntimeConfigurator(fingerprinting.Configurator):
  """Configurator for general externalized runtimes.

  Attributes:
    runtime: (ExternalizedRuntime) The runtime that produced this.
    params: (fingerprinting.Params) Runtime parameters.
      data: ({str: object, ...} or None) Optional dictionary of runtime data
        passed back through a runtime_parameters message.
  """

  def __init__(self, runtime, params, data):
    """Constructor.

    Args:
      runtime: (ExternalizedRuntime) The runtime that produced this.
      params: (fingerprinting.Params) Runtime parameters.
      data: ({str: object, ...} or None) Optional dictionary of runtime data
        passed back through a runtime_parameters message.
    """
    self.runtime = runtime
    self.params = params
    self.data = data

  def GenerateConfigs(self):
    # TODO(mmuller): implement GenerateConfigs() (We only define it so lint
    # doesn't give us an error)
    pass


class PluginResult(object):

  def __init__(self):
    self.exit_code = -1
    self.runtime_data = None
    self.docker_context = None
    self.files = []


class _Collector(object):
  """Manages a PluginResult in a thread-safe context."""

  def __init__(self):
    self.result = PluginResult()
    self.lock = threading.Lock()


_LOG_FUNCS = {
    'info': log.info,
    'error': log.error,
    'warn': log.warn,
    'debug': log.debug
}


class ExternalizedRuntime(object):
  """Encapsulates an externalized runtime."""

  def __init__(self, path, config):
    self.root = path
    self.config = config

  @staticmethod
  def Load(path):
    """Loads the externalized runtime from the specified path.

    Args:
      path: (str) root directory of the runtime definition.  Should
        contain a "runtime.yaml" file.

    Returns:
      (ExternalizedRuntime)
    """
    with open(os.path.join(path, 'runtime.yaml')) as f:
      return ExternalizedRuntime(path, yaml.load(f))

  def _ProcessPluginStderr(self, section_name, stderr):
    """Process the standard error stream of a plugin.

    Standard error output is just written to the log at "warning" priority and
    otherwise ignored.

    Args:
      section_name: (str) Section name, to be attached to log messages.
      stderr: (file) Process standard error stream.
    """
    while True:
      line = stderr.readline()
      if not line:
        break
      log.warn('%s: %s' % (section_name, line.rstrip()))

  def _ProcessMessage(self, message, result):
    msg_type = message.get('type')
    if msg_type is None:
      log.error('Missing type in message: %0.80s' % str(message))
    elif msg_type in _LOG_FUNCS:
      _LOG_FUNCS[msg_type](message.get('message'))
    elif msg_type == 'runtime_parameters':
      try:
        result.runtime_data = message['runtime_data']
      except KeyError:
        log.error('Missing [runtime_data] field in runtime_parameters message.')
    # TODO(mmuller): implement remaining message types.
    else:
      log.error('Unknown message type %s' % msg_type)

  def _ProcessPluginPipes(self, section_name, proc, result):
    """Process the standard output and input streams of a plugin."""
    while True:
      line = proc.stdout.readline()
      if not line:
        break

      # Parse and process the message.
      try:
        message = json.loads(line)
        self._ProcessMessage(message, result)
      except ValueError:
        # Unstructured lines get logged as "info".
        log.info('%s: %s' % (section_name, line.rstrip()))

  def _NormalizePath(self, pathname):
    """Get the absolute path from a unix-style relative path.

    Args:
      pathname: (str) A unix-style (forward slash separated) path relative to
        the runtime definition root directory.

    Returns:
      (str) An absolute path conforming to the conventions of the operating
      system.  Note: in order for this to work, 'pathname' must not contain
      any characters with special meaning in any of the targeted operating
      systems.  Keep those names simple.
    """
    components = pathname.split('/')
    return os.path.join(self.root, *components)

  def RunPlugin(self, section_name, plugin_spec, args=None,
                valid_exit_codes=(0,)):
    """Run a plugin.

    Args:
      section_name: (str) Name of the config section that the plugin spec is
        from.
      plugin_spec: ({str: str, ...}) A dictionary mapping plugin locales to
        script names
      args: ([str, ...] or None) Command line arguments for the plugin.
      valid_exit_codes: (int, ...) Exit codes that will be accepted without
        raising an exception.

    Returns:
      (PluginResult) A bundle of the exit code and data produced by the plugin.

    Raises:
      PluginInvocationFailed: The plugin terminated with a non-zero exit code.
    """
    # TODO(mmuller): Support other script types.
    if plugin_spec.has_key('python'):
      normalized_path = self._NormalizePath(plugin_spec['python'])

      # We're sharing 'result' with the output collection thread, we can get
      # away with this without locking because we pass it into the thread at
      # creation and do not use it again until after we've joined the thread.
      result = PluginResult()

      p = subprocess.Popen([execution_utils.GetPythonExecutable(),
                            normalized_path] + (args if args else []),
                           stdout=subprocess.PIPE,
                           stdin=subprocess.PIPE,
                           stderr=subprocess.PIPE)
      stderr_thread = threading.Thread(target=self._ProcessPluginStderr,
                                       args=(section_name, p.stderr,))
      stderr_thread.start()
      stdout_thread = threading.Thread(target=self._ProcessPluginPipes,
                                       args=(section_name, p, result))
      stdout_thread.start()

      stderr_thread.join()
      stdout_thread.join()
      exit_code = p.wait()
      result.exit_code = exit_code
      if exit_code not in valid_exit_codes:
        raise PluginInvocationFailed('Failed during execution of plugin %s '
                                     'for section %s of runtime %s. rc = %s' %
                                     (normalized_path, section_name,
                                      self.config.get('name', 'unknown'),
                                      exit_code))
      return result
    else:
      log.error('No usable plugin type found for %s' % section_name)

  def Detect(self, params, path):
    """Determine if 'path' contains an instance of the runtime type.

    Checks to see if the 'path' directory looks like an instance of the
    runtime type.

    Args:
      params: (fingerprinting.Params) Parameters used by the framework.
      path: (str) The path name.

    Returns:
      (fingerprinting.Configurator) An object containing parameters inferred
        from source inspection.
    """
    if self.config.has_key('detect'):
      result = self.RunPlugin('detect', self.config['detect'], [path], (0, 1))
      if result.exit_code:
        return None
      else:
        return ExternalRuntimeConfigurator(self, params, result.runtime_data)

    else:
      return None
