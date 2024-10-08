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

from googlecloudsdk.api_lib.eventarc import base
from googlecloudsdk.api_lib.eventarc import common
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources


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

  def BuildGoogleApiSource(
      self,
      google_api_source_ref,
      destination_ref,
      logging_config,
      crypto_key_name,
  ):
    logging_config_enum = None
    if logging_config is not None:
      logging_config_enum = self._messages.LoggingConfig(
          logSeverity=self._messages.LoggingConfig.LogSeverityValueValuesEnum(
              logging_config
          ),
      )
    return self._messages.GoogleApiSource(
        name=google_api_source_ref.RelativeName(),
        destination=destination_ref.RelativeName(),
        loggingConfig=logging_config_enum,
        cryptoKeyName=crypto_key_name,
    )

  @property
  def _resource_label_plural(self):
    return 'google-api-sources'
