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
"""Support library to handle the delivery-pipeline subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.clouddeploy import client_util


class DeliveryPipelinesClient(object):
  """Client for delivery pipeline service in the Cloud Deploy API."""

  def __init__(self, client=None, messages=None):
    """Initialize a delivery_pipeline.DeliveryPipelinesClient.

    Args:
      client: base_api.BaseApiClient, the client class for Cloud Deploy.
      messages: module containing the definitions of messages for Cloud Deploy.
    """
    self.client = client or client_util.GetClientInstance()
    self.messages = messages or client_util.GetMessagesModule(client)
    self._service = self.client.projects_locations_deliveryPipelines

  def Get(self, name):
    """Gets the delivery pipeline object by calling the delivery pipeline get API.

    Args:
      name: delivery pipeline name.

    Returns:
      a delivery pipeline object.
    """
    request = self.messages.ClouddeployProjectsLocationsDeliveryPipelinesGetRequest(
        name=name)
    return self._service.Get(request)
