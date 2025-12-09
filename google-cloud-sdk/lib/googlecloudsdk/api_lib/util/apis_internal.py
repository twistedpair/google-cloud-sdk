# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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
"""Library for obtaining API clients and messages.

This should only be called by api_lib.util.apis, core.resources, gcloud meta
commands, and module tests.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis_util
from googlecloudsdk.api_lib.util import resource as resource_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import transport
from googlecloudsdk.generated_clients.apis import apis_map
import six
from six.moves.urllib.parse import urljoin
from six.moves.urllib.parse import urlparse
from six.moves.urllib.parse import urlunparse


def _GetApiNameAndAlias(api_name):
  # pylint:disable=protected-access
  return (apis_util._API_NAME_ALIASES.get(api_name, api_name), api_name)


def _GetDefaultVersion(api_name):
  api_name, _ = _GetApiNameAndAlias(api_name)
  api_vers = apis_map.MAP.get(api_name, {})
  for ver, api_def in six.iteritems(api_vers):
    if api_def.default_version:
      return ver
  return None


def _GetApiNames():
  """Returns list of avaiblable apis, ignoring the version."""
  return sorted(apis_map.MAP.keys())


def _GetVersions(api_name):
  """Return available versions for given api.

  Args:
    api_name: str, The API name (or the command surface name, if different).

  Raises:
    apis_util.UnknownAPIError: If api_name does not exist in the APIs map.

  Returns:
    list, of version names.
  """
  api_name, _ = _GetApiNameAndAlias(api_name)
  version_map = apis_map.MAP.get(api_name, None)
  if version_map is None:
    raise apis_util.UnknownAPIError(api_name)
  return list(version_map.keys())


def GetApiDef(api_name, api_version):
  """Returns the APIDef for the specified API and version.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Raises:
    apis_util.UnknownAPIError: If api_name does not exist in the APIs map.
    apis_util.UnknownVersionError: If api_version does not exist for given
      api_name in the APIs map.

  Returns:
    APIDef, The APIDef for the specified API and version.
  """
  api_name, api_name_alias = _GetApiNameAndAlias(api_name)
  if api_name not in apis_map.MAP:
    raise apis_util.UnknownAPIError(api_name)

  version_overrides = properties.VALUES.api_client_overrides.AllValues()

  # First attempt to get api specific override, then full surface override.
  version_override = version_overrides.get('{}/{}'.format(
      api_name, api_version))
  if not version_override:
    version_override = version_overrides.get(api_name_alias, None)

  api_version = version_override or api_version

  api_versions = apis_map.MAP[api_name]
  if api_version is None or api_version not in api_versions:
    raise apis_util.UnknownVersionError(api_name, api_version)
  else:
    api_def = api_versions[api_version]

  return api_def


def _GetClientClass(api_name, api_version):
  """Returns the client class for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    base_api.BaseApiClient, Client class for the specified API.
  """
  api_def = GetApiDef(api_name, api_version)
  return _GetClientClassFromDef(api_def)


def _GetClientClassFromDef(api_def):
  """Returns the apitools client class for the API definition specified in args.

  Args:
    api_def: apis_map.APIDef, The definition of the API.

  Returns:
    base_api.BaseApiClient, Client class for the specified API.
  """
  client_full_classpath = api_def.apitools.client_full_classpath
  module_path, client_class_name = client_full_classpath.rsplit('.', 1)
  module_obj = __import__(module_path, fromlist=[client_class_name])
  return getattr(module_obj, client_class_name)


def _GetClientInstance(api_name,
                       api_version,
                       no_http=False,
                       http_client=None,
                       check_response_func=None,
                       http_timeout_sec=None,
                       region=None):
  """Returns an instance of the API client specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    no_http: bool, True to not create an http object for this client.
    http_client: bring your own http client to use. Incompatible with
      no_http=True.
    check_response_func: error handling callback to give to apitools.
    http_timeout_sec: int, seconds of http timeout to set, defaults if None.
    region: str, Region (or multi-region) for regionalized endpoints (REP).

  Returns:
    base_api.BaseApiClient, An instance of the specified API client.
  """

  # pylint: disable=g-import-not-at-top
  if no_http:
    assert http_client is None
  elif http_client is None:
    # Normal gcloud authentication
    # Import http only when needed, as it depends on credential infrastructure
    # which is not needed in all cases.
    from googlecloudsdk.core.credentials import transports
    http_client = transports.GetApitoolsTransport(
        response_encoding=transport.ENCODING,
        timeout=http_timeout_sec if http_timeout_sec else 'unset')

  client_class = _GetClientClass(api_name, api_version)
  client_instance = client_class(
      url=_GetEffectiveApiEndpoint(api_name, api_version, client_class, region),
      get_credentials=False,
      http=http_client)
  if check_response_func is not None:
    client_instance.check_response_func = check_response_func
  api_key = properties.VALUES.core.api_key.Get()
  if api_key:
    client_instance.AddGlobalParam('key', api_key)
    header = 'X-Google-Project-Override'
    client_instance.additional_http_headers[header] = 'apikey'
  return client_instance


def _GetGapicClientClass(api_name,
                         api_version,
                         transport_choice=apis_util.GapicTransport.GRPC):
  """Returns the GAPIC client class for the API def specified by the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    transport_choice: apis_util.GapicTransport, The transport to be used by the
      client.
  """
  api_def = GetApiDef(api_name, api_version)
  if transport_choice == apis_util.GapicTransport.GRPC_ASYNCIO:
    client_full_classpath = api_def.gapic.async_client_full_classpath
  elif transport_choice == apis_util.GapicTransport.REST:
    client_full_classpath = api_def.gapic.rest_client_full_classpath
  else:
    client_full_classpath = api_def.gapic.client_full_classpath

  module_path, client_class_name = client_full_classpath.rsplit('.', 1)
  module_obj = __import__(module_path, fromlist=[client_class_name])
  return getattr(module_obj, client_class_name)


def _GetGapicClientInstance(
    api_name,
    api_version,
    credentials,
    address_override_func=None,
    transport_choice=apis_util.GapicTransport.GRPC,
    attempt_direct_path=False,
    redact_request_body_reason=None,
    custom_interceptors=None,
):
  """Returns an instance of the GAPIC API client specified in the args.

  For apitools API clients, the API endpoint override is something like
  http://compute.googleapis.com/v1/. For GAPIC API clients, the DEFAULT_ENDPOINT
  is something like compute.googleapis.com. To use the same endpoint override
  property for both, we use the netloc of the API endpoint override.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.
    credentials: google.auth.credentials.Credentials, the credentials to use.
    address_override_func: function, function to call to override the client
      host. It takes a single argument which is the original host.
    transport_choice: apis_util.GapicTransport, The transport to be used by the
      client.
    attempt_direct_path: bool, True if we want to attempt direct path gRPC where
      possible.
    redact_request_body_reason: str, the reason why the request body must be
      redacted if --log-http is used. If None, the body is not redacted.
    custom_interceptors: list[grpc interceptor], a list of custom interceptors
    to add to the channel.

  Returns:
    An instance of the specified GAPIC API client.
  """
  def AddressOverride(address):
    try:
      endpoint_override = properties.VALUES.api_endpoint_overrides.Property(
          api_name).Get()
    except properties.NoSuchPropertyError:
      endpoint_override = None

    if endpoint_override:
      address = urlparse(endpoint_override).netloc

    if address_override_func:
      address = address_override_func(address)

    if endpoint_override is not None:
      return address

    return UniversifyAddress(address)

  client_class = _GetGapicClientClass(
      api_name, api_version, transport_choice=transport_choice)

  return client_class(
      credentials,
      address_override_func=AddressOverride,
      mtls_enabled=_MtlsEnabled(api_name, api_version),
      attempt_direct_path=attempt_direct_path,
      redact_request_body_reason=redact_request_body_reason,
      custom_interceptors=custom_interceptors,
  )


def UniversifyAddress(address):
  """Update a URL based on the current universe domain."""
  universe_domain_property = properties.VALUES.core.universe_domain
  universe_domain = universe_domain_property.Get()
  if (address is not None and
      universe_domain_property.default != universe_domain):
    address = address.replace(universe_domain_property.default,
                              universe_domain, 1)
  return address


def _GetRegionalizedEndpoint(domain, region):
  """Returns regionalized domain.

  Regional endpoints (REPs) have the following format:
    {service}.{region}.rep.googleapis.com

  Args:
    domain: Domain for the API in form {service}.googleapis.com.
    region: REP region (or multi-region).

  Returns:
    str, Regionalized domain.
  """
  if region is None:
    raise ValueError('Region must be provided.')
  if domain.count('.') > 2:
    raise ValueError(
        'Base URLs should have form {service}.googleapis.com;'
        f' received: [{domain}].')
  service, base_domain = domain.split('.', 1)
  return f'{service}.{region}.rep.{base_domain}'


class UnsupportedEndpointModeError(exceptions.Error):
  """Error when regional/endpoint_mode property is unsupported by a command."""


def _ShouldUseRegionalEndpoints():
  """Returns whether or not regional endpoint should be used.

  Depending on the user-specified regional/endpoint_mode setting and the
  developer-specified command annotation, this function calculates whether or
  not to use regional endpoints. In case of an invalid combination, an error
  will be raised.

  Returns:
    bool, Whether to use regional endpoints.
  Raises:
    UnsupportedEndpointModeError: If the command does not support the given
      endpoint mode.
  """
  mode = properties.VALUES.regional.endpoint_mode.Get()
  compatibility = properties.VALUES.regional.endpoint_compatibility.Get()
  if mode == properties.VALUES.regional.REGIONAL and compatibility is None:
    raise UnsupportedEndpointModeError(
        f'The regional/endpoint_mode property is currently set to [{mode}], but'
        ' this command does not support regional endpoints.')
  if (
      mode == properties.VALUES.regional.GLOBAL and
      compatibility == properties.VALUES.regional.REQUIRED
  ):
    raise UnsupportedEndpointModeError(
        f'The regional/endpoint_mode property is currently set to [{mode}], but'
        ' this command only supports regional endpoints.')
  return (
      compatibility == properties.VALUES.regional.REQUIRED
      or mode == properties.VALUES.regional.REGIONAL
      or (
          mode == properties.VALUES.regional.REGIONAL_PREFERRED
          and compatibility == properties.VALUES.regional.SUPPORTED
      )
  )


def _GetMtlsEndpoint(api_name, api_version, client_class=None):
  """Returns mtls endpoint."""
  api_def = GetApiDef(api_name, api_version)
  if api_def.apitools:
    client_class = client_class or _GetClientClass(api_name, api_version)
  else:
    client_class = client_class or _GetGapicClientClass(api_name, api_version)
  return api_def.mtls_endpoint_override or client_class.MTLS_BASE_URL


def _MtlsEnabled(api_name, api_version):
  """Checks if the API of the given version should use mTLS.

  If context_aware/always_use_mtls_endpoint is True, then mTLS will always be
  used.

  If context_aware/use_client_certificate is True, then mTLS will be used only
  if the API version is in the mTLS allowlist.

  gcloud maintains a client-side allowlist for the mTLS feature
  (go/gcloud-rollout-mtls).

  Args:
    api_name: str, The API name.
    api_version: str, The version of the API.

  Returns:
    True if the given service and version is in the mTLS allowlist.
  """
  if properties.VALUES.context_aware.always_use_mtls_endpoint.GetBool():
    return True

  if not properties.VALUES.context_aware.use_client_certificate.GetBool():
    return False

  api_def = GetApiDef(api_name, api_version)
  return api_def.enable_mtls


def _BuildEndpointOverride(endpoint_override, base_url):
  """Constructs a normalized endpoint URI depending on the client base_url."""
  url_base = urlparse(base_url)
  url_endpoint_override = urlparse(endpoint_override)
  if url_base.path == '/' or url_endpoint_override.path != '/':
    return endpoint_override
  return urljoin(
      '{}://{}'.format(url_endpoint_override.scheme,
                       url_endpoint_override.netloc), url_base.path)


def _GetBaseUrlFromApi(api_name, api_version):
  """Returns base url for given api."""
  if GetApiDef(api_name, api_version).apitools:
    client_class = _GetClientClass(api_name, api_version)
  else:
    client_class = _GetGapicClientClass(api_name, api_version)

  if hasattr(client_class, 'BASE_URL'):
    client_base_url = client_class.BASE_URL
  else:
    try:
      client_base_url = _GetResourceModule(api_name, api_version).BASE_URL
    except AttributeError:
      client_base_url = 'https://{}.googleapis.com/{}'.format(
          api_name, api_version
      )
  return UniversifyAddress(client_base_url)


def _GetEffectiveApiEndpoint(
    api_name, api_version, client_class=None, region=None):
  """Returns effective endpoint for given api."""
  try:
    endpoint_override = properties.VALUES.api_endpoint_overrides.Property(
        api_name).Get()
  except properties.NoSuchPropertyError:
    endpoint_override = None

  api_def = GetApiDef(api_name, api_version)
  if api_def.apitools:
    client_class = client_class or _GetClientClass(api_name, api_version)
  else:
    client_class = client_class or _GetGapicClientClass(api_name, api_version)
  client_base_url = _GetBaseUrlFromApi(api_name, api_version)
  if endpoint_override:
    address = _BuildEndpointOverride(endpoint_override, client_base_url)
  elif _MtlsEnabled(api_name, api_version):
    address = UniversifyAddress(
        _GetMtlsEndpoint(api_name, api_version, client_class)
    )
  # Note that regionalized endpoints are incompatible with mTLS / non-Google
  # universe domains.
  elif _ShouldUseRegionalEndpoints():
    url_base = urlparse(client_base_url)
    regionalized_domain = _GetRegionalizedEndpoint(url_base.netloc, region)
    address = urlunparse(url_base._replace(netloc=regionalized_domain))
  else:
    address = client_base_url

  return address


def _GetMessagesModule(api_name, api_version):
  """Returns the messages module for the API specified in the args.

  Args:
    api_name: str, The API name (or the command surface name, if different).
    api_version: str, The version of the API.

  Returns:
    Module containing the definitions of messages for the specified API.
  """
  api_def = GetApiDef(api_name, api_version)
  # fromlist below must not be empty, see:
  # http://stackoverflow.com/questions/2724260/why-does-pythons-import-require-fromlist.
  return __import__(
      api_def.apitools.messages_full_modulepath, fromlist=['something'])


def _GetResourceModule(api_name, api_version):
  """Imports and returns given api resources module."""

  api_def = GetApiDef(api_name, api_version)
  # fromlist below must not be empty, see:
  # http://stackoverflow.com/questions/2724260/why-does-pythons-import-require-fromlist.
  if api_def.apitools:
    return __import__(
        api_def.apitools.class_path + '.' + 'resources', fromlist=['something']
    )
  # ApiDef must be gapic-only:
  return __import__(
      api_def.gapic.class_path + '.' + 'resources', fromlist=['something']
  )


def _GetApiCollections(api_name, api_version):
  """Yields all collections for for given api."""

  try:
    resources_module = _GetResourceModule(api_name, api_version)
  except ImportError:
    pass
  else:
    for collection in resources_module.Collections:
      yield resource_util.CollectionInfo(
          api_name,
          api_version,
          resources_module.BASE_URL,
          resources_module.DOCS_URL,
          collection.collection_name,
          collection.path,
          collection.flat_paths,
          collection.params,
          collection.enable_uri_parsing,
      )
