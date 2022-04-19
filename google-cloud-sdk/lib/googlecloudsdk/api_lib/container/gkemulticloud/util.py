# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for gkemulticloud API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

_VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1',
    base.ReleaseTrack.BETA: 'v1',
    base.ReleaseTrack.GA: 'v1',
}

MODULE_NAME = 'gkemulticloud'


def GetApiVersionForTrack(release_track=base.ReleaseTrack.GA):
  return _VERSION_MAP.get(release_track)


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  api_version = _VERSION_MAP.get(release_track)
  return apis.GetMessagesModule(MODULE_NAME, api_version)


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  api_version = _VERSION_MAP.get(release_track)
  return apis.GetClientInstance(MODULE_NAME, api_version)


class ClientBase(object):
  """Base class for gkemulticloud API clients."""

  def __init__(self, service=None, list_result_field=None):
    self._client = GetClientInstance()
    self._messages = GetMessagesModule()
    self._service = service
    self._list_result_field = list_result_field

  def List(self, parent_ref, page_size, limit):
    """Lists gkemulticloud API resources."""
    req = self._service.GetRequestType('List')(parent=parent_ref.RelativeName())
    for item in list_pager.YieldFromList(
        self._service,
        req,
        field=self._list_result_field,
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize'):
      yield item

  def Get(self, resource_ref):
    """Gets a gkemulticloud API resource."""
    req = self._service.GetRequestType('Get')(name=resource_ref.RelativeName())
    return self._service.Get(req)

  def Delete(self, resource_ref, validate_only=None, allow_missing=None):
    """Deletes a gkemulticloud API resource."""
    req = self._service.GetRequestType('Delete')(
        name=resource_ref.RelativeName())
    if validate_only:
      req.validateOnly = True
    if allow_missing:
      req.allowMissing = True
    return self._service.Delete(req)
