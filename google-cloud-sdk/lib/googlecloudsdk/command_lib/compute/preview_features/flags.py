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
"""Flags and helpers for the compute preview_features commands."""

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


class PreviewFeaturesCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(PreviewFeaturesCompleter, self).__init__(
        collection='compute.previewFeatures',
        list_command='compute preview_features list --uri',
        **kwargs
    )


def PreviewFeatureArgument():
  """Returns an argument for preview feature resource."""
  return compute_flags.ResourceArgument(
      resource_name='preview feature',
      name='preview_feature',
      completer=compute_completers.PreviewFeaturesCompleter,
      plural=False,
      global_collection='compute.previewFeatures',
  )
