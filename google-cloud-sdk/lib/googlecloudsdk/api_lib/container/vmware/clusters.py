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
"""Utilities for gkeonprem API clients for VMware cluster resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis


class ClustersClient(object):
  """Client for clusters in gkeonprem vmware API."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance('gkeonprem', 'v1')
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_vmwareClusters

  def List(self, location_ref, limit=None, page_size=100):
    """Lists Clusters in the GKE On-Prem VMware API."""
    list_req = self.messages.GkeonpremProjectsLocationsVmwareClustersListRequest(
        parent=location_ref.RelativeName())
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='vmwareClusters',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')

  def Describe(self, resource_ref):
    """Gets a gkeonprem API cluster resource."""
    req = self.messages.GkeonpremProjectsLocationsVmwareClustersGetRequest(
        name=resource_ref.RelativeName())
    return self._service.Get(req)

  def Enroll(self, admin_cluster_membership_ref, resource_ref, local_name=None):
    """Enrolls a VMware cluster to Anthos."""
    enroll_vmware_cluster_request = self.messages.EnrollVmwareClusterRequest(
        adminClusterMembership=admin_cluster_membership_ref.RelativeName(),
        vmwareClusterId=resource_ref.Name(),
        localName=local_name,
    )
    req = self.messages.GkeonpremProjectsLocationsVmwareClustersEnrollRequest(
        parent=resource_ref.Parent().RelativeName(),
        enrollVmwareClusterRequest=enroll_vmware_cluster_request,
    )
    return self._service.Enroll(req)

  def Unenroll(self, resource_ref, force=False):
    """Unenrolls an Anthos cluster on VMware."""
    req = self.messages.GkeonpremProjectsLocationsVmwareClustersUnenrollRequest(
        name=resource_ref.RelativeName(),
        force=force,
    )
    return self._service.Unenroll(req)

  def Delete(self,
             resource_ref,
             allow_missing=False,
             validate_only=False,
             force=False):
    """Deletes an Anthos cluster on VMware."""
    req = self.messages.GkeonpremProjectsLocationsVmwareClustersDeleteRequest(
        name=resource_ref.RelativeName(),
        allowMissing=allow_missing,
        validateOnly=validate_only,
        force=force,
    )
    return self._service.Delete(req)
