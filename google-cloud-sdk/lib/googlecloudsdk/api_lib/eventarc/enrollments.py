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
"""Utilities for Eventarc Enrollments API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.eventarc import base
from googlecloudsdk.api_lib.eventarc import common
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


class NoFieldsSpecifiedError(exceptions.Error):
  """Error when no fields were specified for a Patch operation."""


def GetEnrollmentURI(resource):
  enrollments = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.enrollments'
  )
  return enrollments.SelfLink()


class EnrollmentClientV1(base.EventarcClientBase):
  """Enrollment Client for interaction with v1 of Eventarc Enrollments API."""

  def __init__(self):
    super(EnrollmentClientV1, self).__init__(
        common.API_NAME, common.API_VERSION_1, 'enrollment'
    )

    # Eventarc Client
    client = apis.GetClientInstance(common.API_NAME, common.API_VERSION_1)

    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_enrollments

  def Create(self, enrollment_ref, enrollment_message, dry_run=False):
    """Creates a new Enrollment.

    Args:
      enrollment_ref: Resource, the Enrollment to create.
      enrollment_message: Enrollment, the enrollment message that holds
        enrollment's name, cel_match, message_bus, destination, etc.
      dry_run: If set, the changes will not be committed, only validated

    Returns:
      A long-running operation for create.
    """
    create_req = (
        self._messages.EventarcProjectsLocationsEnrollmentsCreateRequest(
            parent=enrollment_ref.Parent().RelativeName(),
            enrollment=enrollment_message,
            enrollmentId=enrollment_ref.Name(),
            validateOnly=dry_run,
        )
    )
    return self._service.Create(create_req)

  def Get(self, enrollment_ref):
    """Gets the requested Enrollment.

    Args:
      enrollment_ref: Resource, the Enrollment to get.

    Returns:
      The Enrollment message.
    """
    get_req = self._messages.EventarcProjectsLocationsEnrollmentsGetRequest(
        name=enrollment_ref.RelativeName()
    )
    return self._service.Get(get_req)

  def List(self, location_ref, limit, page_size):
    """List available enrollments in location.

    Args:
      location_ref: Resource, the location to list Enrollments in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of Enrollments in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsEnrollmentsListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size
    )
    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        field='enrollments',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Patch(self, enrollment_ref, enrollment_message, update_mask):
    """Updates the specified Enrollment.

    Args:
      enrollment_ref: Resource, the Enrollment to update.
      enrollment_message: Enrollment, the enrollment message that holds
        enrollment's name, cel_match, message_bus, destination, etc.
      update_mask: str, a comma-separated list of Enrollment fields to update.

    Returns:
      A long-running operation for update.
    """
    patch_req = self._messages.EventarcProjectsLocationsEnrollmentsPatchRequest(
        name=enrollment_ref.RelativeName(),
        enrollment=enrollment_message,
        updateMask=update_mask,
    )
    return self._service.Patch(patch_req)

  def Delete(self, enrollment_ref):
    """Deletes the specified Enrollment.

    Args:
      enrollment_ref: Resource, the Enrollment to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = (
        self._messages.EventarcProjectsLocationsEnrollmentsDeleteRequest(
            name=enrollment_ref.RelativeName()
        )
    )
    return self._service.Delete(delete_req)

  def BuildEnrollment(
      self, enrollment_ref, cel_match, message_bus_ref, destination_ref, labels
  ):
    return self._messages.Enrollment(
        name=enrollment_ref.RelativeName(),
        celMatch=cel_match,
        messageBus=message_bus_ref.RelativeName()
        if message_bus_ref is not None
        else '',
        destination=destination_ref.RelativeName()
        if destination_ref is not None
        else '',
        labels=labels,
    )

  def BuildUpdateMask(self, cel_match, destination, labels):
    """Builds an update mask for updating a enrollment.

    Args:
      cel_match: bool, whether to update the cel_match.
      destination: bool, whether to update the destination.
      labels: bool, whether to update the labels.

    Returns:
      The update mask as a string.


    Raises:
      NoFieldsSpecifiedError: No fields are being updated.
    """
    update_mask = []
    if cel_match:
      update_mask.append('celMatch')
    if destination:
      update_mask.append('destination')
    if labels:
      update_mask.append('labels')

    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    return ','.join(update_mask)

  def LabelsValueClass(self):
    return self._messages.Enrollment.LabelsValue
