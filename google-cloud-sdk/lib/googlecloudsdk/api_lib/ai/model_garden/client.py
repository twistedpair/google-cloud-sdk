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
"""Utilities for Vertex AI Model Garden APIs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants


class ModelGardenClient(object):
  """Client used for interacting with Model Garden APIs."""

  def __init__(self, version=constants.BETA_VERSION):
    client = apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[version],
    )
    self._messages = client.MESSAGES_MODULE
    self._publishers_models_service = client.publishers_models
    self._projects_locations_service = client.projects_locations

  def GetPublisherModel(self, model_name, is_hugging_face_model=False):
    """Get a publisher model.

    Args:
      model_name: The name of the model to get. The format should be
        publishers/{publisher}/models/{model}
      is_hugging_face_model: Whether the model is a hugging face model.

    Returns:
      A publisher model.
    """
    request = self._messages.AiplatformPublishersModelsGetRequest(
        name=model_name, isHuggingFaceModel=is_hugging_face_model
    )
    return self._publishers_models_service.Get(request)

  def DeployPublisherModel(
      self,
      project,
      location,
      model,
      accept_eula,
      accelerator_type,
      accelerator_count,
      machine_type,
      endpoint_display_name,
      hugging_face_access_token,
  ):
    """Deploy an open source publisher model.

    Args:
      project: The project to deploy the model to.
      location: The location to deploy the model to.
      model: The name of the model to deploy.
      accept_eula: Whether to accept the end-user license agreement.
      accelerator_type: The type of accelerator to use.
      accelerator_count: The number of accelerators to use.
      machine_type: The type of machine to use.
      endpoint_display_name: The display name of the endpoint.
      hugging_face_access_token: The Hugging Face access token.

    Returns:
      The deploy long-running operation.
    """
    deploy_request = self._messages.GoogleCloudAiplatformV1beta1DeployPublisherModelRequest(
        model=model,
        endpointDisplayName=endpoint_display_name,
        huggingFaceAccessToken=hugging_face_access_token,
        acceptEula=accept_eula,
        dedicatedResources=self._messages.GoogleCloudAiplatformV1beta1DedicatedResources(
            machineSpec=self._messages.GoogleCloudAiplatformV1beta1MachineSpec(
                machineType=machine_type,
                acceleratorType=accelerator_type,
                acceleratorCount=accelerator_count,
            )
        ),
    )
    request = self._messages.AiplatformProjectsLocationsDeployRequest(
        destination=f'projects/{project}/locations/{location}',
        googleCloudAiplatformV1beta1DeployPublisherModelRequest=deploy_request,
    )
    return self._projects_locations_service.Deploy(request)

  def ListPublisherModels(
      self, limit=None, batch_size=100, list_hf_models=False
  ):
    """List publisher models in Model Garden.

    Args:
      limit: The maximum number of items to list. None if all available records
        should be yielded.
      batch_size: The number of items to list per page.
      list_hf_models: Whether to only list Hugging Face models.

    Returns:
      The list of publisher models in Model Garden..
    """
    return list_pager.YieldFromList(
        self._publishers_models_service,
        self._messages.AiplatformPublishersModelsListRequest(
            parent='publishers/*',
            listAllVersions=True,
            filter='is_hf_wildcard(true)'
            if list_hf_models
            else 'is_hf_wildcard(false)',
        ),
        field='publisherModels',
        batch_size_attribute='pageSize',
        batch_size=batch_size,
        limit=limit,
    )
