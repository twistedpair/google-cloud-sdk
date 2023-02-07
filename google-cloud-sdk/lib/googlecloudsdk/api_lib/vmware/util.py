# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Cloud vmware API utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import resources

_DEFAULT_API_VERSION = 'v1'


class VmwareClientBase(object):
  """Base class for vwmare API client wrappers."""

  def __init__(self, api_version=_DEFAULT_API_VERSION):
    self._client = apis.GetClientInstance('vmwareengine', api_version)
    self._messages = apis.GetMessagesModule('vmwareengine', api_version)
    self.service = None
    self.operations_service = self.client.projects_locations_operations

  @property
  def client(self):
    return self._client

  @property
  def messages(self):
    return self._messages

  def GetOperationRef(self, operation):
    """Converts an Operation to a Resource that can be used with `waiter.WaitFor`.
    """
    return resources.REGISTRY.ParseRelativeName(
        operation.name, collection='vmwareengine.projects.locations.operations')

  def WaitForOperation(self,
                       operation_ref,
                       message,
                       has_result=True,
                       max_wait=datetime.timedelta(seconds=3600)):
    """Waits for an operation to complete.

    Polls the IDS Operation service until the operation completes, fails, or
    max_wait_seconds elapses.

    Args:
      operation_ref: a Resource created by GetOperationRef describing the
        operation.
      message: the message to display to the user while they wait.
      has_result: if True, the function will return the target of the operation
        when it completes. If False, nothing will be returned (useful for Delete
        operations)
      max_wait: The time to wait for the operation to succeed before returning.

    Returns:
      if has_result = True, an Endpoint entity.
      Otherwise, None.
    """
    if has_result:
      poller = waiter.CloudOperationPoller(self.service,
                                           self.operations_service)
    else:
      poller = waiter.CloudOperationPollerNoResources(self.operations_service)

    return waiter.WaitFor(
        poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000)

  def GetResponse(self, operation):
    poller = waiter.CloudOperationPoller(self.service, self.operations_service)
    return poller.GetResult(operation)


def GetResourceId(resource_name):
  return resource_name.split('/')[-1]


def ConstructNodeParameterConfigMessage(map_class, config_class, nodes_configs):
  properties = []
  for nodes_config in nodes_configs:
    node_type_config = config_class(
        nodeCount=nodes_config['count'],
        customCoreCount=nodes_config.get('custom-core-count', 0))
    prop = map_class.AdditionalProperty(
        key=nodes_config['type'], value=node_type_config)
    properties.append(prop)
  return map_class(additionalProperties=properties)
