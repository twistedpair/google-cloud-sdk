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
from googlecloudsdk.api_lib.app.appinfo import appinfo
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
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

MANAGED_VMS_DEPRECATION_WARNING = """\
Deployments using `vm: true` have been deprecated.  Please update your \
app.yaml to use `env: flex`. To learn more, please visit \
https://cloud.google.com/appengine/docs/flexible/migration.
"""

UPGRADE_FLEX_PYTHON_URL = (
    'https://cloud.google.com/appengine/docs/flexible/python/migrating')

APP_ENGINE_APIS_DEPRECATION_WARNING = (
    'Support for the compat runtimes and their base images '
    '(enable_app_engine_apis: true) has been deprecated.  Please migrate to a '
    'new base image, or use a Google managed runtime. '
    'To learn more, visit {}.').format(UPGRADE_FLEX_PYTHON_URL)

# This is the equivalent of the following in app.yaml:
# skip_files:
# - ^(.*/)?#.*#$
# - ^(.*/)?.*~$
# - ^(.*/)?.*\.py[co]$
# - ^(.*/)?.*/RCS/.*$
# - ^(.*/)?.git(ignore|/.*)$
# - ^(.*/)?node_modules/.*
DEFAULT_SKIP_FILES_FLEX = (r'^(.*/)?#.*#$|'
                           r'^(.*/)?.*~$|'
                           r'^(.*/)?.*\.py[co]$|'
                           r'^(.*/)?.*/RCS/.*$|'
                           r'^(.*/)?.git(ignore|/.*)$|'
                           r'^(.*/)?node_modules/.*$')


class Error(exceptions.Error):
  """A base error for this module."""
  pass


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

  @property
  def name(self):
    """Name of the config file without extension, e.g. `cron`."""
    (base, _) = os.path.splitext(os.path.basename(self.file))
    return base

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

    if util.IsFlex(parsed.env):
      self.env = util.Environment.FLEX
    elif parsed.vm or parsed.runtime == 'vm':
      self.env = util.Environment.MANAGED_VMS
    else:
      self.env = util.Environment.STANDARD

    # All env: 2 apps are hermetic. All vm: false apps are not hermetic except
    # for those with (explicit) env: 1 and runtime: custom. vm: true apps are
    # hermetic IFF they don't use static files.
    if self.env is util.Environment.FLEX:
      self.is_hermetic = True
    elif util.IsStandard(parsed.env):
      self.is_hermetic = parsed.runtime == 'custom'
    elif parsed.vm:
      for urlmap in parsed.handlers:
        if urlmap.static_dir or urlmap.static_files:
          self.is_hermetic = False
          break
      else:
        self.is_hermetic = True
    else:
      self.is_hermetic = False

    self._UpdateSkipFiles(file_path, parsed)

    if self.env is util.Environment.STANDARD and self.is_hermetic:
      self.runtime = parsed.runtime
    elif (self.env is util.Environment.MANAGED_VMS) or self.is_hermetic:
      self.runtime = parsed.GetEffectiveRuntime()
      self._UpdateVMSettings()
    else:
      self.runtime = parsed.runtime

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
      elif parsed.runtime == 'custom' and not parsed.env:
        raise YamlValidationError(
            'runtime "custom" requires that env be explicitly specified.')

    if parsed.vm:
      log.warn(MANAGED_VMS_DEPRECATION_WARNING)

    if (util.IsFlex(parsed.env) and parsed.beta_settings and
        parsed.beta_settings.get('enable_app_engine_apis')):
      log.warn(APP_ENGINE_APIS_DEPRECATION_WARNING)

    if util.IsFlex(parsed.env) and vm_runtime == 'python27':
      raise YamlValidationError(
          'The "python27" is not a valid runtime in env: flex.  '
          'Please use [python] instead.')

    if util.IsFlex(parsed.env) and vm_runtime == 'python-compat':
      log.warn('[runtime: {}] is deprecated.  Please use [runtime: python] '
               'instead.  See {} for more info.'
               .format(vm_runtime, UPGRADE_FLEX_PYTHON_URL))

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
    return self.env is util.Environment.MANAGED_VMS or self.is_hermetic

  def _UpdateVMSettings(self):
    """Overwrites vm_settings for App Engine services with VMs.

    Also sets module_yaml_path which is needed for some runtimes.

    Raises:
      AppConfigError: if the function was called for a standard service
    """
    if self.env not in [util.Environment.MANAGED_VMS, util.Environment.FLEX]:
      raise AppConfigError(
          'This is not an App Engine Flexible service. Please set `env` '
          'field to `flex`.')
    if not self.parsed.vm_settings:
      self.parsed.vm_settings = appinfo.VmSettings()

    self.parsed.vm_settings['module_yaml_path'] = os.path.basename(self.file)

  def _UpdateSkipFiles(self, file_path, parsed):
    """Resets skip_files field to Flex default if applicable."""
    if self.RequiresImage():
      if parsed.skip_files == appinfo.DEFAULT_SKIP_FILES:
        # Make sure that this was actually a default, not from the file.
        try:
          with open(file_path, 'r') as readfile:
            contents = readfile.read()
        except IOError:  # If the class was initiated with a non-existent file
          contents = ''
        if 'skip_files' not in contents:
          # pylint:disable=protected-access
          parsed.skip_files = validation._RegexStrValue(
              validation.Regex(DEFAULT_SKIP_FILES_FLEX),
              DEFAULT_SKIP_FILES_FLEX,
              'skip_files')
          # pylint:enable=protected-access


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

