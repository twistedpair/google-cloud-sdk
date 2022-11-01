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

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client


class ClustersClient(client.ClientBase):
  """Client for clusters in gkeonprem bare metal API."""

  def __init__(self, **kwargs):
    super(ClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_bareMetalClusters

  def List(self, location_ref, limit=None, page_size=None):
    """Lists Clusters in the GKE On-Prem Bare Metal API."""
    list_req = self._messages.GkeonpremProjectsLocationsBareMetalClustersListRequest(
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
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersGetRequest(
        name=resource_ref.RelativeName())

    return self._service.Get(req)

  def Enroll(self, args):
    """Enrolls a bare metal cluster to Anthos."""
    kwargs = {
        'adminClusterMembership': self._admin_cluster_membership_name(args),
        'bareMetalClusterId': self._user_cluster_id(args),
        'localName': getattr(args, 'local_name', None),
    }
    enroll_bare_metal_cluster_request = self._messages.EnrollBareMetalClusterRequest(
        **kwargs)
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersEnrollRequest(
        parent=self._user_cluster_parent(args),
        enrollBareMetalClusterRequest=enroll_bare_metal_cluster_request,
    )

    return self._service.Enroll(req)

  def QueryVersionConfig(self, args):
    """Query Anthos on bare metal version configuration."""
    kwargs = {
        'createConfig_adminClusterMembership':
            self._admin_cluster_membership_name(args),
        'upgradeConfig_clusterName':
            self._user_cluster_name(args),
        'parent':
            self._location_ref(args).RelativeName(),
    }

    # This is a workaround for the limitation in apitools with nested messages.
    encoding.AddCustomJsonFieldMapping(
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'createConfig_adminClusterMembership',
        'createConfig.adminClusterMembership')
    encoding.AddCustomJsonFieldMapping(
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest,
        'upgradeConfig_clusterName', 'upgradeConfig.clusterName')

    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersQueryVersionConfigRequest(
        **kwargs)
    return self._service.QueryVersionConfig(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'force': getattr(args, 'force', None),
        'allowMissing': getattr(args, 'allow_missing', None),
    }
    req = (
        self._messages
        .GkeonpremProjectsLocationsBareMetalClustersUnenrollRequest(**kwargs))

    return self._service.Unenroll(req)

  def Delete(self, args):
    """Deletes an Anthos cluster on bare metal."""
    kwargs = {
        'name': self._user_cluster_name(args),
        'allowMissing': getattr(args, 'allow_missing', False),
        'validateOnly': getattr(args, 'validate_only', False),
        'force': getattr(args, 'force', False),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalClustersDeleteRequest(
        **kwargs)

    return self._service.Delete(req)
