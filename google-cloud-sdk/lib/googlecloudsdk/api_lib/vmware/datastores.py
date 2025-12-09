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
"""Cloud vmware datastores client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util


class DatastoresClient(util.VmwareClientBase):
  """Cloud vmware datastores client."""

  def __init__(self):
    super(DatastoresClient, self).__init__()
    self.service = self.client.projects_locations_datastores

  def Get(self, resource):
    """Gets a datastore."""
    request = self.messages.VmwareengineProjectsLocationsDatastoresGetRequest(
        name=resource.RelativeName()
    )
    return self.service.Get(request)

  def List(self, location_resource):
    """Lists datastores in a given location."""
    location = location_resource.RelativeName()
    request = self.messages.VmwareengineProjectsLocationsDatastoresListRequest(
        parent=location
    )
    return list_pager.YieldFromList(
        self.service,
        request,
        batch_size_attribute='pageSize',
        field='datastores',
    )

  def Delete(self, resource, etag=None):
    request = (
        self.messages.VmwareengineProjectsLocationsDatastoresDeleteRequest(
            name=resource.RelativeName(), etag=etag
        )
    )
    return self.service.Delete(request)

  def Update(self, resource, description=None):
    datastore = self.Get(resource)
    update_mask = []
    if description is not None:
      datastore.description = description
      update_mask.append('description')
    request = self.messages.VmwareengineProjectsLocationsDatastoresPatchRequest(
        datastore=datastore,
        name=resource.RelativeName(),
        updateMask=','.join(update_mask),
    )
    return self.service.Patch(request)

  def Create(
      self,
      resource,
      description=None,
      netapp_volume=None,
      filestore_instance=None,
      third_party_nfs_network=None,
      third_party_nfs_file_share=None,
      third_party_nfs_servers=None,
  ):
    """Creates a datastore."""
    parent = resource.Parent().RelativeName()
    datastore_id = resource.Name()
    datastore = self.messages.Datastore(description=description)
    nfs_datastore = self.messages.NfsDatastore()
    if netapp_volume:
      nfs_datastore.googleFileService = (
          self.messages.GoogleFileService(
              netappVolume=netapp_volume
          )
      )
    elif filestore_instance:
      nfs_datastore.googleFileService = (
          self.messages.GoogleFileService(
              filestoreInstance=filestore_instance
          )
      )
    elif third_party_nfs_servers:
      nfs_datastore.thirdPartyFileService = (
          self.messages.ThirdPartyFileService(
              servers=third_party_nfs_servers,
              fileShare=third_party_nfs_file_share,
              network=third_party_nfs_network,
          )
      )
    datastore.nfsDatastore = nfs_datastore
    request = (
        self.messages.VmwareengineProjectsLocationsDatastoresCreateRequest(
            parent=parent,
            datastoreId=datastore_id,
            datastore=datastore,
        )
    )
    return self.service.Create(request)
