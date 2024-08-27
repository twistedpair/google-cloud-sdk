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

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants


class ModelGardenClient(object):
  """Client used for interacting with Model Garden APIs."""

  def __init__(self, version=constants.GA_VERSION):
    client = apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[version],
    )
    self._messages = client.MESSAGES_MODULE
    self._service = client.publishers_models

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
    return self._service.Get(request)
