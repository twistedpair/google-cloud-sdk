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
"""Utilities for node pool resources in Anthos standalone clusters on bare metal."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.protorpclite import messages as protorpc_message
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.container.gkeonprem import client
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.generated_clients.apis.gkeonprem.v1 import gkeonprem_v1_messages as messages_module


class StandaloneNodePoolsClient(client.ClientBase):
  """Client for node pools in Anthos clusters on bare metal standalone API."""

  def __init__(self, **kwargs):
    super(StandaloneNodePoolsClient, self).__init__(**kwargs)
    self._service = (
        self._client.projects_locations_bareMetalStandaloneClusters_bareMetalStandaloneNodePools
    )

  def List(
      self,
      location_ref: protorpc_message.Message,
      limit=None,
      page_size=None,
  ) -> protorpc_message.Message:
    """Lists Node Pools in the Anthos clusters on bare metal standalone API."""
    list_req = messages_module.GkeonpremProjectsLocationsBareMetalStandaloneClustersBareMetalStandaloneNodePoolsListRequest(
        parent=location_ref.RelativeName()
    )

    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='bareMetalStandaloneNodePools',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def Describe(self, resource_ref):
    """Gets a GKE On-Prem Bare Metal API standalone node pool resource."""
    req = messages_module.GkeonpremProjectsLocationsBareMetalStandaloneClustersBareMetalStandaloneNodePoolsGetRequest(
        name=resource_ref.RelativeName()
    )

    return self._service.Get(req)

  def Enroll(
      self, args: parser_extensions.Namespace
  ) -> protorpc_message.Message:
    """Enrolls an Anthos On-Prem Bare Metal API standalone node pool resource.

    Args:
      args: parser_extensions.Namespace, known args specified on the command
        line.

    Returns:
      (Operation) The response message.
    """
    req = messages_module.GkeonpremProjectsLocationsBareMetalStandaloneClustersBareMetalStandaloneNodePoolsEnrollRequest(
        enrollBareMetalStandaloneNodePoolRequest=messages_module.EnrollBareMetalStandaloneNodePoolRequest(
            bareMetalStandaloneNodePoolId=self._standalone_node_pool_id(args),
            validateOnly=self.GetFlag(args, 'validate_only'),
        ),
        parent=self._standalone_node_pool_parent(args),
    )

    return self._service.Enroll(req)

  def Unenroll(
      self, args: parser_extensions.Namespace
  ) -> protorpc_message.Message:
    """Unenrolls an Anthos On-Prem bare metal API standalone node pool resource.

    Args:
      args: parser_extensions.Namespace, known args specified on the command
        line.

    Returns:
      (Operation) The response message.
    """
    kwargs = {
        'allowMissing': self.GetFlag(args, 'allow_missing'),
        'name': self._standalone_node_pool_name(args),
        'validateOnly': self.GetFlag(args, 'validate_only'),
    }
    req = messages_module.GkeonpremProjectsLocationsBareMetalStandaloneClustersBareMetalStandaloneNodePoolsUnenrollRequest(
        **kwargs
    )
    return self._service.Unenroll(req)
