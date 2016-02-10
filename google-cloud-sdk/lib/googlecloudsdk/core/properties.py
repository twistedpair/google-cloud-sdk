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

"""Read and write properties for the CloudSDK."""

import ConfigParser
import os
import re
import sys
import threading

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import named_configs
from googlecloudsdk.core.credentials import devshell as c_devshell
from googlecloudsdk.core.credentials import gce as c_gce
from googlecloudsdk.core.credentials import gce_cache
from googlecloudsdk.core.docker import constants as const_lib
from googlecloudsdk.core.util import files
from googlecloudsdk.third_party.py27 import py27_collections as collections

named_configs.FLAG_OVERRIDE_STACK.Push(named_configs.AdhocConfigFlagParse())


_SET_PROJECT_HELP = """\
To set your project, run:

  $ gcloud config set project PROJECT_ID

or to unset it, run:

  $ gcloud config unset project"""


_VALID_PROJECT_REGEX = re.compile(
    r'^'
    # An optional domain-like component, ending with a colon, e.g.,
    # google.com:
    r'(?:(?:[-a-z0-9]{1,63}\.)*(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?):)?'
    # Followed by a required identifier-like component, for example:
    #   waffleHouse    match
    #   -foozle        no match
    #   Foozle         no match
    # We specifically disallow project number, even though some GCP backends
    # could accept them.
    r'(?:(?:[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?))'
    r'$'
)


_VALID_ENDPOINT_OVERRIDE_REGEX = re.compile(
    r'^'
    # require http or https for scheme
    r'(?:https?)://'
    # netlocation portion of address. can be any of
    # - domain name
    # - 'localhost'
    # - ipv4 addr
    # - ipv6 addr
    r'(?:'  # begin netlocation
    # - domain name, e.g. 'test-foo.sandbox.googleapis.com'
    #   1 or more domain labels ending in '.', e.g. 'sandbox.', 'googleapis.'
    r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
    #   ending top-level domain, e.g. 'com'
    r'(?:[A-Z]{2,6}|[A-Z0-9-]{2,})|'
    # - localhost
    r'localhost|'
    # - ipv4
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    # - ipv6
    r'\[?[A-F0-9]*:[A-F0-9:]+\]?'
    r')'  # end netlocation
    # optional port
    r'(?::\d+)?'
    # require trailing slash, fragment optional
    r'(?:/|[/?]\S+/)'
    r'$', re.IGNORECASE)


def _LooksLikeAProjectName(project):
  """Heuristics testing if a string looks like a project name, but an id."""

  if re.match(r'[-0-9A-Z]', project[0]):
    return True

  return any(c in project for c in ' !"\'')


class Error(exceptions.Error):
  """Exceptions for the properties module."""


class PropertiesParseError(Error):
  """An exception to be raised when a properties file is invalid."""


class NoSuchPropertyError(Error):
  """An exception to be raised when the desired property does not exist."""


class MissingConfigLocationError(Error):
  """An exception to be raised when a config location does not exist."""

  def __init__(self, scope):
    super(MissingConfigLocationError, self).__init__(
        'The configuration location for [{scope}] properties does not exist.'
        .format(scope=scope.id))


class ReadOnlyNamedConfigNotSettableError(Error):
  """An exception for when the active config is read-only (e.g. None)."""

  def __init__(self, config_name):
    super(ReadOnlyNamedConfigNotSettableError, self).__init__(
        'Properties in configuration [{0}] are read only.'.format(config_name))


class InvalidScopeValueError(Error):
  """Exception for when a string could not be parsed to a valid scope value."""

  def __init__(self, given):
    """Constructs a new exception.

    Args:
      given: str, The given string that could not be parsed.
    """
    super(InvalidScopeValueError, self).__init__(
        'Could not parse [{0}] into a valid configuration scope.  '
        'Valid values are [{1}]'.format(given,
                                        ', '.join(Scope.AllScopeNames())))


class InvalidValueError(Error):
  """An exception to be raised when the set value of a property is invalid."""


class InvalidProjectError(InvalidValueError):
  """An exception for bad project names, with a little user help."""

  def __init__(self, given):
    super(InvalidProjectError, self).__init__(
        given + '\n' + _SET_PROJECT_HELP)


class RequiredPropertyError(Error):
  """Generic exception for when a required property was not set."""
  FLAG_STRING = ('It can be set on a per-command basis by re-running your '
                 'command with the [{flag}] flag.\n\n')

  def __init__(self, prop, flag=None, extra_msg=None):
    section = (prop.section + '/' if prop.section != VALUES.default_section.name
               else '')
    if flag:
      flag_msg = RequiredPropertyError.FLAG_STRING.format(flag=flag)
    else:
      flag_msg = ''

    msg = ("""\
The required property [{property_name}] is not currently set.
{flag_msg}You may set it for your current workspace by running:

  $ gcloud config set {section}{property_name} VALUE

or it can be set temporarily by the environment variable [{env_var}]"""
           .format(property_name=prop.name,
                   flag_msg=flag_msg,
                   section=section,
                   env_var=prop.EnvironmentName()))
    if extra_msg:
      msg += '\n\n' + extra_msg
    super(RequiredPropertyError, self).__init__(msg)
    self.property = prop


class _Sections(object):
  """Represents the available sections in the properties file.

  Attributes:
    auth: Section, The section containing auth properties for the Cloud SDK.
    default_section: Section, The main section of the properties file (core).
    core: Section, The section containing core properties for the Cloud SDK.
    component_manager: Section, The section containing properties for the
      component_manager.
  """

  class _ValueFlag(object):

    def __init__(self, value, flag):
      self.value = value
      self.flag = flag

  def __init__(self):
    self.api_endpoint_overrides = _SectionApiEndpointOverrides()
    self.api_client_overrides = _SectionApiClientOverrides()
    self.app = _SectionApp()
    self.auth = _SectionAuth()
    self.core = _SectionCore()
    self.component_manager = _SectionComponentManager()
    self.compute = _SectionCompute()
    self.container = _SectionContainer()
    self.datastore_emulator = _SectionDatastoreEmulator()
    self.devshell = _SectionDevshell()
    self.experimental = _SectionExperimental()
    self.metrics = _SectionMetrics()
    self.proxy = _SectionProxy()
    self.test = _SectionTest()

    self.__sections = dict(
        (section.name, section) for section in
        [self.api_endpoint_overrides, self.api_client_overrides, self.app,
         self.auth, self.core, self.component_manager, self.compute,
         self.container, self.datastore_emulator, self.devshell,
         self.experimental, self.metrics, self.proxy, self.test])
    self.__invocation_value_stack = [{}]

  @property
  def default_section(self):
    return self.core

  def __iter__(self):
    return iter(self.__sections.values())

  def PushInvocationValues(self):
    self.__invocation_value_stack.append({})

  def PopInvocationValues(self):
    self.__invocation_value_stack.pop()

  def SetInvocationValue(self, prop, value, flag):
    """Set the value of this property for this command, using a flag.

    Args:
      prop: _Property, The property with an explicit value.
      value: str, The value that should be returned while this command is
          running.
      flag: str, The flag that a user can use to set the property, reported
          if it was required at some point but not set by the command line.
    """
    value_flags = self.GetLatestInvocationValues()
    if value:
      prop.Validate(value)
    value_flags[prop] = _Sections._ValueFlag(value, flag)

  def GetLatestInvocationValues(self):
    return self.__invocation_value_stack[-1]

  def GetInvocationStack(self):
    return self.__invocation_value_stack

  def Section(self, section):
    """Gets a section given its name.

    Args:
      section: str, The section for the desired property.

    Returns:
      Section, The section corresponding to the given name.

    Raises:
      NoSuchPropertyError: If the section is not known.
    """
    try:
      return self.__sections[section]
    except KeyError:
      raise NoSuchPropertyError('Section "{section}" does not exist.'.format(
          section=section))

  def AllSections(self, include_hidden=False):
    """Gets a list of all registered section names.

    Args:
      include_hidden: bool, True to include hidden properties in the result.

    Returns:
      [str], The section names.
    """
    return [name for name, value in self.__sections.iteritems()
            if not value.is_hidden or include_hidden]

  def AllValues(self, list_unset=False, include_hidden=False,
                properties_file=None, only_file_contents=False):
    """Gets the entire collection of property values for all sections.

    Args:
      list_unset: bool, If True, include unset properties in the result.
      include_hidden: bool, True to include hidden properties in the result.
        If a property has a value set but is hidden, it will be included
        regardless of this setting.
      properties_file: PropertyFile, the file to read settings from.  If None
        the active property file will be used.
      only_file_contents: bool, True if values should be taken only from
        the properties file, false if flags, env vars, etc. should
        be consulted too.  Mostly useful for listing file contents.

    Returns:
      {str:{str:str}}, A dict of sections to dicts of properties to values.
    """
    result = {}
    for section in self:
      section_result = section.AllValues(list_unset=list_unset,
                                         include_hidden=include_hidden,
                                         properties_file=properties_file,
                                         only_file_contents=only_file_contents)
      if section_result:
        result[section.name] = section_result
    return result

  def GetHelpString(self):
    """Gets a string with the help contents for all properties and descriptions.

    Returns:
      str, The string for the man page section.
    """
    messages = []
    sections = [self.default_section]
    default_section_name = self.default_section.name
    sections.extend(
        sorted([s for name, s in self.__sections.iteritems()
                if name != default_section_name and not s.is_hidden]))
    for section in sections:
      props = sorted([p for p in section if not p.is_hidden])
      if not props:
        continue
      messages.append('_{section}_::'.format(section=section.name))
      for prop in props:
        messages.append(
            '*{prop}*:::\n\n{text}'.format(prop=prop.name, text=prop.help_text))
    return '\n\n\n'.join(messages)


class _Section(object):
  """Represents a section of the properties file that has related properties.

  Attributes:
    name: str, The name of the section.
    is_hidden: bool, True if the section is hidden, False otherwise.
  """

  def __init__(self, name, hidden=False):
    self.__name = name
    self.__is_hidden = hidden
    self.__properties = {}

  @property
  def name(self):
    return self.__name

  @property
  def is_hidden(self):
    return self.__is_hidden

  def __iter__(self):
    return iter(self.__properties.values())

  def __eq__(self, other):
    return self.name == other.name

  def __ne__(self, other):
    return self.name != other.name

  def __gt__(self, other):
    return self.name > other.name

  def __ge__(self, other):
    return self.name >= other.name

  def __lt__(self, other):
    return self.name < other.name

  def __le__(self, other):
    return self.name <= other.name

  def _Add(self, name, help_text=None, hidden=False, callbacks=None,
           validator=None, choices=None, resource=None,
           resource_command_path=None):
    prop = _Property(
        section=self.__name, name=name, help_text=help_text,
        hidden=(self.is_hidden or hidden),
        callbacks=callbacks, validator=validator, choices=choices,
        resource=resource, resource_command_path=resource_command_path)
    self.__properties[name] = prop
    return prop

  def _AddBool(self, name, help_text=None, hidden=False, callbacks=None):
    return self._Add(name=name, help_text=help_text, hidden=hidden,
                     callbacks=callbacks, choices=('true', 'false'))

  def Property(self, property_name):
    """Gets a property from this section, given its name.

    Args:
      property_name: str, The name of the desired property.

    Returns:
      Property, The property corresponding to the given name.

    Raises:
      NoSuchPropertyError: If the property is not known for this section.
    """
    try:
      return self.__properties[property_name]
    except KeyError:
      raise NoSuchPropertyError(
          'Section "{s}" has no property "{p}".'.format(
              s=self.__name,
              p=property_name))

  def AllProperties(self, include_hidden=False):
    """Gets a list of all registered property names in this section.

    Args:
      include_hidden: bool, True to include hidden properties in the result.

    Returns:
      [str], The property names.
    """
    return [name for name, prop in self.__properties.iteritems()
            if include_hidden or not prop.is_hidden]

  def AllValues(self, list_unset=False, include_hidden=False,
                properties_file=None, only_file_contents=False):
    """Gets all the properties and their values for this section.

    Args:
      list_unset: bool, If True, include unset properties in the result.
      include_hidden: bool, True to include hidden properties in the result.
        If a property has a value set but is hidden, it will be included
        regardless of this setting.
      properties_file: PropertiesFile, the file to read settings from.  If None
        the active property file will be used.
      only_file_contents: bool, True if values should be taken only from
        the properties file, false if flags, env vars, etc. should
        be consulted too.  Mostly useful for listing file contents.

    Returns:
      {str:str}, The dict of {property:value} for this section.
    """
    properties_file = properties_file or PropertiesFile.Load()

    result = {}
    for prop in self:
      if (prop.is_hidden
          and not include_hidden
          and _GetPropertyWithoutCallback(prop, properties_file) is None):
        continue

      if only_file_contents:
        value = properties_file.Get(prop)
      else:
        value = _GetProperty(prop, properties_file, required=False)

      if value is None:
        if not list_unset:
          # Never include if not set and not including unset values.
          continue
        if prop.is_hidden and not include_hidden:
          # If including unset values, exclude if hidden and not including
          # hidden properties.
          continue

      # Always include if value is set (even if hidden)
      result[prop.name] = value
    return result


class _SectionCompute(_Section):
  """Contains the properties for the 'compute' section."""

  def __init__(self):
    super(_SectionCompute, self).__init__('compute')
    self.zone = self._Add(
        'zone',
        help_text='The default zone to use when working with zonal Compute '
        'Engine resources. When a `--zone` flag is required but not provided, '
        'the command will fall back to this value, if set.',
        resource='compute.zones')
    self.region = self._Add(
        'region',
        help_text='The default region to use when working with regional Compute'
        ' Engine resources. When a `--region` flag is required but not '
        'provided, the command will fall back to this value, if set.',
        resource='compute.regions')


class _SectionApp(_Section):
  """Contains the properties for the 'app' section."""

  def __init__(self):
    super(_SectionApp, self).__init__('app')
    self.promote_by_default = self._AddBool(
        'promote_by_default',
        callbacks=[lambda: True],
        hidden=True)
    self.stop_previous_version = self._AddBool(
        'stop_previous_version',
        help_text='If True, when deploying a new version of a service, the '
        'previously deployed version is stopped. If False, older versions must '
        'be stopped manually.')
    self.use_cloud_build = self._AddBool(
        'use_cloud_build',
        help_text='If True, use the Container Builder API to perform docker '
        'builds, rather than a temporary VM. See '
        'https://cloud.google.com/container-builder/docs/ for more '
        'information.')
    self.hosted_build_image = self._Add(
        'hosted_build_image',
        callbacks=[lambda: 'gae-builder-vm'],
        hidden=True)
    self.hosted_build_zone = self._Add(
        'hosted_build_zone',
        callbacks=[lambda: 'us-central1-f'],
        hidden=True)
    self.hosted_build_machine_type = self._Add(
        'hosted_build_machine_type',
        callbacks=[lambda: 'n1-standard-1'],
        hidden=True)
    self.hosted_build_boot_disk_size = self._Add(
        'hosted_build_boot_disk_size',
        callbacks=[lambda: '200GB'],
        hidden=True)
    self.use_appengine_api = self._AddBool(
        'use_appengine_api',
        callbacks=[lambda: True],
        hidden=True)
    self.suppress_change_warning = self._AddBool(
        'suppress_change_warning',
        hidden=True)

    def DockerBuildValidator(docker_build):
      if docker_build is None:
        return
      if docker_build not in ['local', 'remote']:
        raise InvalidValueError("docker_build should be either 'local' or "
                                "'remote'.")
    self.docker_build = self._Add(
        'docker_build',
        help_text='Set to `local` to run `docker build` using a local docker '
        'installation, or `remote` to do the build on a Google Compute Engine '
        'VM.',
        validator=DockerBuildValidator,
        choices=('local', 'remote'))


class _SectionContainer(_Section):
  """Contains the properties for the 'container' section."""

  def __init__(self):
    super(_SectionContainer, self).__init__('container')
    self.cluster = self._Add(
        'cluster',
        help_text='The name of the cluster to use by default when working with '
        'Container Engine.')


def _GetGCEAccount():
  if VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().DefaultAccount()


def _GetGCEProject():
  if VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().Project()


class _SectionCore(_Section):
  """Contains the properties for the 'core' section."""

  def __init__(self):
    super(_SectionCore, self).__init__('core')
    self.account = self._Add(
        'account',
        help_text='The account gcloud should use for authentication.  You can '
        'run `gcloud auth list` to see the accounts you currently have '
        'available.',
        callbacks=[c_devshell.DefaultAccount, _GetGCEAccount])
    self.disable_color = self._AddBool(
        'disable_color',
        help_text='If True, color will not be used when printing messages in '
        'the terminal.')
    self.disable_command_lazy_loading = self._AddBool(
        'disable_command_lazy_loading', hidden=True)
    self.disable_prompts = self._AddBool(
        'disable_prompts',
        help_text='If True, the default answer will be assumed for all user '
        'prompts.  For any prompts that require user input, an error will be '
        'raised. This is the equivalent of using the global `--quiet` flag.')
    self.disable_usage_reporting = self._AddBool(
        'disable_usage_reporting',
        help_text='If True, anonymous statistics on SDK usage will not be '
        'collected.  This is value is set based on your choices during '
        'installation, but can be changed at any time.  For more information, '
        'see: https://cloud.google.com/sdk/usage-statistics')
    self.api_host = self._Add(
        'api_host', hidden=True,
        callbacks=[lambda: 'https://www.googleapis.com'])
    self.verbosity = self._Add(
        'verbosity',
        help_text='The default logging verbosity for gcloud commands.  This is '
        'the equivalent of using the global `--verbosity` flag.')
    self.user_output_enabled = self._AddBool(
        'user_output_enabled',
        help_text='If False, messages to the user and command output on both '
        'standard output and standard error will be suppressed.')
    self.log_http = self._AddBool(
        'log_http',
        help_text='If True, log http requests and responses to the logs.  '
        'You may need to adjust your `verbosity` setting if you want to see '
        'in the terminal, otherwise it is available in the log files.')
    self.check_gce_metadata = self._AddBool(
        'check_gce_metadata', hidden=True,
        callbacks=[lambda: True])
    self.print_unhandled_tracebacks = self._AddBool(
        'print_unhandled_tracebacks', hidden=True)

    def ProjectValidator(project):
      """Checks to see if the project string is valid."""
      if project is None:
        return
      if _VALID_PROJECT_REGEX.match(project):
        return

      if not isinstance(project, basestring):
        raise InvalidValueError('project must be a string')
      if project == '':  # pylint: disable=g-explicit-bool-comparison
        raise InvalidProjectError('The project property is set to the '
                                  'empty string, which is invalid.')
      if project.isdigit():
        raise InvalidProjectError(
            'The project property must be set to a valid project ID, not the '
            'project number [{value}]'.format(value=project))
      if _LooksLikeAProjectName(project):
        raise InvalidProjectError(
            'The project property must be set to a valid project ID, not the '
            'project name [{value}]'.format(value=project))
      # Non heuristics for a better error message.
      raise InvalidProjectError(
          'The project property must be set to a valid project ID, '
          '[{value}] is not a valid project ID.'.format(value=project))

    # pylint: disable=unnecessary-lambda, We don't want to call Metadata()
    # unless we really have to.
    self.project = self._Add(
        'project',
        help_text='The project id of the Cloud Platform project to operate on '
        'by default.  This can be overridden by using the global `--project` '
        'flag.',
        validator=ProjectValidator,
        callbacks=[lambda: c_devshell.Project(), _GetGCEProject],
        resource='cloudresourcemanager.projects',
        resource_command_path='beta.projects')
    self.credentialed_hosted_repo_domains = self._Add(
        'credentialed_hosted_repo_domains',
        hidden=True)


class _SectionAuth(_Section):
  """Contains the properties for the 'auth' section."""

  def __init__(self):
    super(_SectionAuth, self).__init__('auth')
    # pylint: disable=unnecessary-lambda, We don't want to call Metadata()
    # unless we really have to.
    self.auth_host = self._Add(
        'auth_host', hidden=True,
        callbacks=[lambda: 'https://accounts.google.com/o/oauth2/auth'])
    self.token_host = self._Add(
        'token_host', hidden=True,
        callbacks=[lambda: 'https://accounts.google.com/o/oauth2/token'])
    self.disable_ssl_validation = self._AddBool(
        'disable_ssl_validation', hidden=True)
    self.client_id = self._Add(
        'client_id', hidden=True,
        callbacks=[lambda: config.CLOUDSDK_CLIENT_ID])
    self.client_secret = self._Add(
        'client_secret', hidden=True,
        callbacks=[lambda: config.CLOUDSDK_CLIENT_NOTSOSECRET])
    self.authority_selector = self._Add(
        'authority_selector', hidden=True)
    self.authorization_token_file = self._Add(
        'authorization_token_file', hidden=True)


class _SectionMetrics(_Section):
  """Contains the properties for the 'metrics' section."""

  def __init__(self):
    super(_SectionMetrics, self).__init__('metrics', hidden=True)
    self.environment = self._Add('environment', hidden=True)


class _SectionComponentManager(_Section):
  """Contains the properties for the 'component_manager' section."""

  def __init__(self):
    super(_SectionComponentManager, self).__init__('component_manager')
    self.additional_repositories = self._Add(
        'additional_repositories',
        help_text='A comma separated list of additional repositories to check '
        'for components.  This property is automatically managed by the '
        '`gcloud components repositories` commands.')
    self.disable_update_check = self._AddBool(
        'disable_update_check',
        help_text='If True, the Cloud SDK will not automatically check for '
        'updates.')
    self.fixed_sdk_version = self._Add('fixed_sdk_version', hidden=True)
    self.snapshot_url = self._Add('snapshot_url', hidden=True)


class _SectionExperimental(_Section):
  """Contains the properties for gcloud experiments."""

  def __init__(self):
    super(_SectionExperimental, self).__init__('experimental', hidden=True)
    self.fast_component_update = self._AddBool(
        'fast_component_update',
        callbacks=[config.INSTALLATION_CONFIG.IsAlternateReleaseChannel])


class _SectionTest(_Section):
  """Contains the properties for the 'test' section."""

  def __init__(self):
    super(_SectionTest, self).__init__('test')
    self.results_base_url = self._Add('results_base_url', hidden=True)
    # TODO(user): remove this when API provides an alternative to polling.
    self.matrix_status_interval = self._Add('matrix_status_interval',
                                            hidden=True)


class _SectionProxy(_Section):
  """Contains the properties for the 'proxy' section."""

  def __init__(self):
    super(_SectionProxy, self).__init__('proxy')
    self.address = self._Add(
        'address',
        help_text='The hostname or IP address of your proxy server.')
    self.port = self._Add(
        'port',
        help_text='The port to use when connected to your proxy server.')
    self.username = self._Add(
        'username',
        help_text='If your proxy requires authentication, the username to use '
        'when connecting.')
    self.password = self._Add(
        'password',
        help_text='If your proxy requires authentication, the password to use '
        'when connecting.')

    valid_proxy_types = sorted(config.GetProxyTypeMap().keys())
    def ProxyTypeValidator(proxy_type):
      if proxy_type is not None and proxy_type not in valid_proxy_types:
        raise InvalidValueError(
            'The proxy type property value [{0}] is not valid. '
            'Possible values: [{1}].'.format(
                proxy_type, ', '.join(valid_proxy_types)))
    self.proxy_type = self._Add(
        'type',
        help_text='The type of proxy you are using.  Supported proxy types are:'
        ' [{0}].'.format(', '.join(valid_proxy_types)),
        validator=ProxyTypeValidator,
        choices=valid_proxy_types)


class _SectionDevshell(_Section):
  """Contains the properties for the 'devshell' section."""

  def __init__(self):
    super(_SectionDevshell, self).__init__('devshell')
    self.image = self._Add(
        'image', hidden=True,
        callbacks=[lambda: const_lib.DEFAULT_DEVSHELL_IMAGE])
    self.metadata_image = self._Add(
        'metadata_image', hidden=True,
        callbacks=[lambda: const_lib.METADATA_IMAGE])


class _SectionApiEndpointOverrides(_Section):
  """Contains the properties for the 'api-endpoint-overrides' section.

  This overrides what endpoint to use when talking to the given API.
  """

  def __init__(self):
    super(_SectionApiEndpointOverrides, self).__init__(
        'api_endpoint_overrides', hidden=True)
    self.appengine = self._Add('appengine')
    self.bigquery = self._Add('bigquery')
    self.bigtableclusteradmin = self._Add('bigtableclusteradmin')
    self.cloudresourcemanager = self._Add('cloudresourcemanager')
    self.compute = self._Add('compute')
    self.cloudbuild = self._Add('cloudbuild')
    self.clouduseraccounts = self._Add('clouduseraccounts')
    self.container = self._Add('container')
    self.dataflow = self._Add('dataflow')
    self.dataproc = self._Add('dataproc')
    self.datastore = self._Add('datastore')
    self.debug = self._Add('debug')
    self.dns = self._Add('dns')
    self.functions = self._Add('functions')
    self.genomics = self._Add('genomics')
    self.iam = self._Add('iam')
    self.loasproject = self._Add('loasproject')
    self.logging = self._Add('logging')
    self.testing = self._Add('testing')
    self.toolresults = self._Add('toolresults')
    self.source = self._Add('source')
    self.sql = self._Add('sql')
    self.pubsub = self._Add('pubsub')

  def EndpointValidator(self, value):
    """Checks to see if the endpoint override string is valid."""
    if value is None:
      return
    if not _VALID_ENDPOINT_OVERRIDE_REGEX.match(value):
      raise InvalidValueError(
          'The endpoint_overrides property must be an absolute URI beginning '
          'with http:// or https:// and ending with a trailing \'/\'. '
          '[{value}] is not a valid endpoint override.'
          .format(value=value))

  def _Add(self, name):
    return super(_SectionApiEndpointOverrides, self)._Add(
        name, validator=self.EndpointValidator)


class _SectionApiClientOverrides(_Section):
  """Contains the properties for the 'api-client-overrides' section.

  This overrides the API client version to use when talking to this API.
  """

  def __init__(self):
    super(_SectionApiClientOverrides, self).__init__(
        'api_client_overrides', hidden=True)
    self.appengine = self._Add('appengine')
    self.compute = self._Add('compute')
    self.container = self._Add('container')
    self.sql = self._Add('sql')


class _SectionDatastoreEmulator(_Section):
  """Contains the properties for the 'datastore-emulator' section.

  This is used to configure emulator properties like data_dir and host_port.
  """

  def __init__(self):
    super(_SectionDatastoreEmulator, self).__init__(
        'datastore_emulator', hidden=True)
    self.data_dir = self._Add('data_dir')
    self.host_port = self._Add('host_port')


class _Property(object):
  """An individual property that can be gotten from the properties file.

  Attributes:
    section: str, The name of the section the property appears in in the file.
    name: str, The name of the property.
    hidden: bool, True to hide this property from display.
    callbacks: [func], A list of functions to be called, in order, if no value
        is found elsewhere.
    validator: func(str), A function that is called on the value when .Set()'d
        or .Get()'d. For valid values, the function should do nothing. For
        invalid values, it should raise InvalidValueError with an
        explanation of why it was invalid.
  """

  def __init__(self, section, name, help_text=None, hidden=False,
               callbacks=None, validator=None, choices=None, resource=None,
               resource_command_path=None):
    self.__section = section
    self.__name = name
    self.__help_text = help_text
    self.__hidden = hidden
    self.__callbacks = callbacks or []
    self.__validator = validator
    self.__choices = choices
    self.__resource = resource
    self.__resource_command_path = resource_command_path

  @property
  def section(self):
    return self.__section

  @property
  def name(self):
    return self.__name

  @property
  def help_text(self):
    return self.__help_text

  @property
  def is_hidden(self):
    return self.__hidden

  @property
  def callbacks(self):
    return self.__callbacks

  @property
  def choices(self):
    return self.__choices

  @property
  def resource(self):
    return self.__resource

  @property
  def resource_command_path(self):
    return self.__resource_command_path

  def __eq__(self, other):
    return self.section == other.section and self.name == other.name

  def __ne__(self, other):
    return not self == other

  def __gt__(self, other):
    return self.name > other.name

  def __ge__(self, other):
    return self.name >= other.name

  def __lt__(self, other):
    return self.name < other.name

  def __le__(self, other):
    return self.name <= other.name

  def Get(self, required=False, validate=True):
    """Gets the value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Args:
      required: bool, True to raise an exception if the property is not set.
      validate: bool, Whether or not to run the fetched value through the
          validation function.

    Returns:
      str, The value for this property.
    """
    value = _GetProperty(self, PropertiesFile.Load(), required)
    if validate:
      self.Validate(value)
    return value

  def Validate(self, value):
    """Test to see if the value is valid for this property.

    Args:
      value: str, The value of the property to be validated.

    Raises:
      InvalidValueError: If the value was invalid according to the property's
          validator.
    """
    if self.__validator:
      self.__validator(value)

  def GetBool(self, required=False, validate=True):
    """Gets the boolean value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Args:
      required: bool, True to raise an exception if the property is not set.
      validate: bool, Whether or not to run the fetched value through the
          validation function.

    Returns:
      bool, The boolean value for this property, or None if it is not set.
    """
    value = _GetBoolProperty(self, PropertiesFile.Load(), required)
    if validate:
      self.Validate(value)
    return value

  def GetInt(self, required=False, validate=True):
    """Gets the integer value for this property.

    Looks first in the environment, then in the workspace config, then in the
    global config, and finally at callbacks.

    Args:
      required: bool, True to raise an exception if the property is not set.
      validate: bool, Whether or not to run the fetched value through the
          validation function.

    Returns:
      int, The integer value for this property.
    """
    value = _GetIntProperty(self, PropertiesFile.Load(), required)
    if validate:
      self.Validate(value)
    return value

  def Set(self, value):
    """Sets the value for this property as an environment variable.

    Args:
      value: str/bool, The proposed value for this property.  If None, it is
        removed from the environment.
    """
    self.Validate(value)
    if value is not None:
      os.environ[self.EnvironmentName()] = str(value)
    elif self.EnvironmentName() in os.environ:
      del os.environ[self.EnvironmentName()]

  def EnvironmentName(self):
    """Get the name of the environment variable for this property.

    Returns:
      str, The name of the correct environment variable.
    """
    return 'CLOUDSDK_{section}_{name}'.format(
        section=self.__section.upper(),
        name=self.__name.upper(),
    )


VALUES = _Sections()


def FromString(property_string):
  """Gets the property object corresponding the given string.

  Args:
    property_string: str, The string to parse.  It can be in the format
      section/property, or just property if the section is the default one.

  Returns:
    properties.Property, The property or None if it failed to parse to a valid
      property.
  """
  section, prop = ParsePropertyString(property_string)
  if not prop:
    return None
  return VALUES.Section(section).Property(prop)


def ParsePropertyString(property_string):
  """Parses a string into a section and property name.

  Args:
    property_string: str, The property string in the format section/property.

  Returns:
    (str, str), The section and property.  Both will be none if the input
    string is empty.  Property can be None if the string ends with a slash.
  """
  if not property_string:
    return None, None

  if '/' in property_string:
    section, prop = tuple(property_string.split('/', 1))
  else:
    section = None
    prop = property_string

  section = section or VALUES.default_section.name
  prop = prop or None
  return section, prop


class Scope(object):
  """An enum class for the different types of property files that can be used.
  """
  _SCOPE_TUPLE = collections.namedtuple('_ScopeTuple',
                                        ['id', 'description', 'get_file'])
  INSTALLATION = _SCOPE_TUPLE(
      id='installation',
      description='The installation based configuration file applies to all '
      'users on the system that use this version of the Cloud SDK.  If the SDK '
      'was installed by an administrator, you will need administrator rights '
      'to make changes to this file.',
      get_file=lambda: config.Paths().installation_properties_path)
  USER = _SCOPE_TUPLE(
      id='user',
      description='The user based configuration file applies only to the '
      'current user of the system.  It will override any values from the '
      'installation configuration.',
      get_file=named_configs.GetEffectiveNamedConfigFile)
  WORKSPACE = _SCOPE_TUPLE(
      id='workspace',
      description='The workspace based configuration file is based on your '
      'current working directory.  You can set project specific configuration '
      'here that will only take effect when working within that project\'s '
      'directory.  You cannot set this value if you are not currently within a '
      'gcloud workspace.  This will override all values from any other '
      'configuration files.\n'
      'Workspace configurations are deprecated and will be removed from a'
      'future version of gcloud.',
      get_file=lambda: config.Paths().workspace_properties_path)

  _ALL = [WORKSPACE, USER, INSTALLATION]
  _ALL_SCOPE_NAMES = [s.id for s in _ALL]

  @staticmethod
  def AllValues():
    """Gets all possible enum values.

    Returns:
      [Scope], All the enum values.
    """
    return list(Scope._ALL)

  @staticmethod
  def AllScopeNames():
    return list(Scope._ALL_SCOPE_NAMES)

  @staticmethod
  def FromId(scope_id):
    """Gets the enum corresponding to the given scope id.

    Args:
      scope_id: str, The scope id to parse.

    Raises:
      InvalidScopeValueError: If the given value cannot be parsed.

    Returns:
      OperatingSystemTuple, One of the OperatingSystem constants or None if the
      input is None.
    """
    if not scope_id:
      return None
    for scope in Scope._ALL:
      if scope.id == scope_id:
        return scope
    raise InvalidScopeValueError(scope_id)

  @staticmethod
  def GetHelpString():
    return '\n\n'.join(['*{0}*::: {1}'.format(s.id, s.description)
                        for s in Scope.AllValues()])


def PersistProperty(prop, value, scope=None, properties_file=None):
  """Sets the given property in the properties file.

  This function should not generally be used as part of normal program
  execution.  The property files are user editable config files that they should
  control.  This is mostly for initial setup of properties that get set during
  SDK installation.

  Args:
    prop: properties.Property, The property to set.
    value: str, The value to set for the property. If None, the property is
      removed.
    scope: Scope, The config location to set the property in.  If given, only
      this location will be udpated and it is an error if that location does
      not exist.  If not given, it will attempt to update the property in the
      first of the following places that exists:
        - the workspace config
        - the active named config
        - user level config
      It will never fall back to installation properties; you must
      use that scope explicitly to set that value.
    properties_file: str, Path to an explicit properties file to use (instead of
      one of the known locations).  It is an error to specify a scope and an
      explicit file.

  Raises:
    ValueError: If you give both a scope and a properties file.
    MissingConfigLocationError: If there is not file for the given scope.
    ReadOnlyNamedConfigNotSettableError: If the user is attempting to set
      a property in a read-only configuration.
    InternalError: If there's a programming error.
  """
  prop.Validate(value)
  if scope and properties_file:
    raise ValueError('You cannot provide both a scope and a specific properties'
                     ' file.')
  if not properties_file:
    if scope:
      if scope == Scope.INSTALLATION:
        config.EnsureSDKWriteAccess()
      properties_file = scope.get_file()
      if not properties_file:
        raise MissingConfigLocationError(scope)
    else:
      properties_file = Scope.WORKSPACE.get_file()
      if not properties_file:
        properties_file = named_configs.GetEffectiveNamedConfigFile()
        if properties_file is None:
          # Should be dead code.
          raise exceptions.InternalError('Unexpected None properties file.')
        if properties_file == os.path.devnull:
          # Refuse to write and fail with an informative error
          # TODO(b/22817095) Simplify control flow and update
          # messaging when moving to automatic upgrade scenario
          # on all release tracks.
          if (named_configs.GetNameOfActiveNamedConfig() ==
              named_configs.RESERVED_NAMED_CONFIG_NAME_NONE):
            raise ReadOnlyNamedConfigNotSettableError(
                named_configs.RESERVED_NAMED_CONFIG_NAME_NONE)
          if not Scope.USER.get_file():
            raise MissingConfigLocationError(Scope.USER)

  parsed_config = ConfigParser.ConfigParser()
  parsed_config.read(properties_file)

  if not parsed_config.has_section(prop.section):
    if value is None:
      return
    parsed_config.add_section(prop.section)

  if value is None:
    parsed_config.remove_option(prop.section, prop.name)
  else:
    parsed_config.set(prop.section, prop.name, str(value))

  properties_dir, unused_name = os.path.split(properties_file)
  files.MakeDir(properties_dir)
  with open(properties_file, 'w') as fp:
    parsed_config.write(fp)

  PropertiesFile.Invalidate()


def _GetProperty(prop, properties_file, required):
  """Gets the given property.

  If the property has a designated command line argument and args is provided,
  check args for the value first. If the corresponding environment variable is
  set, use that second. If still nothing, use the callbacks.

  Args:
    prop: properties.Property, The property to get.
    properties_file: PropertiesFile, An already loaded properties files to use.
    required: bool, True to raise an exception if the property is not set.

  Raises:
    RequiredPropertyError: If the property was required but unset.

  Returns:
    str, The value of the property, or None if it is not set.
  """

  flag_to_use = None

  invocation_stack = VALUES.GetInvocationStack()
  if len(invocation_stack) > 1:
    # First item is the blank stack entry, second is from the user command args.
    first_invocation = invocation_stack[1]
    if prop in first_invocation:
      flag_to_use = first_invocation.get(prop).flag

  value = _GetPropertyWithoutCallback(prop, properties_file)
  if value is not None:
    return str(value)

  # Still nothing, fall back to the callbacks.
  for callback in prop.callbacks:
    value = callback()
    if value is not None:
      return str(value)

  # Not set, throw if required.
  if required:
    raise RequiredPropertyError(
        prop, flag=flag_to_use)

  return None


def _GetPropertyWithoutCallback(prop, properties_file):
  """Gets the given property without using a callback.

  If the property has a designated command line argument and args is provided,
  check args for the value first. If the corresponding environment variable is
  set, use that second. If still nothing, use the callbacks.

  Args:
    prop: properties.Property, The property to get.
    properties_file: PropertiesFile, An already loaded properties files to use.

  Returns:
    str, The value of the property, or None if it is not set.
  """

  invocation_stack = VALUES.GetInvocationStack()
  for value_flags in reversed(invocation_stack):
    if prop not in value_flags:
      continue
    value_flag = value_flags.get(prop, None)
    if not value_flag:
      continue
    if value_flag.value is not None:
      return str(value_flag.value)

  value = os.environ.get(prop.EnvironmentName(), None)
  if value is not None:
    return str(value)

  value = properties_file.Get(prop)
  if value is not None:
    return str(value)

  return None


def _GetBoolProperty(prop, properties_file, required):
  """Gets the given property in bool form.

  Args:
    prop: properties.Property, The property to get.
    properties_file: PropertiesFile, An already loaded properties files to use.
    required: bool, True to raise an exception if the property is not set.

  Returns:
    bool, The value of the property, or None if it is not set.
  """
  value = _GetProperty(prop, properties_file, required)
  if value is None:
    return None
  return value.lower() in ['1', 'true', 'on', 'yes']


def _GetIntProperty(prop, properties_file, required):
  """Gets the given property in integer form.

  Args:
    prop: properties.Property, The property to get.
    properties_file: PropertiesFile, An already loaded properties files to use.
    required: bool, True to raise an exception if the property is not set.

  Returns:
    int, The integer value of the property, or None if it is not set.
  """
  value = _GetProperty(prop, properties_file, required)
  if value is None:
    return None
  try:
    return int(value)
  except ValueError:
    raise InvalidValueError(
        'The property [{section}.{name}] must have an integer value: [{value}]'
        .format(section=prop.section, name=prop.name, value=value))


class PropertiesFile(object):
  """Properties holder for CloudSDK CLIs."""

  _PROPERTIES = None
  _LOCK = threading.RLock()
  _ALREADY_GAVE_DEPRECATION_WARNINGS = False

  @staticmethod
  def Load():
    """Loads the set of properties for the CloudSDK CLIs from files.

    This function will load the properties file, first from the installation
    config, then from either the global config directory
    CLOUDSDK_GLOBAL_CONFIG_DIR (to be deprecated) or an named config set
    at CLOUDSDK_NAMED_CONFIG_ACTIVATOR_PATH,
    and then from the workspace config directory
    CLOUDSDK_WORKSPACE_CONFIG_DIR (to be deprecated).

    If the properties have already been loaded, the cached values are returned.

    Returns:
      properties.Properties, The CloudSDK properties.
    """
    PropertiesFile._LOCK.acquire()
    try:
      if not PropertiesFile._PROPERTIES:
        config_paths = config.Paths()
        named_configs.WarnOnActiveNamedConfigMissing()
        paths = [config_paths.installation_properties_path,
                 named_configs.GetEffectiveNamedConfigFile(),
                 config_paths.workspace_properties_path]
        # Filter out None elements in paths
        paths = [p for p in paths if p]
        PropertiesFile._PROPERTIES = PropertiesFile(paths)

        # Warn if loading file from deperecated paths

        # Setting PropertiesFile._ALREADY_GAVE_DEPRECATION_WARNINGS is used
        # to avoid printing redundant warnings after properties invalidation.
        if not PropertiesFile._ALREADY_GAVE_DEPRECATION_WARNINGS:

          PropertiesFile._ALREADY_GAVE_DEPRECATION_WARNINGS = True

          if ((config_paths.user_properties_path in paths) and
              os.path.isfile(config_paths.user_properties_path)):
            # Write to standard output directly as importing `logging` here
            # messes up the logging boot-strap process.  We could probably do
            # a more principled refactor to avoid this, but it doesn't seem
            # worthwhile for a temporary warning message.
            sys.stderr.write("""\
Loading legacy configuration file: [{0}]
This configuration file is deprecated and will not be read in a future
gcloud release.  gcloud will automatically migrate your current settings to the
new configuration format the next time you set a property by running:
  $ gcloud config set PROPERTY VALUE
You may also run:
  $ gcloud init
to create a new configuration and walk you through initializing some basic
settings.  You can find more information on named configurations by running:
  $ gcloud topic configurations

""".format(config_paths.user_properties_path))

          if ((config_paths.workspace_properties_path in paths) and
              os.path.isfile(config_paths.workspace_properties_path)):
            sys.stderr.write(
                'Loading workspace configuration file: [{0}].\n'
                'Workspace configuration files are deprecated and will '
                'not be read in a future gcloud release.\n'.format(
                    config_paths.workspace_properties_path))
    finally:
      PropertiesFile._LOCK.release()
    return PropertiesFile._PROPERTIES

  @staticmethod
  def Invalidate():
    """Invalidate the chached property values."""
    PropertiesFile._PROPERTIES = None

  def __init__(self, paths):
    """Creates a new PropertiesFile and load from the given paths.

    Args:
      paths: [str], List of files to load properties from, in order.
    """
    self._properties = {}

    for properties_path in paths:
      self.__Load(properties_path)

  def __Load(self, properties_path):
    """Loads properties from the given file.

    Overwrites anything already known.

    Args:
      properties_path: str, Path to the file containing properties info.
    """
    parsed_config = ConfigParser.ConfigParser()
    try:
      parsed_config.read(properties_path)
    except ConfigParser.ParsingError as e:
      raise PropertiesParseError(e.message)

    for section in parsed_config.sections():
      if section not in self._properties:
        self._properties[section] = {}
      self._properties[section].update(dict(parsed_config.items(section)))

  def Get(self, prop):
    """Gets the value of the given property.

    Args:
      prop: Property, The property to get.

    Returns:
      str, The value for the given section and property, or None if it is not
        set.
    """
    try:
      return self._properties[prop.section][prop.name]
    except KeyError:
      return None


def DisplayProperties(writer, properties):
  """Pretty prints the properties passed in a dictionary.

  Args:
    writer: a file-like object to receive output
    properties: {section: {property: value}} or {property: value} formatted
      dictionary

  Returns:
    None
  """

  for section, props in sorted(properties.iteritems()):
    writer.write('[{section}]\n'.format(section=section))
    for prop, value in sorted(props.iteritems()):
      if value is None:
        writer.write('{prop} (unset)\n'.format(prop=prop))
      else:
        writer.write('{prop} = {value}\n'.format(prop=prop, value=value))


def GetMetricsEnvironment():
  """Get the metrics environment.

  Returns the property metrics/environment if set, if not, it tries to deduce if
  we're on some known platforms like devshell or GCE.

  Returns:
    None, if no environment is set or found
    str, a string denoting the environment if one is set or found
  """

  environment = VALUES.metrics.environment.Get()
  if environment:
    return environment

  # No explicit environment defined, try to deduce it.
  if c_devshell.IsDevshellEnvironment():
    return 'devshell'
  if gce_cache.GetOnGCE(check_age=False):
    return 'GCE'

  return None
