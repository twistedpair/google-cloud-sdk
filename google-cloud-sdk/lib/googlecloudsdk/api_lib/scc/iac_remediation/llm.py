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
"""Library for interacting with the LLM model APIs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.scc.iac_remediation import const
from googlecloudsdk.api_lib.util import apis


def GetClient():
  return apis.GetClientInstance(const.LLM_API_NAME, const.LLM_API_VERSION)


def GetMessages():
  return apis.GetMessagesModule(const.LLM_API_NAME, const.LLM_API_VERSION)


def MakeLLMCall(
    input_text,
    proj_id,
    model_name=const.LLM_DEFAULT_MODEL_NAME,
) -> str:
  """Makes a call to the LLM.

  Args:
    input_text: string of the prompt to be sent to the LLM
    proj_id: project_id of the LLM enabled project
    model_name: name of the LLM model to be used

  Returns:
    LLM response in string
  """
  client = GetClient()
  messages = GetMessages()
  request = messages.AiplatformProjectsLocationsEndpointsGenerateContentRequest(
      googleCloudAiplatformV1GenerateContentRequest=messages.GoogleCloudAiplatformV1GenerateContentRequest(
          contents=[
              messages.GoogleCloudAiplatformV1Content(
                  parts=[
                      messages.GoogleCloudAiplatformV1Part(text=input_text)
                  ],
                  role='user')
          ]
      ),
      # model API endpoint to be used for the LLM call
      model=f'projects/{proj_id}/locations/us-central1/publishers/google/models/{model_name}',
  )
  resp = client.projects_locations_endpoints.GenerateContent(request)
  return resp.candidates[0].content.parts[0].text
