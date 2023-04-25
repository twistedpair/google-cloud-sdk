# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Client for interacting with Google Cloud Storage using gRPC API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage.gcs_grpc import download
from googlecloudsdk.api_lib.storage.gcs_grpc import grpc_util
from googlecloudsdk.api_lib.storage.gcs_json import client as gcs_json_client
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.command_lib.storage.tasks.cp import download_util


class GrpcClientWithJsonFallback(gcs_json_client.JsonClient):
  """Client for Google Cloud Storage API using gRPC with JSON fallback."""

  def __init__(self):
    super(GrpcClientWithJsonFallback, self).__init__()
    self._gapic_client = None

  def _get_gapic_client(self):
    # Not using @property because the side-effect is non-trivial and
    # might not be obvious. Someone might accidentally access the
    # property and end up creating the gapic client.
    # Creating the gapic client before "fork" will lead to a deadlock.
    if self._gapic_client is None:
      self._gapic_client = core_apis.GetGapicClientInstance('storage', 'v2')
    return self._gapic_client

  def download_object(self,
                      cloud_resource,
                      download_stream,
                      request_config,
                      digesters=None,
                      do_not_decompress=False,
                      download_strategy=cloud_api.DownloadStrategy.RESUMABLE,
                      progress_callback=None,
                      start_byte=0,
                      end_byte=None):
    """See super class."""
    if download_util.return_and_report_if_nothing_to_download(
        cloud_resource, progress_callback
    ):
      return None

    downloader = download.GrpcDownload(
        gapic_client=self._get_gapic_client(),
        cloud_resource=cloud_resource,
        download_stream=download_stream,
        start_byte=start_byte,
        end_byte=end_byte,
        digesters=digesters,
        progress_callback=progress_callback)
    if download_strategy == cloud_api.DownloadStrategy.ONE_SHOT:
      downloader.simple_download()
    else:
      downloader.run(retriable_in_flight=True)
    # TODO(b/261180916) Return server encoding.
    return None

  def upload_object(self,
                    source_stream,
                    destination_resource,
                    request_config,
                    source_resource=None,
                    serialization_data=None,
                    tracker_callback=None,
                    upload_strategy=cloud_api.UploadStrategy.SIMPLE):
    """See CloudApi class for function doc strings."""
    return grpc_util.upload_object(self._get_gapic_client(),
                                   source_stream,
                                   destination_resource,
                                   request_config)
