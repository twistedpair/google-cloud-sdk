# Copyright 2015 Google Inc. All Rights Reserved.
"""Support for externalized runtimes."""

import json
import os
import shutil
import subprocess
import sys
import threading
import yaml

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.third_party.appengine.admin.tools.conversion import schema
from googlecloudsdk.third_party.py27 import py27_subprocess as subprocess


class PluginInvocationFailed(exceptions.Error):
  """Raised when a plugin invocation returns a non-zero result code."""
  # It's not clear whether this class should be derived from Error or not.  In
  # cases of the canned runtimes, failures of this sort are arguably internal
  # errors, but in the case of externally supported runtimes the correct
  # course of action is "report the error to the owner of the plugin."
  pass


class InvalidRuntimeDefinition(exceptions.Error):
  """Raised when an inconsistency is found in the runtime definition."""
  pass


class ExternalRuntimeConfigurator(fingerprinting.Configurator):
  """Configurator for general externalized runtimes.

  Attributes:
    runtime: (ExternalizedRuntime) The runtime that produced this.
    params: (fingerprinting.Params) Runtime parameters.
    data: ({str: object, ...} or None) Optional dictionary of runtime data
      passed back through a runtime_parameters message.
    path: (str) Path to the user's source directory.
  """

  def __init__(self, runtime, params, data, path):
    """Constructor.

    Args:
      runtime: (ExternalizedRuntime) The runtime that produced this.
      params: (fingerprinting.Params) Runtime parameters.
      data: ({str: object, ...} or None) Optional dictionary of runtime data
        passed back through a runtime_parameters message.
      path: (str) Path to the user's source directory.
    """
    self.runtime = runtime
    self.params = params
    self.data = data
    self.path = path

  def GenerateConfigs(self):
    return self.runtime.GenerateConfigs(self)


def _NormalizePath(basedir, pathname):
  """Get the absolute path from a unix-style relative path.

  Args:
    basedir: (str) Platform-specific encoding of the base directory.
    pathname: (str) A unix-style (forward slash separated) path relative to
      the runtime definition root directory.

  Returns:
    (str) An absolute path conforming to the conventions of the operating
    system.  Note: in order for this to work, 'pathname' must not contain
    any characters with special meaning in any of the targeted operating
    systems.  Keep those names simple.
  """
  components = pathname.split('/')
  return os.path.join(basedir, *components)


class GeneratedFile(object):

  def __init__(self, filename, contents):
    self.filename = filename
    self.contents = contents

  def WriteTo(self, dest_dir):
    path = _NormalizePath(dest_dir, self.filename)
    if not os.path.exists(path):
      with open(path, 'w') as f:
        f.write(self.contents)
      return path

    return None


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

# A section consisting only of scripts.
_EXEC_SECTION = schema.Message(
    python=schema.Value(converter=str))

_RUNTIME_SCHEMA = schema.Message(
    name=schema.Value(converter=str),
    description=schema.Value(converter=str),
    author=schema.Value(converter=str),
    api_version=schema.Value(converter=str),
    generate_configs=schema.Message(
        python=schema.Value(converter=str),
        files_to_copy=schema.RepeatedField(element=schema.Value(converter=str)),
        ),
    detect=_EXEC_SECTION,
    pre_build=_EXEC_SECTION,
    post_build=_EXEC_SECTION)


class ExternalizedRuntime(object):
  """Encapsulates an externalized runtime."""

  def __init__(self, path, config):
    self.root = path
    try:
      # Do validation up front, after this we can assume all of the types are
      # correct.
      self.config = _RUNTIME_SCHEMA.ConvertValue(config)
    except ValueError as ex:
      raise InvalidRuntimeDefinition(
          'Invalid runtime definition: {0}'.format(ex.message))

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

  def _ProcessMessage(self, plugin_stdin, message, result, params,
                      runtime_data):
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
    elif msg_type == 'gen_file':
      try:
        # TODO(mmuller): deal with 'encoding'
        filename = message['filename']
        contents = message['contents']
        result.files.append(GeneratedFile(filename, contents))
      except KeyError as ex:
        log.error('Missing [%s] field in gen_file message', ex.message)
    elif msg_type == 'get_config':
      response = {'type': 'get_config_response',
                  'params': params.ToDict(),
                  'runtime_data': runtime_data}
      json.dump(response, plugin_stdin)
      plugin_stdin.write('\n')
      plugin_stdin.flush()
    # TODO(mmuller): implement remaining message types.
    else:
      log.error('Unknown message type %s' % msg_type)

  def _ProcessPluginPipes(self, section_name, proc, result, params,
                          runtime_data):
    """Process the standard output and input streams of a plugin."""
    while True:
      line = proc.stdout.readline()
      if not line:
        break

      # Parse and process the message.
      try:
        message = json.loads(line)
        self._ProcessMessage(proc.stdin, message, result, params, runtime_data)
      except ValueError:
        # Unstructured lines get logged as "info".
        log.info('%s: %s' % (section_name, line.rstrip()))

  def RunPlugin(self, section_name, plugin_spec, params, args=None,
                valid_exit_codes=(0,),
                runtime_data=None):
    """Run a plugin.

    Args:
      section_name: (str) Name of the config section that the plugin spec is
        from.
      plugin_spec: ({str: str, ...}) A dictionary mapping plugin locales to
        script names
      params: (fingerprinting.Params or None) Parameters for the plugin.
      args: ([str, ...] or None) Command line arguments for the plugin.
      valid_exit_codes: (int, ...) Exit codes that will be accepted without
        raising an exception.
      runtime_data: ({str: object, ...}) A dictionary of runtime data passed
        back from detect.

    Returns:
      (PluginResult) A bundle of the exit code and data produced by the plugin.

    Raises:
      PluginInvocationFailed: The plugin terminated with a non-zero exit code.
    """
    # TODO(mmuller): Support other script types.
    if plugin_spec.has_key('python'):
      normalized_path = _NormalizePath(self.root, plugin_spec['python'])

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
                                       args=(section_name, p, result,
                                             params, runtime_data))
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

  def Detect(self, path, params):
    """Determine if 'path' contains an instance of the runtime type.

    Checks to see if the 'path' directory looks like an instance of the
    runtime type.

    Args:
      path: (str) The path name.
      params: (fingerprinting.Params) Parameters used by the framework.

    Returns:
      (fingerprinting.Configurator) An object containing parameters inferred
        from source inspection.
    """
    detect = self.config.get('detect')
    if detect:
      result = self.RunPlugin('detect', detect, params, [path], (0, 1))
      if result.exit_code:
        return None
      else:
        return ExternalRuntimeConfigurator(self, params, result.runtime_data,
                                           path)

    else:
      return None

  # The legacy runtimes use "Fingerprint" for this function, the externalized
  # runtime code uses "Detect" to mirror the name in runtime.yaml, so alias it.
  # b/25117700
  Fingerprint = Detect

  def GenerateConfigs(self, configurator):
    """Do config generation on the runtime.

    This should generally be called from the configurator's GenerateConfigs()
    method.

    Args:
      configurator: (ExternalRuntimeConfigurator) The configurator retuned by
        Detect().

    Returns:
      (fingerprinting.Cleaner) The cleaner for the generated files.

    Raises:
      InvalidRuntimeDefinition: For a variety of problems with the runtime
        definition.
    """
    generate_configs = self.config.get('generateConfigs')
    if generate_configs:
      cleaner = fingerprinting.Cleaner()
      files_to_copy = generate_configs.get('filesToCopy')
      if files_to_copy:

        # Make sure there's nothing else.
        if len(generate_configs) != 1:
          raise InvalidRuntimeDefinition('If "files_to_copy" is specified, '
                                         'it must be the only field in '
                                         'generate_configs.')

        for filename in files_to_copy:
          full_name = _NormalizePath(self.root, filename)
          if not os.path.isfile(full_name):
            raise InvalidRuntimeDefinition('File [%s] specified in '
                                           'files_to_copy, but is not in '
                                           'the runtime definition.' %
                                           filename)

          dest_path = _NormalizePath(configurator.path, filename)
          if not os.path.exists(dest_path):
            cleaner.Add(dest_path)
            shutil.copy(full_name, dest_path)
      else:
        result = self.RunPlugin('generate_configs', generate_configs,
                                configurator.params,
                                runtime_data=configurator.data)
        for file_info in result.files:
          dest_filename = file_info.WriteTo(configurator.path)

          # Cleanup everything except app.yaml files - these are never
          # temporary.
          if dest_filename and file_info.filename != 'app.yaml':
            cleaner.Add(dest_filename)

      return cleaner
    else:
      raise InvalidRuntimeDefinition('Runtime definition contains no '
                                     'generate_configs section.')


def _GetRuntimeDefDir():
  sdk_root = config.Paths().sdk_root
  if sdk_root:
    return os.path.join(sdk_root, 'lib', 'googlecloudsdk', 'api_lib', 'app',
                        'ext_runtimes', 'runtime_defs')
  else:
    # Otherwise we cheat and use the directory of this file.
    return os.path.join(os.path.dirname(__file__), 'ext_runtimes',
                        'runtime_defs')


class CoreRuntimeLoader(object):
  """A loader stub for the core runtimes.

  The externalized core runtimes are currently distributed with the cloud sdk.
  This class encapsulates the name of a core runtime to avoid having to load
  it at module load time.  Instead, the wrapped runtime is demand-loaded when
  the Fingerprint() method is called.
  """

  def __init__(self, name, visible_name, allowed_runtime_names):
    self._name = name
    self._rep = None
    self._visible_name = visible_name
    self._allowed_runtime_names = allowed_runtime_names

  # These need to be named this way because they're constants in the
  # non-externalized implementation.  TODO(mmuller) change the names once the
  # old implementation go away.
  # pylint:disable=invalid-name
  @property
  def ALLOWED_RUNTIME_NAMES(self):
    return self._allowed_runtime_names

  # pylint:disable=invalid-name
  @property
  def NAME(self):
    return self._visible_name

  def Fingerprint(self, path, params):
    if not self._rep:
      path_to_runtime = os.path.join(_GetRuntimeDefDir(), self._name)
      self._rep = ExternalizedRuntime.Load(path_to_runtime)
    return self._rep.Fingerprint(path, params)
