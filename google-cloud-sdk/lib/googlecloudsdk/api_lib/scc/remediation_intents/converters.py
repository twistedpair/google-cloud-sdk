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
"""Module for storing converters to be used in the remediation intents."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Mapping, Sequence, Any, Dict

from googlecloudsdk.api_lib.scc.remediation_intents import sps_api
from googlecloudsdk.calliope import base


class RemediationIntentConverter():
  """Converter related to the Remediation Intent resource."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    """Initializes the RemediationIntentConverter.

    Args:
      release_track: The release track to use for the API version.
    """
    self.messages = sps_api.GetMessagesModule(release_track)

  def DictFilesToMessage(self, files_dict: Mapping[str, str]) -> Sequence[Any]:
    """Converts a dictionary of files with their content to the message.

    Args:
      files_dict: A dictionary of files with their content. [path: content]

    Returns:
      List of message of type [securityposture.messages.FileData]
    """
    return [
        self.messages.FileData(filePath=path, fileContent=content)
        for path, content in files_dict.items()
    ]

  def MessageFilesToDict(self, files_data: Sequence[Any]) -> Mapping[str, str]:
    """Converts a list of file messages to a dictionary.

    Args:
      files_data: A list of file messages. [securityposture.messages.FileData]

    Returns:
      A dictionary of files with their content. [path: content]
    """
    result: Dict[str, str] = {
        file_data.filePath: file_data.fileContent
        for file_data in files_data
    }
    return result
