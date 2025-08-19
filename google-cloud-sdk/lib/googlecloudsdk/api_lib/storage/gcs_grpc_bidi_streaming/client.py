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
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client


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
    raise NotImplementedError()

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
