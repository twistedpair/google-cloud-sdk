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
"""Spanner instance partition operations API helper."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

_API_NAME = 'spanner'
_API_VERSION = 'v1'


def Await(operation, message):
  """Wait for the specified operation."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  poller = waiter.CloudOperationPoller(
      client.projects_instances_instancePartitions,
      client.projects_instances_instancePartitions_operations,
  )
  ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection='spanner.projects.instances.instancePartitions.operations',
  )
  return waiter.WaitFor(poller, ref, message)


def ListGeneric(instance_partition, instance):
  """List operations on an instance partition with generic LRO API."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  ref = resources.REGISTRY.Parse(
      instance_partition,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancesId': instance,
      },
      collection='spanner.projects.instances.instancePartitions',
  )
  req = msgs.SpannerProjectsInstancesInstancePartitionsOperationsListRequest(
      name=ref.RelativeName() + '/operations'
  )
  return list_pager.YieldFromList(
      client.projects_instances_instancePartitions_operations,
      req,
      field='operations',
      batch_size_attribute='pageSize',
  )


def Cancel(instance_partition, instance, operation):
  """Cancel the specified operation."""
  client = apis.GetClientInstance(_API_NAME, _API_VERSION)
  msgs = apis.GetMessagesModule(_API_NAME, _API_VERSION)
  ref = resources.REGISTRY.Parse(
      operation,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancePartitionsId': instance_partition,
          'instancesId': instance,
      },
      collection='spanner.projects.instances.instancePartitions.operations',
  )
  req = msgs.SpannerProjectsInstancesInstancePartitionsOperationsCancelRequest(
      name=ref.RelativeName()
  )
  return client.projects_instances_instancePartitions_operations.Cancel(req)
