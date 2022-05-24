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

import abc
import json

from apitools.base.py import transfer

from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import gcs_metadata_util
from googlecloudsdk.api_lib.storage import retry_util
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import scaled_integer

import six


class _Upload(six.with_metaclass(abc.ABCMeta, object)):
  """Base class shared by different upload strategies."""

  def __init__(self,
               gcs_api,
               http_client,
               source_stream,
               destination_resource,
               should_gzip_in_flight,
               request_config,
               source_resource=None):
    """Initializes an _Upload instance.

    Args:
      gcs_api (gcs_api.GcsApi): The API used to execute the upload request.
      http_client: An httplib2.Http-like object.
      source_stream (io.IOBase): Yields bytes to upload.
      destination_resource (resource_reference.ObjectResource|UnknownResource):
        Metadata for the destination object.
      should_gzip_in_flight (bool): Should gzip encode upload in flight.
      request_config (gcs_api.GcsRequestConfig): Tracks additional request
        preferences.
      source_resource (resource_reference.FileObjectResource|None): Contains the
        source StorageUrl. Can be None if source is pure stream.
    """
    self._gcs_api = gcs_api
    self._http_client = http_client
    self._source_stream = source_stream
    self._destination_resource = destination_resource
    self._should_gzip_in_flight = should_gzip_in_flight
    self._request_config = request_config
    self._source_resource = source_resource

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
        bucket=self._destination_resource.storage_url.bucket_name)

    if self._source_resource:
      source_file_path = self._source_resource.storage_url.object_name
    else:
      source_file_path = None
    gcs_metadata_util.update_object_metadata_from_request_config(
        object_metadata, self._request_config, source_file_path)

    return self._gcs_api.messages.StorageObjectsInsertRequest(
        bucket=object_metadata.bucket,
        object=object_metadata,
        ifGenerationMatch=copy_util.get_generation_match_value(
            self._request_config),
        ifMetagenerationMatch=(
            self._request_config.precondition_metageneration_match),
        predefinedAcl=predefined_acl)

  @abc.abstractmethod
  def run(self):
    """Performs an upload and returns an Object message."""
    pass


class SimpleUpload(_Upload):
  """Uploads objects with a single request."""

  def run(self):
    resource_args = self._request_config.resource_args
    apitools_upload = transfer.Upload(
        self._source_stream,
        resource_args.content_type,
        gzip_encoded=self._should_gzip_in_flight,
        total_size=resource_args.size)
    apitools_upload.bytes_http = self._http_client
    apitools_upload.strategy = transfer.SIMPLE_UPLOAD

    return self._gcs_api.client.objects.Insert(
        self._get_validated_insert_request(), upload=apitools_upload)


class _BaseRecoverableUpload(_Upload):
  """Common logic for strategies allowing retries in-flight."""

  def _get_upload(self):
    """Returns an apitools upload class used for a new transfer."""
    resource_args = self._request_config.resource_args
    size = getattr(resource_args, 'size', None)
    max_retries = properties.VALUES.storage.max_retries.GetInt()
    apitools_upload = transfer.Upload(
        self._source_stream,
        resource_args.content_type,
        auto_transfer=False,
        chunksize=scaled_integer.ParseInteger(
            properties.VALUES.storage.upload_chunk_size.Get()),
        gzip_encoded=self._should_gzip_in_flight,
        total_size=size,
        num_retries=max_retries)
    apitools_upload.strategy = transfer.RESUMABLE_UPLOAD
    return apitools_upload

  def _initialize_upload(self, apitools_upload):
    """Inserts a a new object at the upload destination."""
    if not apitools_upload.initialized:
      self._gcs_api.client.objects.Insert(
          self._get_validated_insert_request(), upload=apitools_upload)

  @abc.abstractmethod
  def _call_appropriate_apitools_upload_strategy(self, apitools_upload):
    """Responsible for pushing bytes to GCS with an appropriate strategy."""
    pass

  def run(self):
    """Uploads with in-flight retry logic and returns an Object message."""
    max_retries = properties.VALUES.storage.max_retries.GetInt()

    apitools_upload = self._get_upload()
    apitools_upload.bytes_http = self._http_client
    retry_util.set_retry_func(apitools_upload)

    self._initialize_upload(apitools_upload)

    attempt = 0
    last_progress_byte = apitools_upload.progress
    # Not using Retryer because we do not require any delays between runs
    # and updating the attempts requires manipulating state.retrial.
    while True:
      try:
        http_response = self._call_appropriate_apitools_upload_strategy(
            apitools_upload)
        break
      except errors.RetryableApiError:
        apitools_upload.RefreshResumableUploadState()
        if apitools_upload.progress > last_progress_byte:
          # Progress was made.
          last_progress_byte = apitools_upload.progress
          attempt = 0
          continue
      attempt += 1
      if attempt > max_retries:
        raise errors.ResumableUploadAbortError(
            'Max attempts reached after retrying {} times.'
            ' Aborting.'.format(attempt))

    return self._gcs_api.client.objects.ProcessHttpResponse(
        self._gcs_api.client.objects.GetMethodConfig('Insert'), http_response)


class StreamingUpload(_BaseRecoverableUpload):
  """Uploads objects from a stream with support for error recovery in-flight."""

  def _call_appropriate_apitools_upload_strategy(self, apitools_upload):
    """Calls StreamInChunks since the final size is unknown."""
    return apitools_upload.StreamInChunks()


class ResumableUpload(_BaseRecoverableUpload):
  """Uploads objects with support for resuming between runs of a command."""

  # pylint: disable=g-doc-args
  def __init__(self,
               gcs_api,
               http_client,
               source_stream,
               destination_resource,
               should_gzip_in_flight,
               request_config,
               source_resource=None,
               serialization_data=None,
               tracker_callback=None):
    """Initializes a ResumableUpload instance.

    See super class for arguments not described below.

    New Args:
      serialization_data (dict): JSON used by apitools to resume an upload.
    """
    # pylint: enable=g-doc-args
    super(ResumableUpload,
          self).__init__(gcs_api, http_client, source_stream,
                         destination_resource, should_gzip_in_flight,
                         request_config, source_resource)
    self._serialization_data = serialization_data
    self._tracker_callback = tracker_callback

  def _get_upload(self):
    """Creates a new transfer object, or gets one from serialization data."""
    max_retries = properties.VALUES.storage.max_retries.GetInt()
    if self._serialization_data is not None:
      # FromData implicitly sets strategy as RESUMABLE.
      return transfer.Upload.FromData(
          self._source_stream,
          json.dumps(self._serialization_data),
          self._gcs_api.client.http,
          auto_transfer=False,
          gzip_encoded=self._should_gzip_in_flight,
          num_retries=max_retries)
    else:
      return super(__class__, self)._get_upload()

  def _initialize_upload(self, apitools_upload):
    """Inserts an object if not already inserted, and writes a tracker file."""
    if self._serialization_data is None:
      super(__class__, self)._initialize_upload(apitools_upload)

    if self._tracker_callback is not None:
      self._tracker_callback(apitools_upload.serialization_data)

  def _call_appropriate_apitools_upload_strategy(self, apitools_upload):
    """Calls StreamMedia, or StreamInChunks when the final size is unknown."""
    if self._should_gzip_in_flight:
      # We do not know the final size of the file, so we must use chunks.
      return apitools_upload.StreamInChunks()
    else:
      # We know the size of the file, so use a strategy that requires fewer
      # round trip API calls.
      return apitools_upload.StreamMedia()
