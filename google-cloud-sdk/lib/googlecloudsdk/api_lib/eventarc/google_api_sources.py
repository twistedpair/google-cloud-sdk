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
"""Utilities for Eventarc GoogleAPISources API."""

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


class NoProjectSubscriptionsSpecifiedError(exceptions.Error):
  """Error when no project subscriptions were specified."""


def GetGoogleAPISourceURI(resource):
  google_api_sources = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.googleApiSources'
  )
  return google_api_sources.SelfLink()


class GoogleApiSourceClientV1(base.EventarcClientBase):
  """GoogleApiSource Client for interaction with v1 of Eventarc GoogleApiSources API."""

  def __init__(self):
    super(GoogleApiSourceClientV1, self).__init__(
        common.API_NAME, common.API_VERSION_1, 'Google API source'
    )

    # Eventarc Client
    client = apis.GetClientInstance(common.API_NAME, common.API_VERSION_1)

    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_googleApiSources

  def Create(
      self, google_api_source_ref, google_api_source_message, dry_run=False
  ):
    """Creates a new GoogleAPISource.

    Args:
      google_api_source_ref: Resource, the GoogleAPISource to create.
      google_api_source_message: GoogleAPISource, the googleApiSource message
        that holds googleApiSource's name, destination message bus, logging
        config, crypto key name, etc.
      dry_run: If set, the changes will not be committed, only validated

    Returns:
      A long-running operation for create.
    """
    create_req = (
        self._messages.EventarcProjectsLocationsGoogleApiSourcesCreateRequest(
            parent=google_api_source_ref.Parent().RelativeName(),
            googleApiSource=google_api_source_message,
            googleApiSourceId=google_api_source_ref.Name(),
            validateOnly=dry_run,
        )
    )
    return self._service.Create(create_req)

  def Get(self, google_api_source_ref):
    """Gets the requested GoogleApiSource.

    Args:
      google_api_source_ref: Resource, the GoogleApiSource to get.

    Returns:
      The GoogleApiSource message.
    """
    get_req = (
        self._messages.EventarcProjectsLocationsGoogleApiSourcesGetRequest(
            name=google_api_source_ref.RelativeName()
        )
    )
    return self._service.Get(get_req)

  def List(self, location_ref, limit, page_size):
    """List available googleApiSources in location.

    Args:
      location_ref: Resource, the location to list GoogleApiSources in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of GoogleApiSources in the location.
    """
    list_req = (
        self._messages.EventarcProjectsLocationsGoogleApiSourcesListRequest(
            parent=location_ref.RelativeName(), pageSize=page_size
        )
    )
    return list_pager.YieldFromList(
        service=self._service,
        request=list_req,
        field='googleApiSources',
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize',
    )

  def Patch(
      self, google_api_source_ref, google_api_source_message, update_mask
  ):
    """Updates the specified GoogleApiSource.

    Args:
      google_api_source_ref: Resource, the GoogleApiSource to update.
      google_api_source_message: GoogleApiSource, the googleApiSource message
        that holds googleApiSource's name, destination message bus, logging
        config, crypto key name, etc.
      update_mask: str, a comma-separated list of GoogleApiSource fields to
        update.

    Returns:
      A long-running operation for update.
    """
    patch_req = (
        self._messages.EventarcProjectsLocationsGoogleApiSourcesPatchRequest(
            name=google_api_source_ref.RelativeName(),
            googleApiSource=google_api_source_message,
            updateMask=update_mask,
        )
    )
    return self._service.Patch(patch_req)

  def Delete(self, google_api_source_ref):
    """Deletes the specified GoogleApiSource.

    Args:
      google_api_source_ref: Resource, the GoogleApiSource to delete.

    Returns:
      A long-running operation for delete.
    """
    delete_req = (
        self._messages.EventarcProjectsLocationsGoogleApiSourcesDeleteRequest(
            name=google_api_source_ref.RelativeName()
        )
    )
    return self._service.Delete(delete_req)

  def BuildGoogleApiSource(
      self,
      google_api_source_ref,
      destination_ref,
      logging_config,
      crypto_key_name,
      labels,
      organization_subscription,
      project_subscriptions,
  ):
    logging_config_enum = None
    if logging_config is not None:
      logging_config_enum = self._messages.LoggingConfig(
          logSeverity=self._messages.LoggingConfig.LogSeverityValueValuesEnum(
              logging_config
          ),
      )
    google_api_source = self._messages.GoogleApiSource(
        name=google_api_source_ref.RelativeName(),
        destination=destination_ref.RelativeName()
        if destination_ref is not None
        else '',
        loggingConfig=logging_config_enum,
        cryptoKeyName=crypto_key_name,
        labels=labels,
    )
    if organization_subscription is not None:
      if organization_subscription:
        google_api_source.organizationSubscription = (
            self._messages.OrganizationSubscription(
                enabled=True,
            )
        )
      else:
        google_api_source.organizationSubscription = (
            self._messages.OrganizationSubscription(
                enabled=False,
            )
        )
    elif project_subscriptions:
      google_api_source.projectSubscriptions = (
          self._BuildProjectSubscriptionsList(project_subscriptions)
      )
    return google_api_source

  def BuildUpdateMask(
      self,
      destination,
      logging_config,
      crypto_key,
      clear_crypto_key,
      labels,
      organization_subscription,
      project_subscriptions,
      clear_project_subscriptions,
  ):
    """Builds an update mask for updating a GoogleApiSource.

    Args:
      destination: bool, whether to update the destination.
      logging_config: bool, whether to update the logging config.
      crypto_key: bool, whether to update the crypto key.
      clear_crypto_key: bool, whether to clear the crypto key.
      labels: bool, whether to update the labels.
      organization_subscription: bool, whether to update the organization
        subscription.
      project_subscriptions: bool, whether to update the project subscriptions.
      clear_project_subscriptions: bool, whether to clear the project
        subscriptions.

    Returns:
      The update mask as a string.


    Raises:
      NoFieldsSpecifiedError: No fields are being updated.
    """
    update_mask = []
    if destination:
      update_mask.append('destination')
    if logging_config:
      update_mask.append('loggingConfig')
    if crypto_key or clear_crypto_key:
      update_mask.append('cryptoKeyName')
    if labels:
      update_mask.append('labels')
    if organization_subscription:
      update_mask.append('organizationSubscription')
    if project_subscriptions or clear_project_subscriptions:
      update_mask.append('projectSubscriptions')

    if not update_mask:
      raise NoFieldsSpecifiedError('Must specify at least one field to update.')
    return ','.join(update_mask)

  def LabelsValueClass(self):
    """Returns the labels value class."""
    return self._messages.GoogleApiSource.LabelsValue

  def _BuildProjectSubscriptionsList(self, project_subscriptions):
    if not project_subscriptions:
      raise NoProjectSubscriptionsSpecifiedError(
          'Must specify at least one project number or project ID in the'
          ' project subscriptions.'
      )
    return self._messages.ProjectSubscriptions(list=list(project_subscriptions))

  @property
  def _resource_label_plural(self):
    return 'google-api-sources'
