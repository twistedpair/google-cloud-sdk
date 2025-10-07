# -*- coding: utf-8 -*- #
# Copyright 2025 Google Inc. All Rights Reserved.
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
"""Client for interaction with EncryptionConfig API CRUD DATAPLEX."""


from googlecloudsdk.api_lib.dataplex import util as dataplex_api


def GenerateEncryptionConfigForCreateRequest(args):
  """Create EncryptionConfig Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1EncryptionConfig(
      name='organizations/{0}/locations/{1}/encryptionConfigs/{2}'.format(
          args.organization, args.location, args.encryption_config
      ),
      key=args.key,
  )
  return request


def GenerateUpdateMask(args):
  """Generates update mask for EncryptionConfig."""
  update_mask = []
  if args.IsSpecified('enable_metastore_encryption'):
    update_mask.append('enableMetastoreEncryption')
  return update_mask


def GenerateEncryptionConfigForUpdateRequest(args):
  """Update EncryptionConfig Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1EncryptionConfig(
      name='organizations/{0}/locations/{1}/encryptionConfigs/{2}'.format(
          args.organization, args.location, args.encryption_config
      ),
      enableMetastoreEncryption=args.enable_metastore_encryption,
  )
  return request
