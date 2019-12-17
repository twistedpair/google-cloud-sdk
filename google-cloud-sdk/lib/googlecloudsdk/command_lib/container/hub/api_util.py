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

from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.container.hub import kube_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


def _MembershipClient():
  api_version = core_apis.ResolveVersion('gkehub')
  return core_apis.GetClientInstance('gkehub', api_version)


def _ComputeClient():
  api_version = core_apis.ResolveVersion('compute')
  return core_apis.GetClientInstance('compute', api_version)


def CreateMembership(project, membership_id, description,
                     gke_cluster_self_link):
  """Creates a Membership resource in the GKE Hub API.

  Args:
    project: the project in which to create the membership
    membership_id: the value to use for the membership_id
    description: the value to put in the description field
    gke_cluster_self_link: the selfLink for the cluster if it is a GKE cluster,
      or None if it is not

  Returns:
    the created Membership resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = _MembershipClient()
  messages = client.MESSAGES_MODULE
  request = messages.GkehubProjectsLocationsMembershipsCreateRequest(
      membership=messages.Membership(description=description),
      parent='projects/{}/locations/global'.format(project),
      membershipId=membership_id,
  )
  if gke_cluster_self_link:
    endpoint = messages.MembershipEndpoint(
        gkeCluster=messages.GkeCluster(resourceLink=gke_cluster_self_link))
    request.membership.endpoint = endpoint

  op = client.projects_locations_memberships.Create(request)
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  return waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_memberships,
                                  client.projects_locations_operations),
      op_resource, 'Waiting for membership to be created')


def GetMembership(name):
  """Gets a Membership resource from the GKE Hub API.

  Args:
    name: the full resource name of the membership to get, e.g.,
      projects/foo/locations/global/memberships/name.

  Returns:
    a Membership resource

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = _MembershipClient()
  return client.projects_locations_memberships.Get(
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsGetRequest(
          name=name))


def ProjectForClusterUUID(uuid, projects):
  """Retrieves the project that the cluster UUID has a Membership with.

  Args:
    uuid: the UUID of the cluster.
    projects: sequence of project IDs to consider.

  Returns:
    a project ID.

  Raises:
    apitools.base.py.HttpError: if any request returns an HTTP error
  """

  client = _MembershipClient()
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


def DeleteMembership(name):
  """Deletes a membership from the GKE Hub.

  Args:
    name: the full resource name of the membership to delete, e.g.,
      projects/foo/locations/global/memberships/name.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error
  """

  client = _MembershipClient()
  op = client.projects_locations_memberships.Delete(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsDeleteRequest(name=name))
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  waiter.WaitFor(
      waiter.CloudOperationPollerNoResources(
          client.projects_locations_operations), op_resource,
      'Waiting for membership to be deleted')


def GKEClusterSelfLink(args):
  """Returns the selfLink of a cluster, if it is a GKE cluster.

  There is no straightforward way to obtain this information from the cluster
  API server directly. This method uses metadata on the Kubernetes nodes to
  determine the instance ID and project ID of a GCE VM, whose metadata is used
  to find the location of the cluster and its name.

  Args:
    args: an argparse namespace. All arguments that were provided to the command
      invocation.

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

  kube_client = kube_util.KubernetesClient(args)

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
