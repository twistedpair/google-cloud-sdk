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
"""Utilities for calling the Composer API."""

from __future__ import absolute_import
from __future__ import unicode_literals
from apitools.base.py import encoding

from googlecloudsdk.api_lib.util import apis
import six

COMPOSER_API_NAME = 'composer'
COMPOSER_API_VERSION = 'v1beta1'

SUPPORTED_LOCATIONS = ['us-central1', 'europe-west1']
DEFAULT_PAGE_SIZE = 30


def GetClientInstance(version=COMPOSER_API_VERSION):
  return apis.GetClientInstance(COMPOSER_API_NAME, version)


def GetMessagesModule(version=COMPOSER_API_VERSION):
  return apis.GetMessagesModule(COMPOSER_API_NAME, version)


def ParseOperationJsonMetadata(metadata_value, metadata_type):
  if not metadata_value:
    return metadata_type()
  return encoding.JsonToMessage(metadata_type,
                                encoding.MessageToJson(metadata_value))


def DictToMessage(dictionary, msg_type):
  return msg_type(additionalProperties=[
      msg_type.AdditionalProperty(key=key, value=value)
      for key, value in six.iteritems(dictionary)
  ])
