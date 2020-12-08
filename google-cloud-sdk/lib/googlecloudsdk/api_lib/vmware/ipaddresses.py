# -*- coding: utf-8 -*- # # Copyright 2020 Google LLC. All Rights Reserved.
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
"""Cloud vmware IPAdresses client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.vmware import util
from googlecloudsdk.command_lib.vmware import flags


class IPAddressesClient(util.VmwareClientBase):
  """cloud vmware ip addresses client."""

  def __init__(self):
    super(IPAddressesClient, self).__init__()
    self.service = self.client.projects_locations_clusterGroups_ipAddresses

  def Create(self, resource, internal_ip, labels=None):
    ip_address = self.messages.IpAddress(internalIp=internal_ip)
    flags.AddLabelsToMessage(labels, ip_address)

    request = self.messages.SddcProjectsLocationsClusterGroupsIpAddressesCreateRequest(
        ipAddress=ip_address,
        ipAddressId=resource.Name(),
        parent=resource.Parent().RelativeName())

    return self.service.Create(request)

  def Delete(self, resource):
    request = self.messages.SddcProjectsLocationsClusterGroupsIpAddressesDeleteRequest(
        name=resource.RelativeName())
    return self.service.Delete(request)

  def Get(self, resource):
    request = self.messages.SddcProjectsLocationsClusterGroupsIpAddressesGetRequest(
        name=resource.RelativeName())
    return self.service.Get(request)

  def List(self,
           resource,
           filter_expression=None,
           limit=None,
           page_size=None):
    ip_name = resource.RelativeName()
    request = self.messages.SddcProjectsLocationsClusterGroupsIpAddressesListRequest(
        parent=ip_name, filter=filter_expression)
    if page_size:
      request.page_size = page_size
    return list_pager.YieldFromList(
        self.service,
        request,
        limit=limit,
        batch_size_attribute='pageSize',
        batch_size=page_size,
        field='ipAddresses')
