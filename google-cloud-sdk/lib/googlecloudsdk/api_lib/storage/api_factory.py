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

_INVALID_PROVIDER_PREFIX_MESSAGE = (
    'Invalid provider. Valid provider prefixes: {}'.format(', '.join(
        sorted([scheme.value for scheme in storage_url.VALID_CLOUD_SCHEMES]))))

# Module variable for holding one API instance per thread per provider.
_cloud_api_thread_local_storage = None


def _get_api_class(provider):
  """Returns a CloudApi subclass corresponding to the requested provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.

  Returns:
    An appropriate CloudApi subclass.

  Raises:
    ValueError: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  if provider == storage_url.ProviderPrefix.GCS:
    return gcs_api.GcsApi
  elif provider == storage_url.ProviderPrefix.S3:
    return s3_api.S3Api
  else:
    raise ValueError(_INVALID_PROVIDER_PREFIX_MESSAGE)


def get_api(provider):
  """Returns thread local API instance for cloud provider.

  Uses thread local storage to make sure only one instance of an API exists
  per thread per provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.

  Returns:
    CloudApi client object for provider argument.

  Raises:
    ValueError: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  global _cloud_api_thread_local_storage
  if properties.VALUES.storage.use_threading_local.GetBool():
    if not _cloud_api_thread_local_storage:
      _cloud_api_thread_local_storage = threading.local()

    api_client = getattr(_cloud_api_thread_local_storage, provider.value, None)
    if api_client:
      return api_client

  api_class = _get_api_class(provider)
  api_client = api_class()

  if properties.VALUES.storage.use_threading_local.GetBool():
    setattr(_cloud_api_thread_local_storage, provider.value, api_client)

  return api_client


def get_capabilities(provider):
  """Gets the capabilities of a cloud provider.

  Args:
    provider (storage_url.ProviderPrefix): Cloud provider prefix.

  Returns:
    The CloudApi.capabilities attribute for the requested provider.

  Raises:
    ValueError: If provider is not a cloud scheme in storage_url.ProviderPrefix.
  """
  api_class = _get_api_class(provider)
  return api_class.capabilities
