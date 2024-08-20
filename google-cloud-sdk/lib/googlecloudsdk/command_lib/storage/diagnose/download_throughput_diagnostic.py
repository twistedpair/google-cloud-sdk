# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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

"""Download Throughput Diagnostic."""


from __future__ import annotations

import enum
import math
from typing import List
import uuid

from googlecloudsdk.command_lib.storage import optimize_parameters_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import scaled_integer


_DEFAULT_OBJECT_COUNT = 5
_DEFAULT_OBJECT_SIZE = 1024 * 1024
_SLICED_OBJECT_DOWNLOAD_COMPONENT_SIZE_ENV_VAR = (
    'CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_COMPONENT_SIZE'
)
_SLICED_OBJECT_DOWNLOAD_THRESHOLD_ENV_VAR = (
    'CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_THRESHOLD'
)
_DOWNLOAD_THROUGHPUT_RESULT_KEY = 'download_throughput'
_DIAGNOSTIC_NAME = 'Download Throughput Diagnostic'
_STREAMING_DOWNLOAD_DESTINATION = '-'
_STREAMING_DOWNLOAD_PARALLELISM_WARNING = (
    'Process and/or thread count is set but streaming downloads dont'
    ' support parallelism. Ignoring these values.'
)
_METRIC_NAME = 'download throughput'


def _get_payload_description(object_count: int, object_size: int) -> str:
  """Returns the payload description for the given object count and size."""
  return (
      f'Transferred {object_count} objects for a total transfer size of'
      f' {scaled_integer.FormatBinaryNumber(object_size, decimal_places=1)}.'
  )


def _get_formatted_download_throughput(download_throughput: float) -> str:
  """Formats the download throughput to a human readable format."""
  scaled_download_throughput = scaled_integer.FormatBinaryNumber(
      download_throughput, decimal_places=1
  )
  return f'{scaled_download_throughput}/sec'


class DownloadType(enum.Enum):
  """Enum class for specifying download type for diagnostic tests."""

  STREAMING = 'STREAMING'
  SLICED = 'SLICED'
  FILE = 'FILE'


class DownloadThroughputDiagnostic(diagnostic.Diagnostic):
  """Diagnostic to measure download throughput."""

  def __init__(
      self,
      test_bucket_url: storage_url.CloudUrl,
      download_type: DownloadType,
      object_sizes: List[int] = None,
      thread_count: int = None,
      process_count: int = None,
  ):
    """Initializes the download throughput diagnostic.

    Args:
      test_bucket_url: Bucket url to use for the diagnostic.
      download_type: Type of download to use for the diagnostic.
      object_sizes: List of object sizes to use for the diagnostic.
      thread_count: Number of threads to use for the diagnostic.
      process_count: Number of processes to use for the diagnostic.
    """
    self.bucket_url = test_bucket_url
    self._process_count = process_count
    self._thread_count = thread_count
    self._object_sizes = (
        object_sizes
        if object_sizes
        else [_DEFAULT_OBJECT_SIZE] * _DEFAULT_OBJECT_COUNT
    )
    self._object_count = len(self._object_sizes)
    self._download_type = download_type
    self._files = []
    self._old_env_vars = {}
    self.temp_dir = None
    self._download_dir = None
    self._result = {}
    # Make sure the prefix is unique to avoid collisions with other diagnostics
    # and previous runs of this diagnostic.
    self.object_prefix = 'download_throughput_diagnostics_' + str(uuid.uuid4())

  @property
  def name(self) -> str:
    return _DIAGNOSTIC_NAME

  def _pre_process(self):
    """Uploads test files to the bucket."""
    super(DownloadThroughputDiagnostic, self)._pre_process()
    is_done = self._create_test_files(self._object_sizes, self.object_prefix)

    if not is_done:
      raise diagnostic.DiagnosticIgnorableError('Failed to create test files.')

    self._run_cp(
        self.temp_dir.path + '/' + self.object_prefix + '*',
        self.bucket_url.url_string,
    )

  def _set_sliced_download_env_vars(self):
    """Sets the environment variables for sliced downloads."""
    self._set_parallelism_env_vars()
    self._set_env_variable(
        _SLICED_OBJECT_DOWNLOAD_THRESHOLD_ENV_VAR,
        # Setting this property greater than 0 will enable sliced downloads.
        1,
    )
    # Setting component size to make sure that there are more than 1 components
    # for the sliced downloads.
    min_object_size = min(self._object_sizes)
    if min_object_size <= scaled_integer.ParseBinaryInteger(
        optimize_parameters_util.COMPONENT_SIZE
    ):
      optimal_component_size = scaled_integer.FormatBinaryNumber(
          min_object_size / 2, decimal_places=0
      )
      self._set_env_variable(
          _SLICED_OBJECT_DOWNLOAD_COMPONENT_SIZE_ENV_VAR,
          optimal_component_size,
      )

  def _set_cloud_sdk_env_vars(self):
    """Sets the environment variables for the diagnostic depending on the download type."""
    if self._download_type == DownloadType.STREAMING:
      if self._process_count is not None or self._thread_count is not None:
        log.warning(_STREAMING_DOWNLOAD_PARALLELISM_WARNING)
    elif self._download_type == DownloadType.SLICED:
      self._set_sliced_download_env_vars()
    elif self._download_type == DownloadType.FILE:
      self._set_parallelism_env_vars()

  def _run(self):
    """Runs the diagnostic."""
    self._set_cloud_sdk_env_vars()

    if self._download_type == DownloadType.STREAMING:
      log.status.Print(
          f'Starting download of {self._object_count} objects to path :'
          f' {_STREAMING_DOWNLOAD_DESTINATION} with download type: '
          f' {self._download_type.value}'
      )
      with diagnostic.time_recorder(
          _DOWNLOAD_THROUGHPUT_RESULT_KEY, self._result
      ):
        self._run_cp(
            self.bucket_url.url_string + self.object_prefix + '*',
            _STREAMING_DOWNLOAD_DESTINATION,
        )
    elif (
        self._download_type == DownloadType.SLICED
        or self._download_type == DownloadType.FILE
    ):
      self._download_dir = file_utils.TemporaryDirectory()
      log.status.Print(
          f'Starting download of {self._object_count} objects to path :'
          f' {self._download_dir.path} with download type'
          f' {self._download_type.value}'
      )
      with diagnostic.time_recorder(
          _DOWNLOAD_THROUGHPUT_RESULT_KEY, self._result
      ):
        self._run_cp(
            self.bucket_url.url_string + self.object_prefix + '*',
            self._download_dir.path,
        )
    else:
      raise diagnostic.DiagnosticIgnorableError(
          f'Unknown download type: {self._download_type}'
      )

  def _post_process(self):
    super(DownloadThroughputDiagnostic, self)._post_process()
    if self.temp_dir:
      try:
        self.temp_dir.Close()
        log.status.Print('Cleaned up temp files.')
      except OSError as e:
        log.warning(f'{self.name} : Failed to clean up temp files. {e}')
    if self._download_dir:
      try:
        self._download_dir.Close()
        log.status.Print('Cleaned up downloaded files.')
      except OSError as e:
        log.warning(
            f'{self.name} : Failed to clean up temp downloaded files. {e}'
        )
    self._clean_up_objects(self.bucket_url.url_string, self.object_prefix)

  @property
  def result(self) -> diagnostic.DiagnosticResult | None:
    """Returns the summarized result of the diagnostic."""
    if not self._result:
      return None

    download_time = self._result[_DOWNLOAD_THROUGHPUT_RESULT_KEY]
    download_payload_size = sum(self._object_sizes)
    # Handle division by zero case.
    if math.isclose(download_time, 0.0):
      download_throughput = diagnostic.PLACEHOLDER_METRIC_VALUE
    else:
      download_throughput = _get_formatted_download_throughput(
          round(download_payload_size / download_time, 2)
      )

    operation_result = diagnostic.DiagnosticOperationResult(
        name=_METRIC_NAME,
        result=download_throughput,
        payload_description=_get_payload_description(
            self._object_count, download_payload_size
        ),
    )
    return diagnostic.DiagnosticResult(
        name=self.name,
        operation_results=[operation_result],
    )
