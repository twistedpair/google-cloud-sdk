# Lint as: python3
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
"""Module to handle Cloud KMS calls needed in the gcloud ca interface.

Contains calls to interact with cloud KMS keys such as obtaining keys
for use in gcloud ca commands.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis

CLOUD_KMS_VERSION = "v1"
CLOUD_KMS_API = "cloudkms"


def GetClient():
  return apis.GetClientInstance(CLOUD_KMS_API, CLOUD_KMS_VERSION)


def GetMessagesModule():
  return apis.GetMessagesModule(CLOUD_KMS_API, CLOUD_KMS_VERSION)


def GetCryptoKeyVersion(resource_ref):
  """Get Crypto Key Version from KMS using resource reference.

  Args:
    resource_ref: A resources.Resource for the CryptoKeyVersion.

  Returns:
    The corresponding CryptoKeyVersion message
  """
  client = GetClient()
  messages = GetMessagesModule()

  version = client.projects_locations_keyRings_cryptoKeys_cryptoKeyVersions.Get(
      messages
      .CloudkmsProjectsLocationsKeyRingsCryptoKeysCryptoKeyVersionsGetRequest(
          name=resource_ref.RelativeName()))

  return version
