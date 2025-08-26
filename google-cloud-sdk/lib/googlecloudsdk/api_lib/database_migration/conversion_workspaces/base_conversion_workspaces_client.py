# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Database Migration Service conversion workspaces Base Client."""

import abc
from typing import Iterable, Optional, TYPE_CHECKING

from googlecloudsdk.api_lib.database_migration import api_util
from googlecloudsdk.calliope import base
from googlecloudsdk.generated_clients.apis.datamigration.v1 import datamigration_v1_client as client

# pylint: disable=g-bad-import-order
if TYPE_CHECKING:
  from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_client  # pylint: disable=g-import-not-at-top


class BaseConversionWorkspacesClient(abc.ABC):
  """Base Client for Conversion Workspaces APIs.

  This class is the base class for the conversion workspaces clients and
  provides the common services used by the clients in order to send API
  requests.

  Each client inheriting from this class handles a specific part of the API, and
  might need to call other clients in order to complete its
  functionality. Accessing other clients is done through the parent_client
  property.

  Attributes:
    release_track: The release track of the client, controlling the API version
      to use.
    parent_client: The parent client of the conversion workspaces client.
    client: The client used to send API requests.
    messages: The messages module used to construct API requests.
  """

  def __init__(
      self,
      release_track: base.ReleaseTrack,
      parent_client: 'conversion_workspaces_client.ConversionWorkspacesClient',
  ):
    """Initializes the instance with an API client based on the release track.

    Args:
      release_track: The release track of the client, controlling the API
        version to use.
      parent_client: The parent client of the conversion workspaces client.
    """

    self.release_track = release_track
    self.parent_client = parent_client

    self.client: client.DatamigrationV1 = api_util.GetClientInstance(
        release_track=release_track
    )
    self.messages = api_util.GetMessagesModule(release_track=release_track)

  @property
  def cw_service(
      self,
  ) -> client.DatamigrationV1.ProjectsLocationsConversionWorkspacesService:
    """Returns the conversion workspaces service."""
    return self.client.projects_locations_conversionWorkspaces

  @property
  def mapping_rules_service(
      self,
  ) -> (
      client.DatamigrationV1.ProjectsLocationsConversionWorkspacesMappingRulesService
  ):
    """Returns the mapping rules service."""
    return self.client.projects_locations_conversionWorkspaces_mappingRules

  @property
  def location_service(
      self,
  ) -> client.DatamigrationV1.ProjectsLocationsService:
    """Returns the location service."""
    return self.client.projects_locations

  def CombineFilters(
      self,
      *filter_exprs: Iterable[Optional[str]],
  ) -> Optional[str]:
    """Combine filter expression with global filter.

    Args:
      *filter_exprs: Filter expressions to combine.

    Returns:
      Combined filter expression (or None if no filter expressions are
      provided).
    """

    filter_exprs = tuple(
        filter(
            lambda filter_expr: filter_expr and filter_expr != '*',
            filter_exprs,
        )
    )

    if not filter_exprs:
      return None
    if len(filter_exprs) == 1:
      return filter_exprs[0]

    return ' AND '.join(
        map(lambda filter_expr: f'({filter_expr})', filter_exprs)
    )
