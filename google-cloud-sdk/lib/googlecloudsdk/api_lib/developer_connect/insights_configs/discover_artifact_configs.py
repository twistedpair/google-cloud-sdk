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
"""Common utility functions for Developer Connect Insights Configs Discover App Hub."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.asset import client_util as asset_client_util
from googlecloudsdk.command_lib.developer_connect import name
from googlecloudsdk.core import log


def QueryCaisForAssets(gke_workload):
  """Queries CAIS for assets associated with the given GKE workload.

  Args:
    gke_workload: A GKE workload.

  Returns:
    The assets that are associated with the GKE workload.
  """
  partial_pod_uri, parent = ConstructPartialPodUriAndGetParent(gke_workload)
  log.status.Print(
      f'Finding artifacts running in {gke_workload.resource_name()}...'
  )
  search_request = (
      asset_client_util.GetMessages().CloudassetSearchAllResourcesRequest(
          scope=parent,
          query=f'name:{partial_pod_uri}',
          assetTypes=['k8s.io/Pod'],
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


def ConstructPartialPodUriAndGetParent(gke_workload):
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


def GetArtifactURIsFromAssets(assets):
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
      prop_dict = {
          p.key: p.value
          for p in versioned_resource.resource.additionalProperties
      }
      if (
          'spec' not in prop_dict
          or not prop_dict['spec'].object_value
          or not prop_dict['spec'].object_value.properties
      ):
        continue

      spec_dict = {
          p.key: p.value for p in prop_dict['spec'].object_value.properties
      }
      if (
          'containers' not in spec_dict
          or not spec_dict['containers'].array_value
          or not spec_dict['containers'].array_value.entries
      ):
        continue

      containers_array = spec_dict['containers'].array_value.entries
      if (
          not containers_array
          or not containers_array[0].object_value
          or not containers_array[0].object_value.properties
      ):
        continue

      container_dict = {
          p.key: p.value
          for p in containers_array[0].object_value.properties
      }
      if (
          'image' in container_dict
          and container_dict['image'].string_value
      ):
        image_value = container_dict['image'].string_value
        artifact_uris.append(image_value)
  return artifact_uris
