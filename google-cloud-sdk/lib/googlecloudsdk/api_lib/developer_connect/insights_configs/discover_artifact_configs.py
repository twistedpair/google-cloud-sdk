# -*- coding: utf-8 -*- #
#
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Common utility functions for Developer Connect Insights Configs Discover App Hub and Discover Projects."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.asset import client_util as asset_client_util
from googlecloudsdk.command_lib.developer_connect import name
from googlecloudsdk.core import log

_CLOUD_RUN_REVISION_ASSET_TYPE = 'run.googleapis.com/Revision'
_GKE_POD_ASSET_TYPE = 'k8s.io/Pod'


def _get_property_values(properties, keys):
  """Extracts values for given keys from a list of properties.

  Args:
    properties: A list of property objects, each with 'key' and 'value'.
    keys: A list of keys to look for.

  Returns:
    A tuple of values corresponding to the keys. If a key is not found,
    the corresponding value in the tuple will be None.
  """
  prop_dict = {p.key: p.value for p in properties}
  return tuple(prop_dict.get(key) for key in keys)


def query_cais_for_gke_assets(gke_workload):
  """Queries CAIS for assets associated with the given GKE workload.

  Args:
    gke_workload: A GKE workload.

  Returns:
    The assets that are associated with the GKE workload.
  """
  partial_pod_uri, parent = construct_partial_pod_uri_and_get_parent(
      gke_workload
  )
  log.status.Print(
      f'Finding artifacts running in {gke_workload.resource_name()}...'
  )
  search_request = (
      asset_client_util.GetMessages().CloudassetSearchAllResourcesRequest(
          scope=parent,
          query=f'name:{partial_pod_uri}',
          assetTypes=[_GKE_POD_ASSET_TYPE],
          readMask='name,versioned_resources,create_time,state',
      )
  )
  assets = list_pager.YieldFromList(
      asset_client_util.GetClient().v1,
      search_request,
      method='SearchAllResources',
      field='results',
      batch_size_attribute='pageSize',
  )
  return list(assets)


def query_cais_for_gke_assets_in_project(project):
  """Queries CAIS for GKE assets in a given GCP project.

  Args:
    project: A GCP Project.

  Returns:
    The GKE assets that are associated with the GCP Project.
  """
  # DCI does not track system namespaces.
  system_deployment_namespaces = [
      'config-management-system',
      'gke-gmp-system',
      'gke-managed-checkpointing',
      'gke-managed-cim',
      'gke-managed-lustrecsi',
      'gke-managed-parallelstorecsi',
      'gke-managed-system',
      'gke-managed-volumepopulator',
      'gke-system',
      'gmp-system',
      'istio-system',
      'knative-serving',
      'kube-system',
  ]

  # Dynamically build the exclusion query string.
  # Result matches: "NOT name:/namespaces/ns1/ NOT name:/namespaces/ns2/ ..."
  namespace_exclusions = [
      f'NOT name:/namespaces/{ns}/' for ns in system_deployment_namespaces
  ]
  query_string = ' '.join(namespace_exclusions)

  log.status.Print(f'Finding GKE artifacts running in {project}...')
  search_request = (
      asset_client_util.GetMessages().CloudassetSearchAllResourcesRequest(
          scope=f'projects/{project}',
          query=query_string,
          assetTypes=[_GKE_POD_ASSET_TYPE],
          readMask='name,versioned_resources,create_time,state',
      )
  )
  assets = list_pager.YieldFromList(
      asset_client_util.GetClient().v1,
      search_request,
      method='SearchAllResources',
      field='results',
      batch_size_attribute='pageSize',
  )
  return list(assets)


def query_cais_for_cloud_run_services(cloud_run_service):
  """Queries CAIS for assets associated with the given Cloud Run service.

  Args:
    cloud_run_service: A Cloud Run service.

  Returns:
    The assets that are associated with the Cloud Run service.
  """
  parent_full_service_resource_name = cloud_run_service.resource_name()
  log.status.Print(
      f'Finding artifacts running in {parent_full_service_resource_name}...'
  )
  search_request = (
      asset_client_util.GetMessages().CloudassetSearchAllResourcesRequest(
          scope=f'projects/{cloud_run_service.project_id}',
          query=f'parentFullResourceName:{parent_full_service_resource_name}',
          assetTypes=[_CLOUD_RUN_REVISION_ASSET_TYPE],
          readMask='name,versioned_resources',
      )
  )
  assets = list_pager.YieldFromList(
      asset_client_util.GetClient().v1,
      search_request,
      method='SearchAllResources',
      field='results',
      batch_size_attribute='pageSize',
  )
  return list(assets)


def query_cais_for_cloud_run_services_in_project(project):
  """Queries CAIS for Cloud Run service assets associated with the given GCP Project.

  Args:
    project: A GCP Project.

  Returns:
    The Cloud Run assets that are associated with the GCP Project.
  """
  log.status.Print(f'Finding Cloud Run artifacts running in {project}...')
  search_request = (
      asset_client_util.GetMessages().CloudassetSearchAllResourcesRequest(
          scope=f'projects/{project}',
          assetTypes=[_CLOUD_RUN_REVISION_ASSET_TYPE],
          readMask='name,versioned_resources',
      )
  )
  assets = list_pager.YieldFromList(
      asset_client_util.GetClient().v1,
      search_request,
      method='SearchAllResources',
      field='results',
      batch_size_attribute='pageSize',
  )
  return list(assets)


def construct_partial_pod_uri_and_get_parent(gke_workload):
  """Constructs a partial pod URI from a GKE workload and returns the parent.

  Args:
    gke_workload: A GKE workload.

  Returns:
    A partial pod URI that can be used to query CAIS for pods.
    A parent that can be used to query CAIS for resources.
  """
  project_info = name.Project(gke_workload.gke_namespace.gke_cluster.project)
  location = gke_workload.gke_namespace.gke_cluster.location_id
  cluster_id = gke_workload.gke_namespace.gke_cluster.cluster_id
  namespace_id = gke_workload.gke_namespace.namespace_id
  deployment_id = gke_workload.deployment_id
  parent = f'projects/{project_info.project_id}'
  partial_pod_uri = (
      f'//container.googleapis.com/projects/{project_info.project_id}/'
      f'locations/{location}/clusters/{cluster_id}/k8s/namespaces/'
      f'{namespace_id}/pods/{deployment_id}'
  )
  return partial_pod_uri, parent


def get_artifact_uris_from_gke_assets(assets):
  """Gets artifact URIs from assets.

  Args:
    assets: A list of assets.

  Returns:
    A list of artifact uris.
  """
  artifact_uris = []
  for asset in assets:
    for versioned_resource in asset.versionedResources:
      if versioned_resource.version != 'v1':
        continue
      (spec_value,) = _get_property_values(
          versioned_resource.resource.additionalProperties, ['spec']
      )
      if (
          not spec_value
          or not spec_value.object_value
          or not spec_value.object_value.properties
      ):
        continue

      (containers_value,) = _get_property_values(
          spec_value.object_value.properties, ['containers']
      )
      if (
          not containers_value
          or not containers_value.array_value
          or not containers_value.array_value.entries
      ):
        continue

      containers_array = containers_value.array_value.entries
      if (
          not containers_array
          or not containers_array[0].object_value
          or not containers_array[0].object_value.properties
      ):
        continue

      (image_value,) = _get_property_values(
          containers_array[0].object_value.properties, ['image']
      )
      if image_value and image_value.string_value:
        artifact_uris.append(image_value.string_value)
  return artifact_uris


def _is_cloud_run_revision_active(status_value):
  """Checks if a Cloud Run revision is active based on its status.

  An 'Active' condition with a 'True' status on a revision means it is
  deployed and serving traffic. We filter for active revisions to ensure
  we are discovering artifacts that are currently deployed and running,
  rather than old or inactive revisions.

  Args:
    status_value: The status property of a Cloud Run revision resource.

  Returns:
    True if the revision is active, False otherwise.
  """
  (conditions_value,) = _get_property_values(
      status_value.object_value.properties, ['conditions']
  )
  conditions = getattr(conditions_value, 'array_value', None)

  if not conditions:
    return False

  for condition_entry in conditions.entries:
    condition_type_value, condition_status_value = _get_property_values(
        condition_entry.object_value.properties, ['type', 'status']
    )

    condition_type = getattr(condition_type_value, 'string_value', None)
    condition_status = getattr(condition_status_value, 'string_value', None)

    if condition_type == 'Active' and condition_status == 'True':
      return True
  return False


def _get_artifact_uris_from_cloud_run_versioned_resource(versioned_resource):
  """Gets image URIs from a Cloud Run versioned resource.

  Args:
    versioned_resource: A Cloud Run versioned resource.

  Returns:
    A list of artifact URIs from the active containers.
  """
  artifact_uris = []
  if versioned_resource.version != 'v1':
    return []

  spec_value, status_value = _get_property_values(
      versioned_resource.resource.additionalProperties, ['spec', 'status']
  )

  if not status_value or not hasattr(status_value, 'object_value'):
    return []

  if not _is_cloud_run_revision_active(status_value):
    return []

  if spec_value and hasattr(spec_value, 'object_value'):
    (containers_value,) = _get_property_values(
        spec_value.object_value.properties, ['containers']
    )
    containers = getattr(containers_value, 'array_value', None)

    if containers:
      for container_entry in containers.entries:
        (image_value,) = _get_property_values(
            container_entry.object_value.properties, ['image']
        )
        image_uri = getattr(image_value, 'string_value', None)
        if image_uri:
          artifact_uris.append(image_uri)
  return artifact_uris


def get_artifact_uris_from_cloud_run_assets(assets):
  """Gets image URIs from Cloud Run assets that are active and v1.

  Args:
    assets: A list of Cloud Run assets.

  Returns:
      A list of artifact URIs from the active containers.
  """
  artifact_uris = []
  for asset in assets:
    for vr in asset.versionedResources:
      artifact_uris.extend(
          _get_artifact_uris_from_cloud_run_versioned_resource(vr)
      )

  return artifact_uris
