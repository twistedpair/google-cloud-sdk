# -*- coding: utf-8 -*- #
# Copyright 2020 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Returns correct API client instance for user command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading

from googlecloudsdk.api_lib.storage import gcs_api
from googlecloudsdk.api_lib.storage import s3_api
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import properties

# Module variable for holding one API instance per thread per provider.
_cloud_api_thread_local_storage = threading.local()


def get_api(provider):
  """Returns thread local API instance for cloud provider.

  Uses thread local storage to make sure only one instance of an API exists
  per thread per provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.

  Returns:
    CloudApi client object for provider argument.

  Raises:
    ValueError: Invalid API provider.
  """
  if properties.VALUES.storage.use_threading_local.GetBool():
    api_client = getattr(_cloud_api_thread_local_storage, provider.value, None)
    if api_client:
      return api_client

  if provider == storage_url.ProviderPrefix.GCS:
    api_client = gcs_api.GcsApi()
  elif provider == storage_url.ProviderPrefix.S3:
    api_client = s3_api.S3Api()
  else:
    raise ValueError('Provider must be a valid storage_url.ProviderPrefix.')

  if properties.VALUES.storage.use_threading_local.GetBool():
    setattr(_cloud_api_thread_local_storage, provider.value, api_client)

  return api_client
