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
"""Utilities for dealing with AI Platform indexes API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants


class IndexesClient(object):
  """High-level client for the AI Platform indexes surface."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[constants.BETA_VERSION])
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_indexes

  def Get(self, index_ref):
    request = self.messages.AiplatformProjectsLocationsIndexesGetRequest(
        name=index_ref.RelativeName())
    return self._service.Get(request)

  def List(self, limit=None, region_ref=None):
    return list_pager.YieldFromList(
        self._service,
        self.messages.AiplatformProjectsLocationsIndexesListRequest(
            parent=region_ref.RelativeName()),
        field='indexes',
        batch_size_attribute='pageSize',
        limit=limit)
