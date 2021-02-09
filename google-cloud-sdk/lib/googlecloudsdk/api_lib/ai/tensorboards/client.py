# -*- coding: utf-8 -*- #
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
"""Utilities for AI Platform Tensorboards API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.util.args import labels_util


class TensorboardsClient(object):
  """High-level client for the AI Platform Tensorboard surface."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[constants.ALPHA_VERSION])
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_tensorboards

  def Create(self, location_ref, args):
    """Create a new Tensorboard."""
    labels = labels_util.ParseCreateArgs(
        args,
        self.messages.GoogleCloudAiplatformV1alpha1Tensorboard.LabelsValue)
    request = self.messages.AiplatformProjectsLocationsTensorboardsCreateRequest(
        parent=location_ref.RelativeName(),
        googleCloudAiplatformV1alpha1Tensorboard=self.messages
        .GoogleCloudAiplatformV1alpha1Tensorboard(
            displayName=args.display_name,
            description=args.description,
            labels=labels))
    return self._service.Create(request)
