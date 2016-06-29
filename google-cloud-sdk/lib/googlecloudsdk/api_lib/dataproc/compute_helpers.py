# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Constants for the dataproc tool."""

from googlecloudsdk.api_lib.compute import base_classes as compute_base
from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.api_lib.compute import scope_prompter
from googlecloudsdk.api_lib.compute import utils as compute_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core.credentials import http


# Copy into dataproc for cleaner separation
SCOPE_ALIASES = compute_constants.SCOPES


def ExpandScopeAliases(scopes):
  """Replace known aliases in the list of scopes provided by the user."""
  scopes = scopes or []
  expanded_scopes = []
  for scope in scopes:
    if scope in SCOPE_ALIASES:
      expanded_scopes.append(SCOPE_ALIASES[scope])
    else:
      # Validate scopes server side.
      expanded_scopes.append(scope)
  return sorted(expanded_scopes)


class ZoneWrapper(object):
  """Abstract data type holding a zone."""
  zone = None


class ConfigurationHelper(scope_prompter.ScopePrompter):
  """Helper that uses compute component logic to build GceConfiguration."""

  def __init__(self, batch_url, compute, project, resources):
    """Sets fields expected by ScopePrompter."""
    self.batch_url = batch_url
    self.compute = compute
    self.project = project
    self.resources = resources
    self.resource_type = None
    self.http = http.Http()

  @classmethod
  def FromContext(cls, context):
    """Updates required global state and constructs ConfigurationHelper."""
    holder = compute_base.ComputeApiHolder(base.ReleaseTrack.GA)
    batch_url = holder.client.batch_url
    compute = holder.client.apitools_client
    resources = holder.resources
    zone_prop = properties.VALUES.compute.zone
    project_prop = properties.VALUES.core.project
    project = project_prop.Get(required=True)
    resources.SetParamDefault(
        'compute', None, 'project', resolvers.FromProperty(project_prop))
    resources.SetParamDefault(
        'compute', None, 'zone', resolvers.FromProperty(zone_prop))
    return cls(batch_url, compute, project, resources)

  def _GetResourceUri(
      self, resource_name, resource_type, region=None, zone=None):
    """Convert a GCE resource short-name into a URI."""
    if not resource_name:
      # Resource must be optional and server-specified. Ignore it.
      return resource_name
    if region:
      resource_ref = self.CreateRegionalReference(
          resource_name, region, resource_type=resource_type)
    elif zone:
      resource_ref = self.CreateZonalReference(
          resource_name, zone, resource_type=resource_type)
    else:
      resource_ref = self.CreateGlobalReference(
          resource_name, resource_type=resource_type)
    return resource_ref.SelfLink()

  def _GetZoneRef(self, cluster_name):
    """Get GCE zone resource prompting if necessary."""
    # Instances is an arbitrary GCE zonal resource type.
    if compute_utils.HasApiParamDefaultValue(
        self.resources, 'instances', 'zone'):
      zone = None
    else:
      # Dummy wrapper to let PromptForScope set the zone of.
      wrapped_zone = ZoneWrapper()
      self.PromptForScope(
          ambiguous_refs=[(cluster_name, wrapped_zone)],
          attributes=['zone'],
          services=[self.compute.zones],
          resource_type='cluster',
          flag_names=['--zone', '-z'],
          prefix_filter=None)
      zone = wrapped_zone.zone
    zone_ref = self.resources.Parse(zone, collection='compute.zones')
    return zone_ref

  def ResolveGceUris(
      self,
      cluster_name,
      image,
      master_machine_type,
      worker_machine_type,
      network,
      subnetwork):
    """Build dict of GCE URIs for Dataproc cluster request."""
    zone_ref = self._GetZoneRef(cluster_name)
    zone = zone_ref.Name()
    region = compute_utils.ZoneNameToRegionName(zone)
    uris = {
        'image': self._GetResourceUri(image, 'images'),
        'master_machine_type':
            self._GetResourceUri(
                master_machine_type, 'machineTypes', zone=zone),
        'worker_machine_type':
            self._GetResourceUri(
                worker_machine_type, 'machineTypes', zone=zone),
        'network': self._GetResourceUri(network, 'networks'),
        'subnetwork':
            self._GetResourceUri(subnetwork, 'subnetworks', region=region),
        'zone': zone_ref.SelfLink(),
    }
    return uris
