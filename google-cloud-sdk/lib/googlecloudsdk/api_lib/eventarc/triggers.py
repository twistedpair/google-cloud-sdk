# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for Eventarc Triggers API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources

_API_NAME = 'eventarc'
_API_VERSION = 'v1beta1'


def GetTriggerURI(resource):
  trigger = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='eventarc.projects.locations.triggers')
  return trigger.SelfLink()


class TriggersClient(object):
  """Client for Triggers service in the Eventarc API."""

  def __init__(self):
    client = apis.GetClientInstance(_API_NAME, _API_VERSION)
    self._messages = client.MESSAGES_MODULE
    self._service = client.projects_locations_triggers

  def List(self, location_ref, limit, page_size):
    """Lists Triggers in a given location.

    Args:
      location_ref: Resource, the location to list Triggers in.
      limit: int or None, the total number of results to return.
      page_size: int, the number of entries in each batch (affects requests
        made, but not the yielded results).

    Returns:
      A generator of Triggers in the location.
    """
    list_req = self._messages.EventarcProjectsLocationsTriggersListRequest(
        parent=location_ref.RelativeName(), pageSize=page_size)
    return list_pager.YieldFromList(
        self._service,
        list_req,
        field='triggers',
        batch_size=page_size,
        limit=limit,
        batch_size_attribute='pageSize')
