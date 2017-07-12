# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Functions for creating a client to talk to the App Engine Admin API."""

from googlecloudsdk.api_lib.app import operations_util
from googlecloudsdk.api_lib.app.api import appengine_api_client_base as base
from googlecloudsdk.api_lib.app.api import requests
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


class AppengineAppUpdateApiClient(base.AppengineApiClientBase):
  """Client used by gcloud to communicate with the App Engine API."""

  def __init__(self, client):
    base.AppengineApiClientBase.__init__(self, client)

    self._registry = resources.REGISTRY.Clone()
    self._registry.RegisterApiByName('appengine', self.ApiVersion())

  @classmethod
  def ApiVersion(cls):
    return 'v1beta'

  def PatchApplication(self,
                       split_health_checks=None):
    """Updates an application.

    Args:
      split_health_checks: Boolean, whether to enable split health checks by
      default.

    Returns:
      Long running operation.
    """
    # Create a configuration update request.
    application_update = self.messages.Application()
    update_mask = ''
    if split_health_checks is not None:
      update_mask = 'featureSettings'
      application_update.featureSettings = self.messages.FeatureSettings(
          splitHealthChecks=split_health_checks)

    update_request = self.messages.AppengineAppsPatchRequest(
        name=self._FormatApp(),
        application=application_update,
        updateMask=update_mask)

    operation = requests.MakeRequest(
        self.client.apps.Patch, update_request)

    log.debug('Received operation: [{operation}]'.format(
        operation=operation.name))

    return operations_util.WaitForOperation(self.client.apps_operations,
                                            operation)
