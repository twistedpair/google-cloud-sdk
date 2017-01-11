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
"""Code that's shared between multiple backend-services subcommands."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import scope as compute_scope
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class CacheKeyQueryStringException(core_exceptions.Error):

  def __init__(self):
    super(CacheKeyQueryStringException, self).__init__(
        'cache-key-query-string-whitelist and '
        'cache-key-query-string-blacklist may only be set when '
        'cache-key-include-query-string is enabled.')


def IsRegionDefaultModeWarnOtherwise(print_warning=True):
  """Returns the value of core/default_regional_backend_service."""
  default_regional = (
      properties.VALUES.core.default_regional_backend_service.GetBool())
  if default_regional is None:
    # Print a warning and use False if it isn't set.
    if print_warning:
      log.warn(
          'This backend service is assumed to be global. To access a regional '
          'backend service, provide the --region flag.\n'
          'In the future, backend services will be regional by default unless '
          'the --global flag is specified.')
    return False

  return default_regional


def GetDefaultScope(args):
  """Gets the default compute flags scope enum value."""
  if IsRegionDefaultModeWarnOtherwise(
      print_warning=(
          getattr(args, 'global', None) is None and
          getattr(args, 'region', None) is None)):
    return compute_scope.ScopeEnum.REGION
  else:
    return compute_scope.ScopeEnum.GLOBAL


def IsRegionalRequest(args):
  """Determines whether the args specify a regional or global request."""
  if IsRegionDefaultModeWarnOtherwise(
      print_warning=(
          getattr(args, 'global', None) is None and
          getattr(args, 'region', None) is None)):
    # Return True (regional request) unless --global was specified.
    return getattr(args, 'global', None) is None
  else:
    # Return False (global request) unless --region was specified.
    return getattr(args, 'region', None) is not None


def GetHealthChecks(args, resource_parser):
  """Returns health check URIs from arguments."""
  health_check_refs = []

  if args.http_health_checks:
    health_check_refs.extend(resource_parser.CreateGlobalReferences(
        args.http_health_checks, resource_type='httpHealthChecks'))

  if getattr(args, 'https_health_checks', None):
    health_check_refs.extend(resource_parser.CreateGlobalReferences(
        args.https_health_checks, resource_type='httpsHealthChecks'))

  if getattr(args, 'health_checks', None):
    if health_check_refs:
      raise exceptions.ToolException(
          'Mixing --health-checks with --http-health-checks or with '
          '--https-health-checks is not supported.')
    else:
      health_check_refs.extend(resource_parser.CreateGlobalReferences(
          args.health_checks, resource_type='healthChecks'))

  return [health_check_ref.SelfLink() for health_check_ref in health_check_refs]


def GetIAP(args, messages, existing_iap_settings=None):
  """Returns IAP settings from arguments."""

  if 'enabled' in args.iap and 'disabled' in args.iap:
    raise exceptions.InvalidArgumentException(
        '--iap', 'Must specify only one of [enabled] or [disabled]')

  iap_settings = messages.BackendServiceIAP()
  if 'enabled' in args.iap:
    iap_settings.enabled = True
  elif 'disabled' in args.iap:
    iap_settings.enabled = False
  elif existing_iap_settings is not None:
    iap_settings.enabled = existing_iap_settings.enabled

  if iap_settings.enabled:
    # If either oauth2-client-id or oauth2-client-secret is specified,
    # then the other should also be specified.
    if 'oauth2-client-id' in args.iap or 'oauth2-client-secret' in args.iap:
      iap_settings.oauth2ClientId = args.iap.get('oauth2-client-id')
      iap_settings.oauth2ClientSecret = args.iap.get('oauth2-client-secret')
      if not iap_settings.oauth2ClientId or not iap_settings.oauth2ClientSecret:
        raise exceptions.InvalidArgumentException(
            '--iap',
            'Both [oauth2-client-id] and [oauth2-client-secret] must be '
            'specified together')

  return iap_settings


class BackendServiceMutator(base_classes.BaseAsyncMutator):
  """Makes mutator respect Regional/Global resources."""

  @property
  def service(self):
    if self.global_request:
      return self.compute.backendServices
    else:
      return self.compute.regionBackendServices

  @property
  def resource_type(self):
    return 'backendServices'

  def CreateGlobalRequests(self, args):
    """Override to return a list of one of more globally-scoped request."""

  def CreateRegionalRequests(self, args):
    """Override to return a list of one of more regionally-scoped request."""

  def CreateRequests(self, args):
    self.global_request = not IsRegionalRequest(args)

    if self.global_request:
      return self.CreateGlobalRequests(args)
    else:
      return self.CreateRegionalRequests(args)

  def Format(self, args):
    return self.ListFormat(args)


def ValidateBalancingModeArgs(messages, add_or_update_backend_args,
                              current_balancing_mode=None):
  """Check whether the setup of the backend LB related fields is valid.

  Args:
    messages: API messages class, determined by release track.
    add_or_update_backend_args: argparse Namespace. The arguments
      provided to add-backend or update-backend commands.
    current_balancing_mode: BalancingModeValueValuesEnum. The balancing mode
      of the existing backend, in case of update-backend command. Must be
      None otherwise.
  """
  balancing_mode = current_balancing_mode
  if add_or_update_backend_args.balancing_mode:
    balancing_mode = messages.Backend.BalancingModeValueValuesEnum(
        add_or_update_backend_args.balancing_mode)

  invalid_arg = None
  if balancing_mode == messages.Backend.BalancingModeValueValuesEnum.RATE:
    if add_or_update_backend_args.max_utilization is not None:
      invalid_arg = '--max-utilization'
    elif add_or_update_backend_args.max_connections is not None:
      invalid_arg = '--max-connections'
    elif add_or_update_backend_args.max_connections_per_instance is not None:
      invalid_arg = '--max-connections-per-instance'

    if invalid_arg is not None:
      raise exceptions.InvalidArgumentException(
          invalid_arg,
          'cannot be set with RATE balancing mode')
  elif (balancing_mode ==
        messages.Backend.BalancingModeValueValuesEnum.CONNECTION):
    if add_or_update_backend_args.max_utilization is not None:
      invalid_arg = '--max-utilization'
    elif add_or_update_backend_args.max_rate is not None:
      invalid_arg = '--max-rate'
    elif add_or_update_backend_args.max_rate_per_instance is not None:
      invalid_arg = '--max-rate-per-instance'

    if invalid_arg is not None:
      raise exceptions.InvalidArgumentException(
          invalid_arg,
          'cannot be set with CONNECTION balancing mode')


def UpdateCacheKeyPolicy(args, cache_key_policy):
  """Sets the cache_key_policy according to the command line arguments.

  Args:
    args: Arguments specified through command line.
    cache_key_policy: new CacheKeyPolicy to be set (or preexisting one if
      using update).
  """
  if args.cache_key_include_protocol is not None:
    cache_key_policy.includeProtocol = args.cache_key_include_protocol
  if args.cache_key_include_host is not None:
    cache_key_policy.includeHost = args.cache_key_include_host
  if args.cache_key_include_query_string is not None:
    cache_key_policy.includeQueryString = args.cache_key_include_query_string
    if not args.cache_key_include_query_string:
      cache_key_policy.queryStringWhitelist = []
      cache_key_policy.queryStringBlacklist = []
  if args.cache_key_query_string_whitelist is not None:
    (cache_key_policy.queryStringWhitelist
    ) = args.cache_key_query_string_whitelist
    cache_key_policy.includeQueryString = True
    cache_key_policy.queryStringBlacklist = []
  if args.cache_key_query_string_blacklist is not None:
    (cache_key_policy.queryStringBlacklist
    ) = args.cache_key_query_string_blacklist
    cache_key_policy.includeQueryString = True
    cache_key_policy.queryStringWhitelist = []


def ValidateCacheKeyPolicyArgs(cache_key_policy_args):
  # If includeQueryString is not set, it should default to True
  include_query_string = (
      cache_key_policy_args.cache_key_include_query_string is None or
      cache_key_policy_args.cache_key_include_query_string)
  if not include_query_string:
    if (cache_key_policy_args.cache_key_query_string_whitelist is not None or
        cache_key_policy_args.cache_key_query_string_blacklist is not None):
      raise CacheKeyQueryStringException()
