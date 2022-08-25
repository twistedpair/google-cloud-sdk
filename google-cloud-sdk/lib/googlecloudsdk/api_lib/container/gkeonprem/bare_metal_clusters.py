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
"""Utilities for gkeonprem API clients for Bare Metal cluster resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client


# pylint: disable=protected-access
class ClustersClient(object):
  """Client for clusters in gkeonprem bare metal API."""

  def __init__(self):
    self._base_client = client.ClientBase()
    self._service = self._base_client._client.projects_locations_bareMetalClusters

  def List(self, location_ref, limit=None, page_size=None):
    """Lists Clusters in the GKE On-Prem Bare Metal API."""
    list_req = self._base_client._messages.GkeonpremProjectsLocationsBareMetalClustersListRequest(
        parent=location_ref.RelativeName())

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalClusters',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal API cluster resource."""
    req = self._base_client._messages.GkeonpremProjectsLocationsBareMetalClustersGetRequest(
        name=resource_ref.RelativeName())

    return self._service.Get(req)

  def Enroll(self, args):
    """Enrolls a bare metal cluster to Anthos."""
    kwargs = {
        'adminClusterMembership':
            self._base_client._admin_cluster_membership_name(args),
        'bareMetalClusterId':
            self._base_client._user_cluster_id(args),
        'localName':
            getattr(args, 'local_name', None),
    }
    enroll_bare_metal_cluster_request = self._base_client._messages.EnrollBareMetalClusterRequest(
        **kwargs)
    req = self._base_client._messages.GkeonpremProjectsLocationsBareMetalClustersEnrollRequest(
        parent=self._base_client._user_cluster_parent(args),
        enrollBareMetalClusterRequest=enroll_bare_metal_cluster_request,
    )

    return self._service.Enroll(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._base_client._user_cluster_name(args),
        'force': getattr(args, 'force', None),
        'allowMissing': getattr(args, 'allow_missing', None),
    }
    req = (
        self._base_client._messages
        .GkeonpremProjectsLocationsBareMetalClustersUnenrollRequest(**kwargs))
    return self._service.Unenroll(req)
