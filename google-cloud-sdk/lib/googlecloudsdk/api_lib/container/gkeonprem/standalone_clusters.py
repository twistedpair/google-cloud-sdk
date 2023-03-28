# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utilities for gkeonprem API clients for Bare Metal Standalone cluster resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client


class StandaloneClustersClient(client.ClientBase):
  """Client for clusters in gkeonprem bare metal API."""

  def __init__(self, **kwargs):
    super(StandaloneClustersClient, self).__init__(**kwargs)
    self._service = self._client.projects_locations_bareMetalStandaloneClusters

  def List(self, location_ref, limit=None, page_size=None):
    """Lists Clusters in the GKE On-Prem Bare Metal Standalone API."""
    list_req = self._messages.GkeonpremProjectsLocationsBareMetalStandaloneClustersListRequest(
        parent=location_ref.RelativeName())

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalStandaloneClusters',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal Standalone API cluster resource."""
    req = self._messages.GkeonpremProjectsLocationsBareMetalStandaloneClustersGetRequest(
        name=resource_ref.RelativeName())

    return self._service.Get(req)

  def Enroll(self, args):
    """Enrolls an existing bare metal standalone cluster to the GKE on-prem API within a given project and location."""
    kwargs = {
        'membership': self._standalone_cluster_membership_name(args),
        'bareMetalStandaloneClusterId': self._standalone_cluster_id(args),
        'localName': getattr(args, 'local_name', None),
    }
    req = (
        self._messages.GkeonpremProjectsLocationsBareMetalStandaloneClustersEnrollRequest(
            parent=self._standalone_cluster_parent(args),
            enrollBareMetalStandaloneClusterRequest=
            self._messages.EnrollBareMetalStandaloneClusterRequest(**kwargs),
        )
    )

    return self._service.Enroll(req)

