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
"""Retry wrapper for resumable BiDi downloads."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import retry_util as storage_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc import retry_util as grpc_retry_util
from googlecloudsdk.api_lib.storage.gcs_grpc_bidi_streaming import download
from googlecloudsdk.core.util import retry


def _should_retry_bidi(exc_type, exc_value, exc_traceback, state=None):
  """Returns True if the BiDi download error is retryable."""
  if isinstance(exc_value, BrokenPipeError):
    return False
  return isinstance(
      exc_value, download.BidiDownloadIncompleteError
  ) or grpc_retry_util.is_retriable(exc_type, exc_value, exc_traceback, state)


def run_with_retries(
    process_chunk_func,
    gapic_client,
    cloud_resource,
    download_stream,
    digesters,
    progress_callback,
    start_byte,
    end_byte,
    download_strategy,
    decryption_key,
    target_size,
):
  """Executes download with retries, resuming from processed_bytes."""
  bidi_downloader = download.BidiDownloader(
      process_chunk_func,
      gapic_client,
      cloud_resource,
      download_stream,
      digesters,
      progress_callback,
      start_byte,
      end_byte,
      download_strategy,
      decryption_key,
      target_size,
  )

  try:
    storage_retry_util.retryer(
        target=bidi_downloader.download_chunk,
        should_retry_if=_should_retry_bidi,
    )
  except (download.BidiDownloadIncompleteError, retry.MaxRetrialsException):
    # Retries exhausted.
    pass
  return (
      bidi_downloader.processed_bytes,
      bidi_downloader.destination_pipe_is_broken,
  )
