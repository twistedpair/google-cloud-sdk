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
"""A library for streaming prediction results from the Vertex AI PredictionService API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.api_lib.util import apis


class PredictionStreamer(object):
  """Streams prediction responses using gRPC."""

  def __init__(self, version):
    self.client = apis.GetGapicClientInstance('aiplatform', version)

  def StreamDirectPredict(
      self,
      endpoint,
      inputs,
      parameters,
  ):
    """Streams prediction results from the Cloud Vertex AI PredictionService API.

    Args:
      endpoint: The name of the endpoint to stream predictions from.
      inputs: The inputs to send to the endpoint.
      parameters: The parameters to send to the endpoint.

    Yields:
      Streamed prediction results.
    """
    # Construct the request.
    request = self.client.types.StreamDirectPredictRequest(endpoint=endpoint)
    for curr_input in inputs:
      request.inputs.append(
          self.client.types.Tensor.from_json(json.dumps(curr_input))
      )
    request.parameters = self.client.types.Tensor.from_json(
        json.dumps(parameters)
    )

    for prediction in self.client.prediction.stream_direct_predict(
        iter([request])
    ):
      yield prediction

  def StreamDirectRawPredict(
      self,
      endpoint,
      method_name,
      input,
  ):
    """Streams prediction results from the Cloud Vertex AI PredictionService API.

    Args:
      endpoint: The name of the endpoint to stream predictions from.
      method_name: The name of the method to call.
      input: The input bytes to send to the endpoint.

    Yields:
      Streamed prediction results.
    """
    # Construct the request.
    request = self.client.types.StreamDirectRawPredictRequest(
        endpoint=endpoint, method_name=method_name, input=input
    )

    for prediction in self.client.prediction.stream_direct_raw_predict(
        iter([request])
    ):
      yield prediction
