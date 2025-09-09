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
"""Upload workflow using gRPC bidi streaming API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import io

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage.resources import resource_reference
import six


class _Upload(six.with_metaclass(abc.ABCMeta, object)):
  """Base class shared by different upload strategies."""

  def __init__(
      self,
      client,
      source_stream: io.IOBase,
      destination_resource: (
          resource_reference.ObjectResource | resource_reference.UnknownResource
      ),
      request_config: request_config_factory._GcsRequestConfig,
      source_resource: (
          resource_reference.FileObjectResource
          | resource_reference.ObjectResource
          | None
      ) = None,
      start_offset: int = 0,
      delegator: cloud_api.CloudApi | None = None,
  ):
    """Initializes _Upload.

    Args:
      client (gapic_clients.storage_v2.services.storage.client.StorageClient):
        The GAPIC client.
      source_stream: Yields bytes to upload.
      destination_resource: Metadata for the destination object.
      request_config: Tracks additional request preferences.
      source_resource: Contains the source StorageUrl and source object metadata
        for daisy chain transfers. Can be None if source is pure stream.
      start_offset: The offset from the beginning of the object at which
        the data should be written.
      delegator: The client used to make non-bidi streaming or metadata API
        calls.
    """
    self._client = client
    self._source_stream = source_stream
    self._destination_resource = destination_resource
    self._request_config = request_config
    self._start_offset = start_offset
    # Maintain the state of upload. Useful for resumable and streaming uploads.
    self._uploaded_so_far = start_offset
    self._source_resource = source_resource
    self._delegator = delegator

  @abc.abstractmethod
  def run(self):
    """Performs an upload and returns an Object message."""
    raise NotImplementedError()


class SimpleUpload(_Upload):
  """Uploads an object in single-shot mode."""

  def run(self):
    """Uploads the object in single-shot mode.

    Returns:
      gapic_clients.storage_v2.types.BidiWriteObjectResponse: A
        BidiWriteObjectResponse instance.
    """
    raise NotImplementedError()


class ResumableUpload(_Upload):
  """Uploads an object in resumable mode."""

  def run(self):
    """Uploads the object in resumable mode.

    Returns:
      gapic_clients.storage_v2.types.BidiWriteObjectResponse: A
        BidiWriteObjectResponse instance.
    """
    raise NotImplementedError()
