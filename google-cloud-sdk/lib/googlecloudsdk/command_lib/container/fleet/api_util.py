# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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

from googlecloudsdk.api_lib.container.fleet import gkehub_api_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


def _ComputeClient():
  api_version = core_apis.ResolveVersion('compute')
  return core_apis.GetClientInstance('compute', api_version)


def _StorageClient():
  return core_apis.GetClientInstance('storage', 'v1')


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


def UpdateMembership(name,
                     membership,
                     update_mask,
                     release_track,
                     external_id=None,
                     issuer_url=None,
                     oidc_jwks=None,
                     api_server_version=None):
  """UpdateMembership updates membership resource in the GKE Hub API.

  Args:
    name: The full resource name of the membership to update, e.g.
    projects/foo/locations/global/memberships/name.
    membership: Membership resource that needs to be updated.
    update_mask: Field names of membership resource to be updated.
    release_track: The release_track used in the gcloud command.
    external_id: the unique id associated with the cluster,
      or None if it is not available.
    issuer_url: The discovery URL for the cluster's service account token
      issuer.
    oidc_jwks: The JSON Web Key Set string containing public keys for validating
      service account tokens. Set to None if the issuer_url is
      publicly-reachable. Still requires issuer_url to be set.
    api_server_version: api_server_version of the cluster

  Returns:
    The updated Membership resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  messages = client.MESSAGES_MODULE
  request = messages.GkehubProjectsLocationsMembershipsPatchRequest(
      membership=membership, name=name, updateMask=update_mask)

  if issuer_url:
    request.membership.authority = messages.Authority(issuer=issuer_url)
    if oidc_jwks:
      request.membership.authority.oidcJwks = oidc_jwks.encode('utf-8')
    else:
      # If oidc_jwks is None, unset membership.oidc_jwks, and let the API
      # determine when that's an error, not the client, to avoid problems
      # like cl/339713504 fixed (see unsetting membership.authority, below).
      request.membership.authority.oidcJwks = None
  else:  # if issuer_url is None, unset membership.authority to disable WI.
    request.membership.authority = None

  # checking different cases in the request to make sure not to override
  # values when updating
  if api_server_version:
    resource_options = messages.ResourceOptions(k8sVersion=api_server_version)
    kubernetes_resource = messages.KubernetesResource(
        resourceOptions=resource_options)
    endpoint = messages.MembershipEndpoint(
        kubernetesResource=kubernetes_resource)
    if request.membership.endpoint:
      if request.membership.endpoint.kubernetesResource:
        if request.membership.endpoint.kubernetesResource.resourceOptions:
          request.membership.endpoint.kubernetesResource.resourceOptions.k8sVersion = api_server_version
        else:
          request.membership.endpoint.kubernetesResource.resourceOptions = resource_options
      else:
        request.membership.endpoint.kubernetesResource = kubernetes_resource
    else:
      request.membership.endpoint = endpoint

  if external_id:
    request.membership.externalId = external_id
  op = client.projects_locations_memberships.Patch(request)
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  return waiter.WaitFor(
      waiter.CloudOperationPoller(client.projects_locations_memberships,
                                  client.projects_locations_operations),
      op_resource, 'Waiting for membership to be updated')


def CreateMembership(project,
                     membership_id,
                     description,
                     location=None,
                     gke_cluster_self_link=None,
                     external_id=None,
                     release_track=None,
                     issuer_url=None,
                     oidc_jwks=None,
                     api_server_version=None):
  """Creates a Membership resource in the GKE Hub API.

  Args:
    project: the project in which to create the membership
    membership_id: the value to use for the membership_id
    description: the value to put in the description field
    location: the location for the membership
    gke_cluster_self_link: the selfLink for the cluster if it is a GKE cluster,
      or None if it is not
    external_id: the unique id associated with the cluster,
      or None if it is not available.
    release_track: the release_track used in the gcloud command,
      or None if it is not available.
    issuer_url: the discovery URL for the cluster's service account token
      issuer. Set to None to skip enabling Workload Identity.
    oidc_jwks: the JSON Web Key Set containing public keys for validating
      service account tokens. Set to None if the issuer_url is
      publicly-routable. Still requires issuer_url to be set.
    api_server_version: api server version of the cluster for CRD

  Returns:
    the created Membership resource.

  Raises:
    - apitools.base.py.HttpError: if the request returns an HTTP error
    - exceptions raised by waiter.WaitFor()
  """
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  messages = client.MESSAGES_MODULE
  parent_ref = ParentRef(project, location)

  request = messages.GkehubProjectsLocationsMembershipsCreateRequest(
      membership=messages.Membership(description=description),
      parent=parent_ref,
      membershipId=membership_id,
  )
  # TODO(b/216318697): Use k8s_version for both GKE/Non-GKE
  if gke_cluster_self_link:
    endpoint = messages.MembershipEndpoint(
        gkeCluster=messages.GkeCluster(resourceLink=gke_cluster_self_link))
    request.membership.endpoint = endpoint
  else:
    # set the request endpoint param here with k8s_version set
    if api_server_version:
      resource_options = messages.ResourceOptions(k8sVersion=api_server_version)
      kubernetes_resource = messages.KubernetesResource(
          resourceOptions=resource_options)
      endpoint = messages.MembershipEndpoint(
          kubernetesResource=kubernetes_resource)
      request.membership.endpoint = endpoint
  if external_id:
    request.membership.externalId = external_id
  if issuer_url:
    request.membership.authority = messages.Authority(issuer=issuer_url)
    if oidc_jwks:
      request.membership.authority.oidcJwks = oidc_jwks.encode('utf-8')

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
          client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsListRequest(
              parent=parent))
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
      client.MESSAGES_MODULE.GkehubProjectsLocationsMembershipsDeleteRequest(
          name=name))
  op_resource = resources.REGISTRY.ParseRelativeName(
      op.name, collection='gkehub.projects.locations.operations')
  waiter.WaitFor(
      waiter.CloudOperationPollerNoResources(
          client.projects_locations_operations), op_resource,
      'Waiting for membership to be deleted')


def ValidateExclusivity(cr_manifest,
                        parent_ref,
                        intended_membership,
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
  release_track = base.ReleaseTrack.BETA
  client = gkehub_api_util.GetApiClientForTrack(release_track)
  return client.projects_locations_memberships.ValidateExclusivity(
      client.MESSAGES_MODULE
      .GkehubProjectsLocationsMembershipsValidateExclusivityRequest(
          parent=parent_ref,
          crManifest=cr_manifest,
          intendedMembership=intended_membership))


def GenerateExclusivityManifest(crd_manifest,
                                cr_manifest,
                                membership_ref,
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
          name=membership_ref, crdManifest=crd_manifest,
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
    request.imagePullSecretContent = image_pull_secret_content.encode('utf-8')
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


def GetGKEURIAndResourceName(project_id, cluster_location, cluster_name):
  """Constructs GKE URI and resource name from args and container endpoint.

  Args:
    project_id: the project identifier to which the cluster to be registered
      belongs.
    cluster_location: zone or region of the cluster.
    cluster_name: name of the cluster to be registered.

  Returns:
    GKE resource link: full resource name as per go/resource-names
      (including preceding slashes).
    GKE cluster URI: URI string looks in the format of
    https://container.googleapis.com/v1/
      projects/{projectID}/locations/{location}/clusters/{clusterName}.
  """
  container_endpoint = core_apis.GetEffectiveApiEndpoint('container', 'v1')
  if container_endpoint.endswith('/'):
    container_endpoint = container_endpoint[:-1]
  gke_resource_link = '//{}/projects/{}/locations/{}/clusters/{}'.format(
      container_endpoint.replace('https://', '', 1).replace('http://', '', 1),
      project_id, cluster_location, cluster_name)
  gke_cluster_uri = '{}/v1/projects/{}/locations/{}/clusters/{}'.format(
      container_endpoint, project_id, cluster_location, cluster_name)
  return gke_resource_link, gke_cluster_uri
