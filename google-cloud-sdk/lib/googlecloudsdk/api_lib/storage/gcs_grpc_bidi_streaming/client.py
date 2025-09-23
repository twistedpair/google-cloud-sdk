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

"""Client for Google Cloud Storage data plane API using gRPC bidi streaming."""

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import download
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage.tasks.cp import download_util


class GcsGrpcBidiStreamingClient(cloud_api.CloudApi):
  """Client for Google Cloud Storage data plane API using gRPC bidi streaming.

  Bidi streaming is supported for Zonal buckets currently so this
  client will only used for zonal buckets. This client will be merged with gRPC
  once the support is added for all the bucket types.

  TODO(b/437037554): Merge this client with gRPC client once the support is
  added for all bucket types.
  """

  capabilities = []

  def __init__(self):
    super(GcsGrpcBidiStreamingClient, self).__init__()
    self._gapic_client = None
    # The delegator is responsible for delegating the requests to the
    # appropriate client.
    self._delegator = gcs_json_client.JsonClient()

  def _get_gapic_client(self, redact_request_body_reason=None):
    # Not using @property because the side-effect is non-trivial and
    # might not be obvious. Someone might accidentally access the
    # property and end up creating the gapic client.
    # Creating the gapic client before "fork" will lead to a deadlock.
    if self._gapic_client is None:
      self._gapic_client = core_apis.GetGapicClientInstance(
          'storage',
          'v2',
          attempt_direct_path=True,
          redact_request_body_reason=redact_request_body_reason,
      )
    return self._gapic_client

  def get_object_metadata(
      self,
      bucket_name,
      object_name,
      request_config=None,
      generation=None,
      fields_scope=None,
      soft_deleted=False,
  ):
    """See super class."""
    object_metadata = self._delegator.get_object_metadata(
        bucket_name=bucket_name,
        object_name=object_name,
        request_config=request_config,
        generation=generation,
        fields_scope=fields_scope,
        soft_deleted=soft_deleted,
    )
    return object_metadata

  def download_object(
      self,
      cloud_resource,
      download_stream,
      request_config,
      digesters=None,
      do_not_decompress=False,
      download_strategy=cloud_api.DownloadStrategy.RESUMABLE,
      progress_callback=None,
      start_byte=0,
      end_byte=None,
  ):
    """See super class."""
    if download_util.return_and_report_if_nothing_to_download(
        cloud_resource, progress_callback
    ):
      return None

    decryption_key = None
    if request_config.resource_args:
      decryption_key = getattr(
          request_config.resource_args, 'decryption_key', None
      )

    downloader = download.BidiGrpcDownload(
        gapic_client=self._get_gapic_client(),
        cloud_resource=cloud_resource,
        download_stream=download_stream,
        start_byte=start_byte,
        end_byte=end_byte,
        digesters=digesters,
        progress_callback=progress_callback,
        download_strategy=download_strategy,
        decryption_key=decryption_key
    )
    downloader.run()

    # Unlike JSON, the response message for gRPC does not hold any
    # content-encoding information. Hence, we do not have to return the
    # server encoding here.
    return None

  def upload_object(
      self,
      source_stream,
      destination_resource,
      request_config,
      posix_to_set=None,
      serialization_data=None,
      source_resource=None,
      tracker_callback=None,
      upload_strategy=cloud_api.UploadStrategy.SIMPLE,
  ):
    """See super class."""
    raise NotImplementedError()
