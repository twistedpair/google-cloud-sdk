# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud Filestore API."""

from __future__ import absolute_import
from __future__ import unicode_literals
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.filestore import filestore_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


class Error(exceptions.Error):
  """Base class for exceptions in this module."""


class InvalidCapacityError(Error):
  """Raised when an invalid capacity value is provided."""


class FilestoreClient(object):
  """Wrapper for working with the file API."""

  def __init__(self):
    self.client = filestore_util.GetClient()
    self.messages = filestore_util.GetMessages()

  def ListInstances(self, location_ref, limit=None):  # pylint: disable=redefined-builtin
    """Make API calls to List active Cloud Filestore instances.

    Args:
      location_ref: The parsed location of the listed Filestore instances.
      limit: The number of Cloud Filestore instances to limit the results to.
        This limit is passed to the server and the server does the limiting.

    Returns:
      Generator that yields the Cloud Filestore instances.
    """
    request = self.messages.FileProjectsLocationsInstancesListRequest(
        parent=location_ref.RelativeName())
    # Check for unreachable locations.
    response = self.client.projects_locations_instances.List(request)
    for location in response.unreachable:
      log.warning('Location {} may be unreachable.'.format(location))
    return list_pager.YieldFromList(
        self.client.projects_locations_instances,
        request,
        field='instances',
        limit=limit,
        batch_size_attribute='pageSize')

  def GetInstance(self, instance_ref):
    """Get Cloud Filestore instance information."""
    request = self.messages.FileProjectsLocationsInstancesGetRequest(
        name=instance_ref.RelativeName())
    return self.client.projects_locations_instances.Get(request)

  def DeleteInstance(self, instance_ref, async_):
    """Delete an existing Cloud Filestore instance."""
    request = self.messages.FileProjectsLocationsInstancesDeleteRequest(
        name=instance_ref.RelativeName())
    delete_op = self.client.projects_locations_instances.Delete(request)
    if async_:
      return delete_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        delete_op.name, collection=filestore_util.OPERATIONS_COLLECTION)
    return self.WaitForOperation(operation_ref)

  def GetOperation(self, operation_ref):
    """Gets description of a long-running operation.

    Args:
      operation_ref: the operation reference.

    Returns:
      messages.GoogleLongrunningOperation, the operation.
    """
    request = self.messages.FileProjectsLocationsOperationsGetRequest(
        name=operation_ref.RelativeName())
    return self.client.projects_locations_operations.Get(request)

  def WaitForOperation(self, operation_ref):
    """Waits on the long-running operation until the done field is True.

    Args:
      operation_ref: the operation reference.

    Raises:
      waiter.OperationError: if the operation contains an error.

    Returns:
      the 'response' field of the Operation.
    """
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.client.projects_locations_operations,
            get_name_func=lambda x: x.RelativeName()), operation_ref,
        'Waiting for [{0}] to finish'.format(operation_ref.Name()))

  def CreateInstance(self, instance_ref, async_, config):
    """Create a Cloud Filestore instance."""
    request = self.messages.FileProjectsLocationsInstancesCreateRequest(
        parent=instance_ref.Parent().RelativeName(),
        instanceId=instance_ref.Name(),
        instance=config)
    create_op = self.client.projects_locations_instances.Create(request)
    if async_:
      return create_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        create_op.name, collection=filestore_util.OPERATIONS_COLLECTION)
    return self.WaitForOperation(operation_ref)

  def _ValidateFileshare(self, instance_tier, capacity_gb):
    """Validates the value of the fileshare capacity."""
    gb_in_one_tb = 1 << 10
    minimum_values = {
        self.messages.Instance.TierValueValuesEnum.STANDARD: gb_in_one_tb,
        self.messages.Instance.TierValueValuesEnum.PREMIUM: 2.5 * gb_in_one_tb}
    minimum = minimum_values.get(instance_tier, 0)
    if capacity_gb < minimum:
      raise InvalidCapacityError(
          'Fileshare capacity must be greater than or equal to {}TB for a {} '
          'instance.'.format(minimum / gb_in_one_tb, instance_tier))

  def ValidateFileshares(self, instance):
    """Validate the fileshare configs on the instance."""
    for volume in instance.volumes:
      if volume.capacityGb:
        self._ValidateFileshare(instance.tier, volume.capacityGb)

  def GetLocation(self, location_ref):
    request = self.messages.FileProjectsLocationsGetRequest(
        name=location_ref.RelativeName())
    return self.client.projects_locations.Get(request)

  def ListLocations(self, project_ref, limit=None):
    request = self.messages.FileProjectsLocationsListRequest(
        name=project_ref.RelativeName())
    return list_pager.YieldFromList(
        self.client.projects_locations,
        request,
        field='locations',
        limit=limit,
        batch_size_attribute='pageSize')

  def ListOperations(self, operation_ref, limit=None):  # pylint: disable=redefined-builtin
    """Make API calls to List active Cloud Filestore operations.

    Args:
      operation_ref: The parsed location of the listed Filestore instances.
      limit: The number of Cloud Filestore instances to limit the results to.
        This limit is passed to the server and the server does the limiting.

    Returns:
      Generator that yields the Cloud Filestore instances.
    """
    request = self.messages.FileProjectsLocationsOperationsListRequest(
        name=operation_ref.RelativeName())
    return list_pager.YieldFromList(
        self.client.projects_locations_operations,
        request,
        field='operations',
        limit=limit,
        batch_size_attribute='pageSize')
