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

"""Utilities for Cloud Batch resource allowances API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.batch import util as batch_api_util


class ResourceAllowancesClient(object):
  """Client for resource allowances service in the Cloud Batch API."""

  def __init__(self, release_track, client=None, messages=None):
    self.client = client or batch_api_util.GetClientInstance(release_track)
    self.messages = messages or self.client.MESSAGES_MODULE
    self.service = self.client.projects_locations_resourceAllowances

  def Create(
      self, resource_allowance_id, location_ref, resource_allowance_config
  ):
    create_req_type = (
        self.messages.BatchProjectsLocationsResourceAllowancesCreateRequest
    )
    create_req = create_req_type(
        resourceAllowanceId=resource_allowance_id,
        parent=location_ref.RelativeName(),
        resourceAllowance=resource_allowance_config,
    )
    return self.service.Create(create_req)

  def Get(self, resource_allowance_ref):
    get_req_type = (
        self.messages.BatchProjectsLocationsResourceAllowancesGetRequest
    )
    get_req = get_req_type(name=resource_allowance_ref.RelativeName())
    return self.service.Get(get_req)

  def Delete(self, resource_allowance_ref):
    delete_req_type = (
        self.messages.BatchProjectsLocationsResourceAllowancesDeleteRequest
    )
    delete_req = delete_req_type(name=resource_allowance_ref.RelativeName())
    return self.service.Delete(delete_req)

  def Update(
      self, resource_allowance_ref, resource_allowance_config, update_mask
  ):
    update_req_type = (
        self.messages.BatchProjectsLocationsResourceAllowancesPatchRequest
    )
    update_req = update_req_type(
        name=resource_allowance_ref.RelativeName(),
        updateMask=','.join(update_mask),
        resourceAllowance=resource_allowance_config,
    )
    return self.service.Patch(update_req)
