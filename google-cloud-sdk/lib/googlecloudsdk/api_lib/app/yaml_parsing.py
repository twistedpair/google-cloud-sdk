# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Module to parse .yaml files for an appengine app."""

import os

from googlecloudsdk.api_lib.app import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.appengine.api import appinfo
from googlecloudsdk.third_party.appengine.api import appinfo_errors
from googlecloudsdk.third_party.appengine.api import appinfo_includes
from googlecloudsdk.third_party.appengine.api import croninfo
from googlecloudsdk.third_party.appengine.api import dispatchinfo
from googlecloudsdk.third_party.appengine.api import dosinfo
from googlecloudsdk.third_party.appengine.api import queueinfo
from googlecloudsdk.third_party.appengine.api import validation
from googlecloudsdk.third_party.appengine.api import yaml_errors
from googlecloudsdk.third_party.appengine.datastore import datastore_index


HINT_PROJECT = ('Project name should instead be specified either by '
                '`gcloud config set project MY_PROJECT` or by setting the '
                '`--project` flag on individual command executions.')

HINT_VERSION = ('Versions are generated automatically by default but can also '
                'be manually specified by setting the `--version` flag on '
                'individual command executions.')


class Error(exceptions.Error):
  """A base error for this module."""
  pass


class AppConfigSetLoadError(Error):
  """An exception for when the set of configurations are not valid."""

  def __init__(self):
    """Creates a new Error."""
    super(AppConfigSetLoadError, self).__init__(
        'Errors occurred while parsing the App Engine app configuration.')


class YamlParseError(Error):
  """An exception for when a specific yaml file is not well formed."""

  def __init__(self, file_path, e):
    """Creates a new Error.

    Args:
      file_path: str, The full path of the file that failed to parse.
      e: Exception, The exception that was originally raised.
    """
    super(YamlParseError, self).__init__(
        'An error occurred while parsing file: [{file_path}]\n{err}'
        .format(file_path=file_path, err=e))


class YamlValidationError(Error):
  """An exception for when a specific yaml file has invalid info."""
  pass


class AppConfigError(Error):
  """Errors in Application Config."""


class _YamlInfo(object):
  """A base class for holding some basic attributes of a parsed .yaml file."""

  def __init__(self, file_path, parsed):
    """Creates a new _YamlInfo.

    Args:
      file_path: str, The full path the file that was parsed.
      parsed: The parsed yaml data as one of the *_info objects.
    """
    self.file = file_path
    self.parsed = parsed

  @staticmethod
  def _ParseYaml(file_path, parser):
    """Parses the given file using the given parser.

    Args:
      file_path: str, The full path of the file to parse.
      parser: str, The parser to use to parse this yaml file.

    Returns:
      The result of the parse.
    """
    with open(file_path, 'r') as fp:
      return parser(fp)


class ConfigYamlInfo(_YamlInfo):
  """A class for holding some basic attributes of a parsed config .yaml file."""

  CRON = 'cron'
  DISPATCH = 'dispatch'
  DOS = 'dos'
  INDEX = 'index'
  QUEUE = 'queue'

  CONFIG_YAML_PARSERS = {
      CRON: croninfo.LoadSingleCron,
      DISPATCH: dispatchinfo.LoadSingleDispatch,
      DOS: dosinfo.LoadSingleDos,
      INDEX: datastore_index.ParseIndexDefinitions,
      QUEUE: queueinfo.LoadSingleQueue,
  }

  def __init__(self, file_path, config, parsed):
    """Creates a new ConfigYamlInfo.

    Args:
      file_path: str, The full path the file that was parsed.
      config: str, The name of the config that was parsed (i.e. 'cron')
      parsed: The parsed yaml data as one of the *_info objects.
    """
    super(ConfigYamlInfo, self).__init__(file_path, parsed)
    self.config = config

  @staticmethod
  def FromFile(file_path):
    """Parses the given config file.

    Args:
      file_path: str, The full path to the config file.

    Raises:
      YamlParseError: If the file is not valid.

    Returns:
      A ConfigYamlInfo object for the parsed file.
    """
    (base, _) = os.path.splitext(os.path.basename(file_path))
    parser = ConfigYamlInfo.CONFIG_YAML_PARSERS.get(base)
    if not parser:
      return None
    try:
      parsed = _YamlInfo._ParseYaml(file_path, parser)
      if not parsed:
        raise YamlParseError(file_path, 'The file is empty')
    except (yaml_errors.Error, validation.Error) as e:
      raise YamlParseError(file_path, e)

    _CheckIllegalAttribute(
        name='application',
        yaml_info=parsed,
        extractor_func=lambda yaml: yaml.application,
        file_path=file_path,
        msg=HINT_PROJECT)

    return ConfigYamlInfo(file_path, config=base, parsed=parsed)


class ServiceYamlInfo(_YamlInfo):
  """A class for holding some basic attributes of a parsed service yaml file."""
  DEFAULT_SERVICE_NAME = 'default'

  def __init__(self, file_path, parsed):
    """Creates a new ServiceYamlInfo.

    Args:
      file_path: str, The full path the file that was parsed.
      parsed: appinfo.AppInfoExternal, parsed Application Configuration.
    """
    super(ServiceYamlInfo, self).__init__(file_path, parsed)
    self.module = parsed.module

    # All env: 2 apps are hermetic. All vm: false apps are not hermetic.
    # vm: true apps are hermetic IFF they don't use static files.
    if util.IsFlex(parsed.env):
      self.is_hermetic = True
    elif parsed.vm:
      for urlmap in parsed.handlers:
        if urlmap.static_dir or urlmap.static_files:
          self.is_hermetic = False
          break
      else:
        self.is_hermetic = True
    else:
      self.is_hermetic = False

    self.is_vm = parsed.runtime == 'vm' or self.is_hermetic
    self.runtime = (parsed.GetEffectiveRuntime()
                    if self.is_vm else parsed.runtime)
    if self.is_vm:
      self._UpdateManagedVMConfig()

  @staticmethod
  def FromFile(file_path):
    """Parses the given service file.

    Args:
      file_path: str, The full path to the service file.

    Raises:
      YamlParseError: If the file is not a valid Yaml-file.
      YamlValidationError: If validation of parsed info fails.

    Returns:
      A ServiceYamlInfo object for the parsed file.
    """
    try:
      parsed = _YamlInfo._ParseYaml(file_path, appinfo_includes.Parse)
    except (yaml_errors.Error, appinfo_errors.Error) as e:
      raise YamlParseError(file_path, e)

    if parsed.runtime == 'vm':
      vm_runtime = parsed.GetEffectiveRuntime()
    else:
      vm_runtime = None
      if parsed.runtime == 'python':
        raise YamlValidationError(
            'Service [{service}] uses unsupported Python 2.5 runtime. '
            'Please use [runtime: python27] instead.'.format(
                service=parsed.module))
      elif parsed.runtime == 'python-compat':
        raise YamlValidationError(
            '"python-compat" is not a supported runtime.')

    if util.IsFlex(parsed.env) and vm_runtime == 'python27':
      raise YamlValidationError(
          'The "python27" is not a valid runtime in env: 2.  '
          'Please use [python-compat] instead.')

    if parsed.module:
      log.warn('The "module" parameter in application .yaml files is '
               'deprecated. Please use the "service" parameter instead.')
    else:
      parsed.module = parsed.service or ServiceYamlInfo.DEFAULT_SERVICE_NAME

    _CheckIllegalAttribute(
        name='application',
        yaml_info=parsed,
        extractor_func=lambda yaml: yaml.application,
        file_path=file_path,
        msg=HINT_PROJECT)

    _CheckIllegalAttribute(
        name='version',
        yaml_info=parsed,
        extractor_func=lambda yaml: yaml.version,
        file_path=file_path,
        msg=HINT_VERSION)

    return ServiceYamlInfo(file_path, parsed)

  def RequiresImage(self):
    """Returns True if we'll need to build a docker image."""
    return self.is_vm

  def _UpdateManagedVMConfig(self):
    """Overwrites vm_settings for App Engine Flexible services.

    Sets has_docker_image to be always True. Required for transition period
    until all images in production are pushed via gcloud (and therefore all
    builds happen locally in the SDK).

    Also sets module_yaml_path which is needed for some runtimes.

    Raises:
      AppConfigError: if the function was called for the service which is not an
        App Engine Flexible service.
    """
    if not self.is_vm:
      raise AppConfigError('This is not an App Engine Flexible service. '
                           'The `vm` field is not set to `true`.')
    if not self.parsed.vm_settings:
      self.parsed.vm_settings = appinfo.VmSettings()
    self.parsed.vm_settings['has_docker_image'] = True
    self.parsed.vm_settings['module_yaml_path'] = os.path.basename(self.file)


def _CheckIllegalAttribute(name, yaml_info, extractor_func, file_path, msg=''):
  """Validates that an illegal attribute is not set.

  Args:
    name: str, The name of the attribute in the yaml files.
    yaml_info: AppInfoExternal, The yaml to validate.
    extractor_func: func(AppInfoExternal)->str, A function to extract the
      value of the attribute from a _YamlInfo object.
    file_path: str, The path of file from which yaml_info was parsed.
    msg: str, Message to couple with the error

  Raises:
      YamlValidationError: If illegal attribute is set.

  """
  attribute = extractor_func(yaml_info)
  if attribute is not None:
    # Disallow use of the given attribute.
    raise YamlValidationError(
        'The [{0}] field is specified in file [{1}]. This field is not used '
        'by gcloud and must be removed. '.format(name, file_path) + msg)


class AppConfigSet(object):
  """Parses and holds information about the set of config files for an app."""
  YAML_EXTS = ['.yaml', '.yml']
  IGNORED_YAMLS = ['backends']

  def __init__(self, files):
    """Creates a new AppConfigSet.

    This will scan all files and directories in items, parse them, and
    validate their contents.

    Args:
      files: str, The files to load into the config set.

    Raises:
      AppConfigSetLoadError: If validation fails on the given files.
      YamlParserError: If a file fails to parse.
    """
    self.__config_yamls = {}
    self.__service_yamls = {}
    self.__error = False

    for f in files:
      if os.path.isfile(f):
        try:
          if not self.__LoadYamlFile(f):
            self.__Error('File [%s] is not a valid deployable yaml file.', f)
        except YamlValidationError as err:
          self.__Error('{0}'.format(err))
      elif os.path.isdir(f):
        self.__Error('Directories are not supported [%s].  You must provide '
                     'explicit yaml files.', f)
      else:
        self.__Error(
            'File [%s] not found.', f)

    if self.__error:
      raise AppConfigSetLoadError()

  def __Error(self, *args, **kwargs):
    log.error(*args, **kwargs)
    self.__error = True

  def Services(self):
    """Gets the services that were found.

    Returns:
      {str, ServiceYamlInfo}, A mapping of service name to definition.
    """
    return dict(self.__service_yamls)

  def HermeticServices(self):
    """Gets the hermetic services that were found.

    Returns:
      {str, ServiceYamlInfo}, A mapping of service name to definition.
    """
    return dict((key, srv) for (key, srv) in self.__service_yamls.iteritems()
                if srv.is_hermetic)

  def NonHermeticServices(self):
    """Gets the non-hermetic services that were found.

    Returns:
      {str, ServiceYamlInfo}, A mapping of service name to definition.
    """
    return dict((key, mod) for (key, mod) in self.__service_yamls.iteritems()
                if not mod.is_hermetic)

  def Configs(self):
    """Gets the configs that were found.

    Returns:
      {str, ConfigYamlInfo}, A mapping of config name to definition.
    """
    return dict(self.__config_yamls)

  def __IsInterestingFile(self, f):
    """Determines if the given file is something we should try to parse.

    Args:
      f: str, The full path to the file.

    Returns:
      True if the file is a service yaml or a config yaml.
    """
    (base, ext) = os.path.splitext(os.path.basename(f))
    if ext not in AppConfigSet.YAML_EXTS:
      return False  # Not a yaml file.
    if base in AppConfigSet.IGNORED_YAMLS:
      return False  # Something we are explicitly not supporting.
    return True

  def __LoadYamlFile(self, file_path):
    """Loads a single yaml file into a configuration object.

    Args:
      file_path: str, The full path of the file to parse.

    Raises:
      YamlValidationError: If the info in the yaml file is invalid.

    Returns:
      True if the file was valid, False if it is not a valid service or config
      file.
    """
    file_path = os.path.abspath(file_path)
    if not self.__IsInterestingFile(file_path):
      return False

    yaml = ConfigYamlInfo.FromFile(file_path)
    if yaml:
      existing_config = self.__config_yamls.get(yaml.config)
      if existing_config:
        self.__Error('Found multiple files for config [%s]: [%s, %s]',
                     yaml.config, self.__RelPath(yaml),
                     self.__RelPath(existing_config))
      else:
        self.__config_yamls[yaml.config] = yaml
    else:
      yaml = ServiceYamlInfo.FromFile(file_path)
      existing_service = self.__service_yamls.get(yaml.module)
      if existing_service:
        self.__Error('Found multiple files declaring service [%s]: [%s, %s]',
                     yaml.module, self.__RelPath(yaml),
                     self.__RelPath(existing_service))
      else:
        self.__service_yamls[yaml.module] = yaml

    return True

  def __RelPath(self, yaml):
    # We are going to display full file paths for now.
    return yaml.file
