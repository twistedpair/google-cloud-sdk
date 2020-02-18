# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utils for GKE Hub commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.container.hub import gkehub_api_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


def _ComputeClient():
  api_version = core_apis.ResolveVersion('compute')
  return core_apis.GetClientInstance('compute', api_version)


def MembershipRef(project, location, membership_id):
  """Get the resource name of a membership.

  Args:
    project: the project in which to create the membership
    location: the GCP region of the membership.
    membership_id: the ID of the membership.

  Returns:
    the full resource name of the membership in the format of
    `projects/{project}/locations/{location}/memberships/{membership_id}`
  """

  return '{}/memberships/{}'.format(ParentRef(project, location), membership_id)


def ParentRef(project, location):
  """Get the resource name of the parent collection of a membership.

  Args:
    project: the project of the parent collection.
    location: the GCP region of the membership.

  Returns:
    the resource name of the parent collection in the format of
    `projects/{project}/locations/{location}`.
  """

  return 'projects/{}/locations/{}'.format(project, location)


def CreateMembership(project,
                     membership_id,
                     description,
                     gke_cluster_self_link=None,
                     external_id=None,
                     release_track=None):
  """Creates a Membership resource in the GKE Hub API.

  Args:
    project: the project in which to create the membership
    membership_id: the value to use for the membership_id
    description: the value to put in the description field
    gke_cluster_self_link: the selfLink for the cluster if it is a GKE cluster,
      or None if it is not
    external_id: the unique id associated with the cluster,
      or None if it is not available.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.

  Returns:
    the created Membership resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  messages = client.MESSAGES_MODULE
  parent_ref = ParentRef(project, 'global')
  request = messages.GkehubProjectsLocationsMembershipsCreateRequest(
      membership=messages.Membership(description=description),
      parent=parent_ref,
      membershipId=membership_id,
  )
  if gke_cluster_self_link:
    endpoint = messages.MembershipEndpoint(
        gkeCluster=messages.GkeCluster(resourceLink=gke_cluster_self_link))
    request.membership.endpoint = endpoint
  if external_id:
    request.membership.externalId = external_id
  op = client.projects_locations_memberships.Create(request)
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  return waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_memberships,
                                  client.projects_locations_operations),
      op_resource, 'Waiting for membership to be created')


def GetMembership(name, release_track=None):
  """Gets a Membership resource from the GKE Hub API.

  Args:
    name: the full resource name of the membership to get, e.g.,
      projects/foo/locations/global/memberships/name.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.

  Returns:
    a Membership resource

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = gkehub_api_util.GetApiClientForTrack(release_track)
  return client.projects_locations_memberships.Get(
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsGetRequest(
          name=name))


def ProjectForClusterUUID(uuid, projects, release_track=None):
  """Retrieves the project that the cluster UUID has a Membership with.

  Args:
    uuid: the UUID of the cluster.
    projects: sequence of project IDs to consider.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.
  Returns:
    a project ID.

  Raises:
    apitools.base.py.HttpError: if any request returns an HTTP error
  """
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  for project in projects:
    if project:
      parent = 'projects/{}/locations/global'.format(project)
      membership_response = client.projects_locations_memberships.List(
          client.MESSAGES_MODULE
          .GkehubProjectsLocationsMembershipsListRequest(parent=parent))
      for membership in membership_response.resources:
        membership_uuid = _ClusterUUIDForMembershipName(membership.name)
        if membership_uuid == uuid:
          return project
  return None


def _ClusterUUIDForMembershipName(membership_name):
  """Extracts the cluster UUID from the Membership resource name.

  Args:
    membership_name: the full resource name of a membership, e.g.,
      projects/foo/locations/global/memberships/name.

  Returns:
    the name in the membership resource, a cluster UUID.

  Raises:
    exceptions.Error: if the membership was malformed.
  """

  match_membership = 'projects/.+/locations/global/memberships/(.+)'
  matches = re.compile(match_membership).findall(membership_name)
  if len(matches) != 1:
    # This should never happen.
    raise exceptions.Error(
        'unable to parse membership {}'.format(membership_name))
  return matches[0]


def DeleteMembership(name, release_track=None):
  """Deletes a membership from the GKE Hub.

  Args:
    name: the full resource name of the membership to delete, e.g.,
      projects/foo/locations/global/memberships/name.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.
  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = gkehub_api_util.GetApiClientForTrack(release_track)
  op = client.projects_locations_memberships.Delete(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsDeleteRequest(name=name))
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  waiter.WaitFor(
      waiter.CloudOperationPollerNoResources(
          client.projects_locations_operations), op_resource,
      'Waiting for membership to be deleted')


def ValidateExclusivity(cr_manifest, parent_ref, intended_membership,
                        release_track=None):
  """Validate the exclusivity state of the cluster.

  Args:
    cr_manifest: the YAML manifest of the Membership CR fetched from the
      cluster.
    parent_ref: the parent collection that the cluster is to be registered to.
    intended_membership: the ID of the membership to be created.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.
  Returns:
    the ValidateExclusivityResponse from API.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error.
  """
  # TODO(b/145955278): Use release_track to select the right Exclusivity API.
  release_track = base.ReleaseTrack.BETA
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  return client.projects_locations_memberships.ValidateExclusivity(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsValidateExclusivityRequest(
          parent=parent_ref,
          crManifest=cr_manifest,
          intendedMembership=intended_membership))


def GenerateExclusivityManifest(crd_manifest, cr_manifest, membership_ref,
                                release_track=None):
  """Generate the CR(D) manifests to apply to the registered cluster.

  Args:
    crd_manifest: the YAML manifest of the Membership CRD fetched from the
      cluster.
    cr_manifest: the YAML manifest of the Membership CR fetched from the
      cluster.
    membership_ref: the full resource name of the membership.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.

  Returns:
    the GenerateExclusivityManifestResponse from API.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error.
  """

  # TODO(b/145955278): remove static mapping after Exclusivity is promoted.
  release_track = base.ReleaseTrack.BETA
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  return client.projects_locations_memberships.GenerateExclusivityManifest(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsGenerateExclusivityManifestRequest(
          name=membership_ref,
          crdManifest=crd_manifest,
          crManifest=cr_manifest))


def GenerateConnectAgentManifest(membership_ref,
                                 image_pull_secret_content=None,
                                 is_upgrade=None,
                                 namespace=None,
                                 proxy=None,
                                 registry=None,
                                 version=None,
                                 release_track=None):
  """Generated the Connect Agent to apply to the registered cluster.

  Args:
    membership_ref: the full resource name of the membership.
    image_pull_secret_content: The image pull secret content to use for private
      registries or None if it is not available.
    is_upgrade: Is this is an upgrade operation, or None if it is not available.
    namespace: The namespace of the Connect Agent, or None if it is not
      available.
    proxy: The proxy address or None if it is not available.
    registry: The registry to pull the Connect Agent image if not using
      gcr.io/gkeconnect, or None if it is not available.
    version: The version of the Connect Agent to install/upgrade, or None if it
      is not available.
    release_track: the release_track used in the gcloud command, or None if it
      is not available.

  Returns:
    the GenerateConnectManifest from API.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error.
  """

  client = gkehub_api_util.GetApiClientForTrack(release_track)
  messages = client.MESSAGES_MODULE
  request = messages.GkehubProjectsLocationsMembershipsGenerateConnectManifestRequest(
      name=membership_ref)
  # Add optional flag values.
  if image_pull_secret_content:
    request.imagePullSecretContent = image_pull_secret_content.encode('ascii')
  if is_upgrade:
    request.isUpgrade = is_upgrade
  if namespace:
    request.namespace = namespace
  if proxy:
    request.proxy = proxy.encode('ascii')
  if registry:
    request.registry = registry
  if version:
    request.version = version
  return client.projects_locations_memberships.GenerateConnectManifest(request)


# TODO(b/145953996): Remove this method once
# gcloud.container.memberships.* has been ported
def GKEClusterSelfLink(kube_client):
  """Returns the selfLink of a cluster, if it is a GKE cluster.

  There is no straightforward way to obtain this information from the cluster
  API server directly. This method uses metadata on the Kubernetes nodes to
  determine the instance ID and project ID of a GCE VM, whose metadata is used
  to find the location of the cluster and its name.

  Args:
    kube_client: A Kubernetes client for the cluster to be registered.

  Returns:
    the full OnePlatform resource path of a GKE cluster, e.g.,
    //container.googleapis.com/project/p/location/l/cluster/c. If the cluster is
    not a GKE cluster, returns None.

  Raises:
    exceptions.Error: if there is an error fetching metadata from the cluster
      nodes
    calliope_exceptions.MinimumArgumentException: if a kubeconfig file
      cannot be deduced from the command line flags or environment
    <others?>
  """

  # Get the instance ID and provider ID of some VM. Since all of the VMs should
  # have the same cluster name, arbitrarily choose the first one that is
  # returned from kubectl.

  # The instance ID field is unique to GKE clusters: Kubernetes-on-GCE clusters
  # do not have this field.
  vm_instance_id, err = kube_client.GetResourceField(
      None, 'nodes',
      '.items[0].metadata.annotations.container\\.googleapis\\.com/instance_id')
  # If we cannot determine this is a GKE cluster, no resource link will be
  # attached.
  if err or (not vm_instance_id):
    return None

  # The provider ID field exists on both GKE-on-GCP and Kubernetes-on-GCP
  # clusters. Therefore, even though it contains all of the necessary
  # information, it's presence does not guarantee that this is a GKE cluster.
  vm_provider_id, err = kube_client.GetResourceField(
      None, 'nodes', '.items[0].spec.providerID')
  if err or not vm_provider_id:
    raise exceptions.Error(
        'Error retrieving VM provider ID for cluster node: {}'.format(
            err or 'field does not exist on object'))

  # Parse the providerID to determine the project ID and VM zone.
  matches = re.match(r'^gce://([^/]+?)/([^/]+?)/.+', vm_provider_id)
  if not matches or matches.lastindex != 2:
    raise exceptions.Error(
        'Error parsing project ID and VM zone from provider ID: unexpected format "{}" for provider ID'
        .format(vm_provider_id))
  project_id = matches.group(1)
  vm_zone = matches.group(2)

  # Call the compute API to get the VM instance with this instance ID.
  compute_client = _ComputeClient()
  request = compute_client.MESSAGES_MODULE.ComputeInstancesGetRequest(
      instance=vm_instance_id, project=project_id, zone=vm_zone)
  instance = compute_client.instances.Get(request)
  if not instance:
    raise exceptions.Error('Empty GCE instance returned from compute API.')
  if not instance.metadata:
    raise exceptions.Error(
        'GCE instance with empty metadata returned from compute API.')

  # Read the cluster name and location from the VM instance's metadata.

  # Convert the metadata message to a Python dict.
  metadata = {}
  for item in instance.metadata.items:
    metadata[item.key] = item.value

  cluster_name = metadata.get('cluster-name')
  cluster_location = metadata.get('cluster-location')

  if not cluster_name:
    raise exceptions.Error('Could not determine cluster name from instance.')
  if not cluster_location:
    raise exceptions.Error(
        'Could not determine cluster location from instance.')

  # Trim http prefix.
  container_endpoint = core_apis.GetEffectiveApiEndpoint(
      'container', 'v1').replace('https://', '', 1).replace('http://', '', 1)
  if container_endpoint.endswith('/'):
    container_endpoint = container_endpoint[:-1]
  return '//{}/projects/{}/locations/{}/clusters/{}'.format(
      container_endpoint, project_id, cluster_location, cluster_name)


def GetEffectiveResourceEndpoint(project_id, cluster_location, cluster_name):
  # where container_endpoint looks like
  # https://container.googleapis.com/v1/projects/{projectID}/locations/{location}/clusters/{clusterName}
  container_endpoint = core_apis.GetEffectiveApiEndpoint(
      'container', 'v1').replace('https://', '', 1).replace('http://', '', 1)
  if container_endpoint.endswith('/'):
    container_endpoint = container_endpoint[:-1]
  return '//{}/projects/{}/locations/{}/clusters/{}'.format(
      container_endpoint, project_id, cluster_location, cluster_name)
