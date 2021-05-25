# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Classes that represent and execute different upload strategies for GCS."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import transfer

from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer


class _Upload:
  """Base class shared by different upload strategies."""

  def __init__(self,
               gcs_api,
               http_client,
               source_stream,
               content_type,
               destination_resource,
               request_config):
    """Initializes an _Upload instance.

    Args:
      gcs_api (gcs_api.GcsApi): The API used to execute the upload request.
      http_client: An httplib2.Http-like object.
      source_stream (io.IOBase): Yields bytes to upload.
      content_type (str): The content/MIME type associated with source_stream.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
          Metadata for the destination object.
      request_config (gcs_api.GcsRequestConfig): Tracks additional request
          preferences.
    """
    self._gcs_api = gcs_api
    self._http_client = http_client
    self._source_stream = source_stream
    self._content_type = content_type
    self._destination_resource = destination_resource
    self._request_config = request_config

  def _get_validated_insert_request(self):
    """Get an insert request that includes validated object metadata."""
    if self._request_config.predefined_acl_string:
      predefined_acl = getattr(
          self._gcs_api.messages.StorageObjectsInsertRequest
          .PredefinedAclValueValuesEnum,
          self._request_config.predefined_acl_string)
    else:
      predefined_acl = None

    object_metadata = self._gcs_api.messages.Object(
        name=self._destination_resource.storage_url.object_name,
        bucket=self._destination_resource.storage_url.bucket_name,
        md5Hash=self._request_config.md5_hash)

    return self._gcs_api.messages.StorageObjectsInsertRequest(
        bucket=object_metadata.bucket,
        object=object_metadata,
        ifGenerationMatch=self._request_config.precondition_generation_match,
        ifMetagenerationMatch=(
            self._request_config.precondition_metageneration_match),
        predefinedAcl=predefined_acl)

  def run(self):
    """Performs an upload and returns an Object message.

    Raises:
      NotImplementedError: This function was not implemented by a class
          using this interface.
    """
    raise NotImplementedError


class SimpleUpload(_Upload):
  """Uploads objects with a single request."""

  def run(self):
    apitools_upload = transfer.Upload(
        self._source_stream,
        self._content_type,
        gzip_encoded=self._request_config.gzip_encoded,
        total_size=self._request_config.size)
    apitools_upload.bytes_http = self._http_client
    apitools_upload.strategy = transfer.SIMPLE_UPLOAD

    return self._gcs_api.client.objects.Insert(
        self._get_validated_insert_request(), upload=apitools_upload)


class ResumableUpload(_Upload):
  """Uploads objects with support for resuming after interruptions."""

  def run(self):
    apitools_upload = transfer.Upload(
        self._source_stream,
        self._content_type,
        auto_transfer=False,
        chunksize=scaled_integer.ParseInteger(
            properties.VALUES.storage.upload_chunk_size.Get()),
        gzip_encoded=self._request_config.gzip_encoded,
        total_size=self._request_config.size)
    apitools_upload.bytes_http = self._http_client
    apitools_upload.strategy = transfer.RESUMABLE_UPLOAD

    self._gcs_api.client.objects.Insert(
        self._get_validated_insert_request(), upload=apitools_upload)

    if self._request_config.gzip_encoded:
      http_response = apitools_upload.StreamInChunks()
    else:
      http_response = apitools_upload.StreamMedia()

    return self._gcs_api.client.objects.ProcessHttpResponse(
        self._gcs_api.client.objects.GetMethodConfig('Insert'),
        http_response)
