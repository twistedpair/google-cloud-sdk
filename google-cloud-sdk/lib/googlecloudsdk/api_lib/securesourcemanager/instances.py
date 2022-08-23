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
"""The Secure Source Manager instances client module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources

VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1'}


def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('securesourcemanager', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('securesourcemanager', api_version)


class InstancesClient(object):
  """Client for Secure Source Manager instances."""

  def __init__(self):
    self.client = GetClientInstance(base.ReleaseTrack.ALPHA)
    self.messages = GetMessagesModule(base.ReleaseTrack.ALPHA)
    self._service = self.client.projects_locations_instances
    self._resource_parser = resources.Registry()
    self._resource_parser.RegisterApiByName('securesourcemanager', 'v1')

  def Create(self, instance_ref, admin_account):
    """Create a new Secure Source Manager instance.

    Args:
      instance_ref: a resource reference to
        securesourcemanager.projects.locations.instances.
      admin_account: the first user when the instance is created,
        default to current account.

    Returns:
      Created instance.
    """
    instance = self.messages.Instance(adminAccount=admin_account)
    create_req = self.messages.SecuresourcemanagerProjectsLocationsInstancesCreateRequest(
        instance=instance,
        instanceId=instance_ref.instancesId,
        parent=instance_ref.Parent().RelativeName())
    return self._service.Create(create_req)

  def Delete(self, instance_ref):
    """Delete a Secure Source Manager instance.

    Args:
      instance_ref: a resource reference to
        securesourcemanager.projects.locations.instances.

    Returns:
      None
    """
    delete_req = self.messages.SecuresourcemanagerProjectsLocationsInstancesDeleteRequest(
        name=instance_ref.RelativeName())
    return self._service.Delete(delete_req)

  def GetOperationRef(self, operation):
    """Converts an operation to a resource that can be used with `waiter.WaitFor`."""
    return self._resource_parser.ParseRelativeName(
        operation.name, 'securesourcemanager.projects.locations.operations')

  def WaitForOperation(self,
                       operation_ref,
                       message,
                       has_result=True,
                       max_wait=datetime.timedelta(seconds=600)):
    """Waits for a Secure Source Manager operation to complete.

      Polls the Secure Source Manager Operation service until the operation
      completes, fails, or max_wait_seconds elapses.

    Args:
      operation_ref: a resource reference created by GetOperationRef describing
        the operation.
      message: a message to display to the user while they wait.
      has_result: If True, the function will return the target of the
        operation (i.e. the Secure Source Manager instance) when it completes.
        If False, nothing will be returned (useful for Delete operations).
      max_wait: The time to wait for the operation to complete before
        returning.

    Returns:
      A Secure Source Manager resource or None
    """
    if has_result:
      poller = waiter.CloudOperationPoller(
          self.client.projects_locations_instances,
          self.client.projects_locations_operations)
    else:
      poller = waiter.CloudOperationPollerNoResources(
          self.client.projects_locations_operations)

    return waiter.WaitFor(
        poller, operation_ref, message, max_wait_ms=max_wait.seconds * 1000)
