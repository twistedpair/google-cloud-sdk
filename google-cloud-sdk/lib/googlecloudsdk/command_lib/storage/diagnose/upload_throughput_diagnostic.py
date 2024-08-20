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
"""Upload Throughput Diagnostic."""

from __future__ import annotations

import enum
import math
from typing import List
import uuid

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.core import log
from googlecloudsdk.core.util import scaled_integer


_DEFAULT_OBJECT_COUNT = 5
_DEFAULT_OBJECT_SIZE = 1024 * 1024
_ENABLE_PARALLEL_COMPOSITE_ENV_VAR = (
    'CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_ENABLED'
)
_PARALLEL_COMPOSITE_UPLOAD_THRESHOLD_ENV_VAR = (
    'CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_THRESHOLD'
)
_PARALLEL_COMPOSITE_UPLOAD_COMPONENT_SIZE_ENV_VAR = (
    'CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_COMPONENT_SIZE'
)
_DEFAULT_PARALLEL_COMPOSITE_UPLOAD_COMPONENT_SIZE = '50M'
_UPLOAD_THROUGHPUT_RESULT_KEY = 'upload_throughput'
_DIAGNOSTIC_NAME = 'Upload Throughput Diagnostic'
_DEFAULT_STREAMING_SIZE = 1024 * 1024
_STREAMING_UPLOAD_SOURCE = '-'
_STREAMING_UPLOAD_PARALLELISM_WARNING = (
    'Process and/or thread count is set but streaming uploads dont'
    ' support parallelism. Ignoring these values.'
)
_METRIC_NAME = 'upload throughput'


def _get_payload_description(object_count: int, object_size: int) -> str:
  """Returns the payload description for the given object count and size."""
  return (
      f'Transferred {object_count} objects for a total transfer size of'
      f' {scaled_integer.FormatBinaryNumber(object_size, decimal_places=1)}.'
  )


def _get_formatted_upload_throughput(upload_throughput: float) -> str:
  """Formats the upload throughput to a human readable format."""
  scaled_upload_throughput = scaled_integer.FormatBinaryNumber(
      upload_throughput, decimal_places=1
  )
  return f'{scaled_upload_throughput}/sec'


class UploadType(enum.Enum):
  """Enum class for specifying upload type for diagnostic tests."""

  PARALLEL_COMPOSITE = 'PARALLEL_COMPOSITE'
  STREAMING = 'STREAMING'
  FILE = 'FILE'


class UploadThroughputDiagnostic(diagnostic.Diagnostic):
  """Upload Throughput Diagnostic."""

  def __init__(
      self,
      test_bucket_url: storage_url.CloudUrl,
      upload_type: UploadType,
      object_sizes: List[int] = None,
      thread_count: int = None,
      process_count: int = None,
  ):
    """Initializes the Upload Throughput Diagnostic.

    Args:
      test_bucket_url: The bucket to upload to.
      upload_type: The type of upload to perform.
      object_sizes: The sizes of the objects to upload.
      thread_count: The number of threads to use for the upload.
      process_count: The number of processes to use for the upload.
    """
    self.bucket_url = test_bucket_url
    self._process_count = process_count
    self._thread_count = thread_count
    self._upload_type = upload_type
    self._files = []
    self._old_env_vars = {}
    self.temp_dir = None
    self._result = {}
    if object_sizes:
      self._object_sizes = object_sizes
    else:
      self._object_sizes = (
          [_DEFAULT_OBJECT_SIZE] * _DEFAULT_OBJECT_COUNT
          if self._upload_type != UploadType.STREAMING
          else [_DEFAULT_STREAMING_SIZE]
      )
    self._object_count = len(self._object_sizes)
    # Make sure the prefix is unique to avoid collisions with other diagnostics
    # and previous runs of this diagnostic.
    self.object_prefix = 'upload_throughput_diagnostics_' + str(uuid.uuid4())

  @property
  def name(self) -> str:
    return _DIAGNOSTIC_NAME

  def _pre_process(self):
    """Prepares the environment for the diagnostic test."""
    super(UploadThroughputDiagnostic, self)._pre_process()
    if self._upload_type == UploadType.STREAMING:
      self.streaming_size = _DEFAULT_STREAMING_SIZE
      if len(self._object_sizes) > 1:
        log.warning(
            'Streaming uploads do not support multiple objects. Ignoring the'
            ' object count and using default size. :'
            f' {_DEFAULT_STREAMING_SIZE}'
        )
      else:
        self.streaming_size = self._object_sizes[0]
      # Do not create test files for streaming uploads.
      return

    if not self._create_test_files(self._object_sizes, self.object_prefix):
      raise diagnostic.DiagnosticIgnorableError('Failed to create test files.')

  def _set_parallel_composite_env_vars(self):
    """Sets the environment variables for parallel composite uploads."""
    self._set_parallelism_env_vars()
    self._set_env_variable(_ENABLE_PARALLEL_COMPOSITE_ENV_VAR, 'true')
    self._set_env_variable(
        _PARALLEL_COMPOSITE_UPLOAD_THRESHOLD_ENV_VAR,
        0,  # Allow all uploads to use parallel composite.
    )
    min_object_size = min(self._object_sizes)
    if min_object_size <= scaled_integer.ParseBinaryInteger(
        _DEFAULT_PARALLEL_COMPOSITE_UPLOAD_COMPONENT_SIZE
    ):
      optimal_component_size = scaled_integer.FormatBinaryNumber(
          min_object_size / 2, decimal_places=0
      )
      self._set_env_variable(
          _PARALLEL_COMPOSITE_UPLOAD_COMPONENT_SIZE_ENV_VAR,
          optimal_component_size,
      )

  def _set_cloud_sdk_env_vars(self):
    """Sets the environment variables for the diagnostic depending on the upload type."""
    if self._upload_type == UploadType.STREAMING:
      if self._process_count is not None or self._thread_count is not None:
        log.warning(_STREAMING_UPLOAD_PARALLELISM_WARNING)
    elif self._upload_type == UploadType.PARALLEL_COMPOSITE:
      self._set_parallel_composite_env_vars()
    elif self._upload_type == UploadType.FILE:
      self._set_parallelism_env_vars()

  def _run(self):
    """Runs the diagnostic test.

    This involves running the gcloud command to upload the files and measuring
    the time it takes to upload the files.
    """
    self._set_cloud_sdk_env_vars()

    if self._upload_type == UploadType.STREAMING:
      with diagnostic.time_recorder(
          _UPLOAD_THROUGHPUT_RESULT_KEY, self._result
      ):
        log.status.Print(
            'Starting streaming upload of {} bytes to : {}'.format(
                self.streaming_size, self.bucket_url
            )
        )
        self._run_cp(
            _STREAMING_UPLOAD_SOURCE,
            self.bucket_url.url_string + self.object_prefix,
            in_str=self._generate_random_string(self.streaming_size),
        )
    elif (
        self._upload_type == UploadType.PARALLEL_COMPOSITE
        or self._upload_type == UploadType.FILE
    ):
      log.status.Print(
          f'Starting upload of {self._object_count} objects to :'
          f' {self.bucket_url} with upload type: {self._upload_type.value}'
      )
      with diagnostic.time_recorder(
          _UPLOAD_THROUGHPUT_RESULT_KEY, self._result
      ):
        self._run_cp(
            self.temp_dir.path + '/' + self.object_prefix + '*',
            self.bucket_url.url_string,
        )
    else:
      raise diagnostic.DiagnosticIgnorableError(
          '{} : Unknown upload type: {}'.format(self.name, self._upload_type)
      )

  def _post_process(self):
    """Restores the environment variables and cleans up temp files."""
    super(UploadThroughputDiagnostic, self)._post_process()
    if self.temp_dir:
      try:
        self.temp_dir.Close()
        log.status.Print('Cleaned up temp files.')
      except OSError as e:
        log.warning(f'{self.name} : Failed to clean up temp files. {e}')
    self._clean_up_objects(self.bucket_url.url_string, self.object_prefix)

  @property
  def result(self) -> diagnostic.DiagnosticResult | None:
    """Returns the summarized result of the diagnostic execution."""
    if not self._result or _UPLOAD_THROUGHPUT_RESULT_KEY not in self._result:
      return None

    upload_time = self._result[_UPLOAD_THROUGHPUT_RESULT_KEY]
    upload_payload_size = sum(self._object_sizes)
    if math.isclose(upload_time, 0.0):
      upload_throughput = diagnostic.PLACEHOLDER_METRIC_VALUE
    else:
      upload_throughput = _get_formatted_upload_throughput(
          round(upload_payload_size / upload_time, 2)
      )

    operation_result = diagnostic.DiagnosticOperationResult(
        name=_METRIC_NAME,
        result=upload_throughput,
        payload_description=_get_payload_description(
            self._object_count, upload_payload_size
        ),
    )
    return diagnostic.DiagnosticResult(
        name=self.name,
        operation_results=[operation_result],
    )
