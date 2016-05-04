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
      # return self.compute.regionalBackendServices
      raise exceptions.ToolException(
          'Regional backends services are not supported')

  @property
  def resource_type(self):
    return 'backendServices'

  def CreateGlobalRequests(self, args):
    """Override to return a list of one of more globally-scoped request."""

  def CreateRegionalRequests(self, args):
    """Override to return a list of one of more regionally-scoped request."""

  def CreateRequests(self, args):
    # Assume global by default.
    self.global_request = not getattr(args, 'region', None)

    if self.global_request:
      return self.CreateGlobalRequests(args)
    else:
      return self.CreateRegionalRequests(args)

  def Format(self, args):
    return self.ListFormat(args)
