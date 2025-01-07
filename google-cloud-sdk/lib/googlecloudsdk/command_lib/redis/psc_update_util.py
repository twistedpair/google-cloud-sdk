# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""PSC Connection utilities for `gcloud redis clusters`."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.redis import util


class Error(Exception):
  """Exceptions for this module."""


class InvalidInputError(Error):
  """Error for parsing cluster endpoint input."""


def _GetCluster(cluster_ref, cluster_name):
  client = util.GetClientForResource(cluster_ref)
  messages = util.GetMessagesForResource(cluster_ref)
  return client.projects_locations_clusters.Get(
      messages.RedisProjectsLocationsClustersGetRequest(name=cluster_name)
  )


def _ValidateConnectionLength(cluster_endpoint):
  if len(cluster_endpoint.connections) != 2:
    raise InvalidInputError(
        'Each cluster endpoint should have two connections in a pair')


def UpdateClusterEndpoints(cluster_ref, args, patch_request):
  """Hook to update cluster endpoint for a redis cluster."""
  cluster = _GetCluster(cluster_ref, patch_request.name)
  all_cluster_endpoints = cluster.clusterEndpoints

  for cluster_endpoint in args.cluster_endpoint:
    _ValidateConnectionLength(cluster_endpoint)
    all_cluster_endpoints.append(cluster_endpoint)

  patch_request.cluster.clusterEndpoints = all_cluster_endpoints
  patch_request.updateMask = 'cluster_endpoints'
  return patch_request


def _ExtractAllPSCIDs(endpoint):
  return set(
      connection.pscConnection.pscConnectionId
      for connection in endpoint.connections
      if connection.pscConnection is not None
  )


def _IsInToBeRemovedList(endpoint, to_be_removed_list):
  existing_ids = _ExtractAllPSCIDs(endpoint)
  return any(
      _ExtractAllPSCIDs(to_be_removed) == existing_ids
      for to_be_removed in to_be_removed_list
  )


def RemoveClusterEndpoints(cluster_ref, args, patch_request):
  """Hook to remove a cluster endpoint from a redis cluster."""
  cluster = _GetCluster(cluster_ref, patch_request.name)
  all_cluster_endpoints = cluster.clusterEndpoints

  for cluster_endpoint in args.cluster_endpoint:
    _ValidateConnectionLength(cluster_endpoint)

  new_cluster_endpoints = []
  for existing_endpoint in all_cluster_endpoints:
    if not _IsInToBeRemovedList(existing_endpoint, args.cluster_endpoint):
      new_cluster_endpoints.append(existing_endpoint)

  patch_request.cluster.clusterEndpoints = new_cluster_endpoints
  patch_request.updateMask = 'cluster_endpoints'
  return patch_request

