# Copyright 2014 Google Inc. All Rights Reserved.

"""Module to parse .yaml files for an appengine app."""

import os

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
    self.project = parsed.application

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
  def FromFile(file_path, project):
    """Parses the given config file.

    Args:
      file_path: str, The full path to the config file.
      project: str, The project being using by gcloud.

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

    parsed.application = _CheckAttribute(
        name='application',
        gcloud_name='project',
        warn_remove=True,
        yaml_info=parsed,
        extractor_func=lambda yaml: yaml.application,
        file_path=file_path,
        current_value=project)

    return ConfigYamlInfo(file_path, config=base, parsed=parsed)


class ModuleYamlInfo(_YamlInfo):
  """A class for holding some basic attributes of a parsed module .yaml file."""
  DEFAULT_MODULE_NAME = 'default'

  def __init__(self, file_path, parsed):
    """Creates a new ModuleYamlInfo.

    Args:
      file_path: str, The full path the file that was parsed.
      parsed: appinfo.AppInfoExternal, parsed Application Configuration.
    """
    super(ModuleYamlInfo, self).__init__(file_path, parsed)
    self.version = parsed.version
    self.module = parsed.module
    self.is_hermetic = bool(parsed.env == '2')
    self.is_vm = parsed.runtime == 'vm' or self.is_hermetic
    self.runtime = (parsed.GetEffectiveRuntime()
                    if self.is_vm else parsed.runtime)
    if self.is_vm:
      self._UpdateManagedVMConfig()

  @staticmethod
  def FromFile(file_path, project, version, check_version):
    """Parses the given module file.

    Args:
      file_path: str, The full path to the module file.
      project: str, The project being using by gcloud.
      version: str, The version being used by gcloud
      check_version: bool, Whether the version info should be validated.

    Raises:
      YamlParseError: If the file is not valid.
      YamlValidationError: If validation of parsed info fails.

    Returns:
      A ModuleYamlInfo object for the parsed file.
    """
    try:
      parsed = _YamlInfo._ParseYaml(file_path, appinfo_includes.Parse)
    except (yaml_errors.Error, appinfo_errors.Error) as e:
      raise YamlParseError(file_path, e)

    if parsed.runtime == 'vm':
      vm_runtime = parsed.GetEffectiveRuntime()
    else:
      vm_runtime = None

    if parsed.env == '2':
      if vm_runtime == 'python27':
        raise YamlValidationError(
            'The "python27" is not a valid runtime in env: 2.  '
            'Please use [python-compat] instead.')
    else:
      if parsed.runtime == 'python' or vm_runtime == 'python':
        raise YamlValidationError(
            'Module [{module}] uses unsupported Python 2.5 runtime. '
            'Please use [runtime: python27] instead.'.format(
                module=parsed.module))
      elif parsed.runtime == 'python-compat' or vm_runtime == 'python-compat':
        raise YamlValidationError(
            '"python-compat" is not a supported runtime.')

    if not parsed.module:
      parsed.module = ModuleYamlInfo.DEFAULT_MODULE_NAME

    parsed.application = _CheckAttribute(
        name='application',
        gcloud_name='project',
        warn_remove=True,
        yaml_info=parsed,
        extractor_func=lambda yaml: yaml.application,
        file_path=file_path,
        current_value=project)

    if check_version:
      parsed.version = _CheckAttribute(
          name='version',
          gcloud_name='version',
          warn_remove=True,
          yaml_info=parsed,
          extractor_func=lambda yaml: yaml.version,
          file_path=file_path,
          current_value=version)

    return ModuleYamlInfo(file_path, parsed)

  def RequiresImage(self):
    """Returns True if we'll need to build a docker image."""
    return self.is_vm

  def _UpdateManagedVMConfig(self):
    """Overwrites vm_settings for Managed VMs modules.

    Sets has_docker_image to be always True. Required for transition period
    until all images in production are pushed via gcloud (and therefore all
    builds happen locally in the SDK).

    Also sets module_yaml_path which is needed for some runtimes.

    Raises:
      AppConfigError: if the function was called for the module which is not a
        Managed VM module.
    """
    if not self.is_vm:
      raise AppConfigError('This is not a Managed VM module. vm != True')
    if not self.parsed.vm_settings:
      self.parsed.vm_settings = appinfo.VmSettings()
    self.parsed.vm_settings['has_docker_image'] = True
    self.parsed.vm_settings['module_yaml_path'] = os.path.basename(self.file)


def _CheckAttribute(name, gcloud_name, warn_remove, yaml_info, extractor_func,
                    file_path, current_value):
  """Validates a single attribute against its parsed value.

  Args:
    name: str, The name of the attribute in the yaml files.
    gcloud_name: str, The name of the attribute as gcloud refers to it.
    warn_remove: bool, True to warn the user to remove the attribute if it is
      present.
    yaml_info: AppInfoExternal, The yaml to validate.
    extractor_func: func(AppInfoExternal)->str, A function to extract the
      value of the attribute from a _YamlInfo object.
    file_path: str, The path of file from which yaml_info was parsed.
    current_value: str, The value that gcloud is using for this attribute.  If
      given, the files must all declare the same value or not declare
      anything.

  Raises:
      YamlValidationError: If validation of attribute fails.

  Returns:
    str, The value for the attribute.  This will always be the current_value
      if given.  If not given, then it will be the value of the parsed
      attribute if it exists.
  """
  attribute = extractor_func(yaml_info)
  if attribute is not None:
    # Make sure it matches the current value if provided.
    if current_value is not None and attribute != current_value:
      raise YamlValidationError(
          'The {0} [{1}] declared in [{2}] does not match the current '
          'gcloud {3} [{4}].'.format(name, attribute, file_path, gcloud_name,
                                     current_value))

    if warn_remove:
      # Recommend to not use the given attribute.
      log.warning('The [{0}] field is specified in file [{1}].  This field '
                  'is not used by gcloud and should be removed.'.format(
                      name, file_path))

    # If no current value, use the value we parsed.
    current_value = current_value or attribute

  return current_value


class AppConfigSet(object):
  """Parses and holds information about the set of config files for an app."""
  YAML_EXTS = ['.yaml', '.yml']
  IGNORED_YAMLS = ['backends']

  def __init__(self, files, project, version=None, check_version=True):
    """Creates a new AppConfigSet.

    This will scan all files and directories in items, parse them, and
    validate their contents.

    Args:
      files: str, The files to load into the config set.
      project: str, The current gcloud project.
      version: str, The app engine version that is being operated on.
      check_version: bool, True if version verification has to be enabled
        (deployment).

    Raises:
      AppConfigSetLoadError: If validation fails on the given files.
      YamlParserError: If a file fails to parse.
    """
    self.__project = project
    self.__version = version
    self.__config_yamls = {}
    self.__module_yamls = {}
    self.__check_version = check_version
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

  def Modules(self):
    """Gets the modules that were found.

    Returns:
      {str, ModuleYamlInfo}, A mapping of module name to definition.
    """
    return dict(self.__module_yamls)

  def HermeticModules(self):
    """Gets the hermetic modules that were found.

    Returns:
      {str, ModuleYamlInfo}, A mapping of module name to definition.
    """
    return dict((key, mod) for (key, mod) in self.__module_yamls.iteritems()
                if mod.is_hermetic)

  def NonHermeticModules(self):
    """Gets the non-hermetic modules that were found.

    Returns:
      {str, ModuleYamlInfo}, A mapping of module name to definition.
    """
    return dict((key, mod) for (key, mod) in self.__module_yamls.iteritems()
                if not mod.is_hermetic)

  def Configs(self):
    """Gets the configs that were found.

    Returns:
      {str, ConfigYamlInfo}, A mapping of config name to definition.
    """
    return dict(self.__config_yamls)

  def Version(self):
    """Gets the app version.

    Returns:
      str, The version that we are acting on.  This can either come from the
        parsed files, or the value that was given during initialization.  All
        given values must match.
    """
    yaml_version = None
    if self.__module_yamls:
      yaml_version = self.__module_yamls.values()[0].version
    return yaml_version or self.__version

  def __IsInterestingFile(self, f):
    """Determines if the given file is something we should try to parse.

    Args:
      f: str, The full path to the file.

    Returns:
      True if the file is a module yaml or a config yaml.
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
      True if the file was valid, False if it is not a valid module or config
      file.
    """
    file_path = os.path.abspath(file_path)
    if not self.__IsInterestingFile(file_path):
      return False

    yaml = ConfigYamlInfo.FromFile(file_path, self.__project)
    if yaml:
      existing_config = self.__config_yamls.get(yaml.config)
      if existing_config:
        self.__Error('Found multiple files for config [%s]: [%s, %s]',
                     yaml.config, self.__RelPath(yaml),
                     self.__RelPath(existing_config))
      else:
        self.__config_yamls[yaml.config] = yaml
    else:
      yaml = ModuleYamlInfo.FromFile(file_path,
                                     self.__project,
                                     self.__version,
                                     self.__check_version)
      existing_module = self.__module_yamls.get(yaml.module)
      if existing_module:
        self.__Error('Found multiple files declaring module [%s]: [%s, %s]',
                     yaml.module, self.__RelPath(yaml),
                     self.__RelPath(existing_module))
      else:
        self.__module_yamls[yaml.module] = yaml

    return True

  def __RelPath(self, yaml):
    # We are going to display full file paths for now.
    return yaml.file
