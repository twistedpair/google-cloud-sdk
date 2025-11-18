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
"""Apphub Extended Metadata Schemas API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.apphub import utils as api_lib_utils
from googlecloudsdk.calliope import base


class ExtendedMetadataSchemasClient(object):
  """Client for extended metadata schemas in apphub API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = api_lib_utils.GetClientInstance(release_track)
    self.messages = api_lib_utils.GetMessagesModule(release_track)
    self._schemas_client = (
        self.client.projects_locations_extendedMetadataSchemas
    )

  def Describe(self, schema_ref):
    """Describe an Extended Metadata Schema.

    Args:
      schema_ref: The resource reference to the schema to describe.

    Returns:
      The described schema resource.
    """
    describe_req = (
        self.messages.ApphubProjectsLocationsExtendedMetadataSchemasGetRequest(
            name=schema_ref.RelativeName()
        )
    )
    return self._schemas_client.Get(describe_req)

  def List(self, parent, limit=None, page_size=100):
    """List extended metadata schemas.

    Args:
      parent: The resource reference to the parent location to list for.
      limit: int, The maximum number of records to yield.
      page_size: int, The number of records to fetch in each request.

    Returns:
      A generator of the schemas.
    """
    list_req = (
        self.messages.ApphubProjectsLocationsExtendedMetadataSchemasListRequest(
            parent=parent
        )
    )
    return list_pager.YieldFromList(
        self._schemas_client,
        list_req,
        field='extendedMetadataSchemas',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize',
    )
