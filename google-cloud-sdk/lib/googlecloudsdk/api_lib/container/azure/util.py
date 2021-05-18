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

"""Utilities Cloud GKE Multi-cloud for Azure API."""

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


class _AzureClientBase(object):
  """Base class for Azure clients."""

  def __init__(self, client=None, messages=None, track=base.ReleaseTrack.GA):
    if track != base.ReleaseTrack.ALPHA:
      raise Exception('Only ALPHA release track currently supported.')
    self.track = track
    self.client = client or GetClientInstance(track)
    self.messages = messages or GetMessagesModule(track)
    self._service = self._GetService()

  def List(self, parent_ref, page_size, limit):
    req = self._service.GetRequestType('List')(parent=parent_ref.RelativeName())
    return list_pager.YieldFromList(
        self._service,
        req,
        field=self.GetListResultsField(),
        limit=limit,
        batch_size=page_size,
        batch_size_attribute='pageSize')
    # return self._service.List(req)

  def Get(self, resource_ref):
    """Get an Azure resource."""

    req = self._service.GetRequestType('Get')(name=resource_ref.RelativeName())
    return self._service.Get(req)

  def Delete(self, resource_ref, validate_only=None, allow_missing=None):
    """Delete an Azure resource."""

    req = self._service.GetRequestType('Delete')(
        name=resource_ref.RelativeName())
    if validate_only:
      req.validateOnly = True
    if allow_missing:
      req.allowMissing = True

    return self._service.Delete(req)

  def _GetService(self):
    raise NotImplementedError(
        '_GetService() method not implemented for this type')

  def GetListResultsField(self):
    raise NotImplementedError(
        'GetListResultsField() method not implemented for this type')


class ClientsClient(_AzureClientBase):
  """Client for Azure Clients in the gkemulticloud API."""

  def Create(self, client_ref, tenant_id, application_id, validate_only=False):
    """Create a new Azure client."""
    req = self.messages.GkemulticloudProjectsLocationsAzureClientsCreateRequest(
        azureClientId=client_ref.azureClientsId,
        parent=client_ref.Parent().RelativeName())
    if validate_only:
      req.validateOnly = True

    client = self._AddClient(req)
    client.name = client_ref.azureClientsId
    client.applicationId = application_id
    client.tenantId = tenant_id

    return self._service.Create(req)

  def GetListResultsField(self):
    return 'azureClients'

  def _GetService(self):
    return self.client.projects_locations_azureClients

  def _AddClient(self, req):
    # Using this to hide the 'v1alpha' that shows up in the type.
    version = GetApiVersionForTrack(self.track).capitalize()
    msg = 'GoogleCloudGkemulticloud{}AzureClient'.format(version)
    attr = 'googleCloudGkemulticloud{}AzureClient'.format(version)
    client = getattr(self.messages, msg)()
    setattr(req, attr, client)
    return client
