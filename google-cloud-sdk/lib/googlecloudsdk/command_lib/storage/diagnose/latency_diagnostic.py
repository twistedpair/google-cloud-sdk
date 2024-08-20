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

"""Latency Diagnostic."""

import math
import os
from typing import List
import uuid

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import statistics_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import scaled_integer

# Default object size of 0B, 1KB, 100KB, and 1MB.
_DEFAULT_OBJECT_SIZES = [0, 1024, 100 * 1024, 1024 * 1024]
_ITERATION_COUNT = 5
_UPLOAD_OPERATION_TITLE = 'upload'
_DOWNLOAD_OPERATION_TITLE = 'download'
_DELETE_OPERATION_TITLE = 'delete'
_METADATA_OPERATION_TITLE = 'metadata'

_MEAN_TITLE = 'Mean'
_STANDARD_DEVIATION_TITLE = 'Standard deviation'
_PERCENTILE_90TH_TITLE = '90th percentile'
_PERCENTILE_50TH_TITLE = '50th percentile'
_DIAGNOSTIC_NAME = 'Latency Diagnostic'


def _format_as_milliseconds(time_in_seconds: float) -> str:
  """Formats a time in seconds as milliseconds."""
  time_in_milliseconds = time_in_seconds * 1000
  return f'{time_in_milliseconds:.2f}ms'


def _get_payload_description(object_size: int, object_number: int) -> str:
  """Returns the payload description for the given object size and number."""
  scaled_object_size = scaled_integer.FormatInteger(object_size)
  return f'object size {scaled_object_size} at index [{object_number}]'


class LatencyDiagnostic(diagnostic.Diagnostic):
  """Diagnostic to measure the latency of various operations.

  This diagnostic test will upload, download, and delete objects of different
  sizes and record the latency of each operation.
  """

  def __init__(
      self,
      test_bucket_url: storage_url.CloudUrl,
      object_sizes: List[int] = None,
  ):
    self.object_sizes = object_sizes if object_sizes else _DEFAULT_OBJECT_SIZES
    self.object_count = len(self.object_sizes)
    self.bucket_url = test_bucket_url
    self.temp_dir = None
    self._files = []
    self._api_client = api_factory.get_api(self.bucket_url.scheme)
    # Dummy file buffer to use for downloading that goes nowhere.
    self._discard_sink = DummyFile()
    # A dictionary which stores the latency data of each operation.
    # _result = {'upload': {'0Kb' : 'iteration1' : values}}
    self._result = {}
    # Make sure the prefix is unique to avoid collisions with other diagnostics
    # and previous runs of this diagnostic.
    self.object_prefix = 'latency_diagnostics_' + str(uuid.uuid4())
    self._should_clean_up_objects = False

  @property
  def name(self) -> str:
    return _DIAGNOSTIC_NAME

  def _pre_process(self):
    """Creates the test files to be used in the diagnostic."""
    is_done = self._create_test_files(self.object_sizes, self.object_prefix)

    if not is_done:
      raise diagnostic.DiagnosticIgnorableError('Failed to create test files.')

  def _create_result_entry(
      self, operation_title: str, object_number: int
  ) -> None:
    """Creates an entry in the result dictionary for the given operation.

    Args:
      operation_title: The title of the operation.
      object_number: The number of the object being operated on.
    """
    if not self._result.get(operation_title):
      self._result[operation_title] = {}

    if not self._result[operation_title].get(object_number):
      self._result[operation_title][object_number] = {}

  def _upload_object(
      self, object_number, file_path, object_resource, request_config, iteration
  ) -> None:
    """Uploads an object and records the latency.

    Args:
      object_number: The number of the object being uploaded.
      file_path: The path to the file to upload.
      object_resource: The object resource to upload.
      request_config: The request config to use for the upload.
      iteration: The iteration number of the upload.
    """
    self._create_result_entry(_UPLOAD_OPERATION_TITLE, object_number)

    with diagnostic.time_recorder(
        iteration, self._result[_UPLOAD_OPERATION_TITLE][object_number]
    ):
      with file_utils.FileReader(file_path) as file:
        self._api_client.upload_object(file, object_resource, request_config)

  def _fetch_object_metadata(self, object_number, object_name, iteration):
    """Fetches object metadata and records the latency.

    Args:
      object_number: The number of the object being uploaded.
      object_name: The name of the object to fetch metadata for.
      iteration: The iteration number of the upload.
    """
    self._create_result_entry(_METADATA_OPERATION_TITLE, object_number)

    with diagnostic.time_recorder(
        iteration,
        self._result[_METADATA_OPERATION_TITLE][object_number],
    ):
      self._api_client.get_object_metadata(
          self.bucket_url.bucket_name, object_name
      )

  def _download_object(
      self, object_number, object_resource, request_config, iteration
  ) -> None:
    """Downloads an object and records the latency.

    Args:
      object_number: The number of the object being uploaded.
      object_resource: The object resource to download.
      request_config: The request config to use for the download.
      iteration: The iteration number of the upload.
    """
    self._create_result_entry(_DOWNLOAD_OPERATION_TITLE, object_number)

    with diagnostic.time_recorder(
        iteration, self._result[_DOWNLOAD_OPERATION_TITLE][object_number]
    ):
      self._api_client.download_object(
          object_resource,
          self._discard_sink,
          request_config,
          download_strategy=cloud_api.DownloadStrategy.ONE_SHOT,
      )

  def _delete_object(
      self, object_number, object_url, request_config, iteration
  ) -> None:
    """Deletes an object and records the latency.

    Args:
      object_number: The number of the object being uploaded.
      object_url: The object url to delete.
      request_config: The request config to use for the delete.
      iteration: The iteration number of the upload.
    """
    self._create_result_entry(_DELETE_OPERATION_TITLE, object_number)

    with diagnostic.time_recorder(
        iteration, self._result[_DELETE_OPERATION_TITLE][object_number]
    ):
      self._api_client.delete_object(object_url, request_config)

  def _run(self):
    """Runs the diagnostic.

    Uploads, downloads, and deletes objects of different sizes and records the
    latency of each operation.
    """
    for iteration in range(_ITERATION_COUNT):
      with progress_tracker.ProgressTracker(
          f'Running latency iteration {iteration}'
      ):
        # Run operation for each file and store the results.
        for object_number in range(self.object_count):
          file_path = self._files[object_number]
          file_size = self.object_sizes[object_number]
          # Extract the object name from the file path. Object name is the last
          # part of the file path.
          object_name = file_path.split(os.path.sep)[-1]

          object_url = storage_url.CloudUrl(
              storage_url.ProviderPrefix.GCS,
              self.bucket_url.bucket_name,
              object_name,
          )

          object_resource = resource_reference.ObjectResource(
              object_url, size=file_size
          )
          request_config = request_config_factory.get_request_config(
              object_resource.storage_url,
              content_type=request_config_factory.DEFAULT_CONTENT_TYPE,
              size=file_size,
          )

          try:
            self._upload_object(
                object_number,
                file_path,
                object_resource,
                request_config,
                iteration,
            )
            self._should_clean_up_objects = True
            self._fetch_object_metadata(
                object_number, object_resource.name, iteration
            )
            self._download_object(
                object_number, object_resource, request_config, iteration
            )
            self._delete_object(
                object_number, object_url, request_config, iteration
            )
            # Only clean up objects if delete could not be performed.
            self._should_clean_up_objects = False
          except api_errors.CloudApiError as e:
            raise diagnostic.DiagnosticIgnorableError(
                'Failed to run operation for object'
                f' {object_resource.name}. {e}'
            )

  def _post_process(self):
    if self.temp_dir is not None:
      try:
        self.temp_dir.Close()
      except OSError as e:
        log.warning(f'{self.name} : Failed to clean up temp files. {e}')

      if self._should_clean_up_objects:
        self._clean_up_objects(self.bucket_url.url_string, self.object_prefix)

  @property
  def result(self) -> diagnostic.DiagnosticResult:
    operation_results = []
    for operation_title, object_number_to_latency_dict in self._result.items():
      for object_number in object_number_to_latency_dict.keys():
        trials = self._result[operation_title][object_number].values()
        cumulative_result_dict = {}

        mean = sum(trials) / _ITERATION_COUNT
        cumulative_result_dict[_MEAN_TITLE] = _format_as_milliseconds(mean)

        standard_deviation = (
            math.sqrt(sum((x - mean) ** 2 for x in trials) / len(trials))
            / _ITERATION_COUNT
        )
        cumulative_result_dict[_STANDARD_DEVIATION_TITLE] = (
            _format_as_milliseconds(standard_deviation)
        )

        cumulative_result_dict[_PERCENTILE_50TH_TITLE] = (
            _format_as_milliseconds(
                statistics_util.find_percentile(list(trials), 50)
            )
        )
        cumulative_result_dict[_PERCENTILE_90TH_TITLE] = (
            _format_as_milliseconds(
                statistics_util.find_percentile(list(trials), 90)
            )
        )

        operation_result = diagnostic.DiagnosticOperationResult(
            operation_title,
            cumulative_result_dict,
            payload_description=_get_payload_description(
                self.object_sizes[object_number], object_number
            ),
        )
        operation_results.append(operation_result)

    return diagnostic.DiagnosticResult(self.name, operation_results)


class DummyFile(object):
  """A dummy file-like object that throws away everything written to it."""

  mode = 'bw'

  def write(self, *agrs, **kwargs):
    pass

  def close(self):
    pass
