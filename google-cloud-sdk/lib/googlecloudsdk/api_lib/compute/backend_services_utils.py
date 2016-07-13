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
    # Assume global by default.
    self.global_request = getattr(args, 'region', None) is None

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
