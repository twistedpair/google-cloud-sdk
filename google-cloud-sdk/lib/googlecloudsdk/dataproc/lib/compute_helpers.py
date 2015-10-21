# Copyright 2015 Google Inc. All Rights Reserved.

"""Constants for the dataproc tool."""

from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.shared.compute import constants as compute_constants
from googlecloudsdk.shared.compute import scope_prompter
from googlecloudsdk.shared.compute import utils as compute_utils


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

  def __init__(self, batch_url, compute, http, project, resources):
    """Sets fields expected by ScopePrompter."""
    self.batch_url = batch_url
    self.compute = compute
    self.http = http
    self.project = project
    self.resources = resources
    self.resource_type = None

  @classmethod
  def FromContext(cls, context):
    """Updates required global state and constructs ConfigurationHelper."""
    http = context['http']
    compute_utils.UpdateContextEndpointEntries(context, http)
    batch_url = context['batch-url']
    compute = context['compute']
    resources = context['resources']
    zone_prop = properties.VALUES.compute.zone
    project_prop = properties.VALUES.core.project
    project = project_prop.Get(required=True)
    resources.SetParamDefault(
        'compute', None, 'project', resolvers.FromProperty(project_prop))
    resources.SetParamDefault(
        'compute', None, 'zone', resolvers.FromProperty(zone_prop))
    return cls(batch_url, compute, http, project, resources)

  def _GetResourceUri(self, resource_name, resource_type, zone=None):
    """Convert a GCE resource short-name into a URI."""
    if not resource_name:
      # Resource must be optional and server-specified. Ignore it.
      return resource_name
    if zone:
      resource_ref = self.CreateZonalReference(
          resource_name, zone, resource_type=resource_type)
    else:
      resource_ref = self.CreateGlobalReference(
          resource_name, resource_type=resource_type)
    return resource_ref.SelfLink()

  def _GetZoneRef(self, cluster_name):
    """Get GCE zone resource prompting if necessary."""
    # Instances is an arbitrary GCE zonal resource type.
    if self.HasDefaultValue('instances', 'zone'):
      zone = None
    else:
      # Dummy wrapper to let PromptForScope set the zone of.
      wrapped_zone = ZoneWrapper()
      self.PromptForScope(
          ambiguous_refs=[(cluster_name, wrapped_zone)],
          attribute='zone',
          service=self.compute.zones,
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
      network):
    """Build dict of GCE URIs for Dataproc cluster request."""
    zone_ref = self._GetZoneRef(cluster_name)
    uris = {
        'image': self._GetResourceUri(image, 'images'),
        'master_machine_type': self._GetResourceUri(
            master_machine_type, 'machineTypes', zone=zone_ref.Name()),
        'worker_machine_type': self._GetResourceUri(
            worker_machine_type, 'machineTypes', zone=zone_ref.Name()),
        'network': self._GetResourceUri(network, 'networks'),
        'zone': zone_ref.SelfLink(),
    }
    return uris
