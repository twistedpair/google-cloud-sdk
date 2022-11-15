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
"""Utilities for gkeonprem API clients for bare metal admin cluster resources.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.api_lib.container.gkeonprem import update_mask


class AdminClustersClient(client.ClientBase):
  """Client for admin clusters in gkeonprem bare metal API."""

  def __init__(self, **kwargs):
    super(AdminClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_bareMetalAdminClusters

  def Enroll(self, args):
    """Enrolls an admin cluster to Anthos on bare metal."""
    kwargs = {
        'membership': self._admin_cluster_membership_name(args),
        'bareMetalAdminClusterId': self._admin_cluster_id(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalAdminClustersEnrollRequest(
        parent=self._admin_cluster_parent(args),
        enrollBareMetalAdminClusterRequest=self._messages
        .EnrollBareMetalAdminClusterRequest(**kwargs),
    )
    return self._service.Enroll(req)

  def Unenroll(self, args):
    """Unenrolls an Anthos on bare metal admin cluster."""
    kwargs = {
        'name': self._admin_cluster_name(args),
    }
    req = (
        self._messages
        .GkeonpremProjectsLocationsBareMetalAdminClustersUnenrollRequest(
            **kwargs))
    return self._service.Unenroll(req)

  def List(self, args):
    """Lists admin clusters in the GKE On-Prem bare metal API."""
    list_req = (
        self._messages
        .GkeonpremProjectsLocationsBareMetalAdminClustersListRequest(
            parent=self._location_name(args)))

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalAdminClusters',
        batch_size=getattr(args, 'page_size', 100),
        limit=getattr(args, 'limit', None),
        batch_size_attribute='pageSize',
    )

  def Update(self, args):
    """Updates an admin cluster in Anthos on bare metal."""
    kwargs = {
        'name':
            self._admin_cluster_name(args),
        'updateMask':
            update_mask.get_update_mask(
                args,
                update_mask.BARE_METAL_ADMIN_CLUSTER_ARGS_TO_UPDATE_MASKS),
        'bareMetalAdminCluster':
            self._bare_metal_admin_cluster(args),
    }
    req = self._messages.GkeonpremProjectsLocationsBareMetalAdminClustersPatchRequest(
        **kwargs)
    return self._service.Patch(req)

  def _bare_metal_admin_cluster(self, args):
    """Constructs proto message BareMetalAdminCluster."""
    kwargs = {
        'bareMetalVersion': getattr(args, 'version', None),
    }
    if any(kwargs.values()):
      return self._messages.BareMetalAdminCluster(**kwargs)
    return None
