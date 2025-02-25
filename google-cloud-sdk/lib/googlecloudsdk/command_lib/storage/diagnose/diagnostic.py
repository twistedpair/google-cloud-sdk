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
"""Classes and utils for Storage diagnostics.

Storage diagnostics are a bunch of tests that can be run to diagnose issues
with the storage system.
"""

from __future__ import annotations

import abc
from collections.abc import MutableMapping
import contextlib
import dataclasses
import io
import os
import random
import string
import tempfile
import time
from typing import Dict, List

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.diagnose import utils
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import files as file_utils

_THREAD_COUNT_ENV_VAR = 'CLOUDSDK_STORAGE_THREAD_COUNT'
_PROCESS_COUNT_ENV_VAR = 'CLOUDSDK_STORAGE_PROCESS_COUNT'
# Placeholder value for metrics that are not available or cannot be calculated.
PLACEHOLDER_METRIC_VALUE = 'N/A'


@contextlib.contextmanager
def time_recorder(key: str, result: MutableMapping[str, float]) -> None:
  """A context manager that records the time it takes to run a block of code.

  Args:
    key: The key to use in the result dictionary.
    result: The dictionary to store the result in. The time taken to run the
      block of code will be stored in this dictionary with the given key.

  Yields:
    None
  """
  t0 = time.time()
  yield
  t1 = time.time()
  result[key] = t1 - t0


class DiagnosticIgnorableError(errors.Error):
  """Ignorable Exception thrown during the diagnostic execution."""


@dataclasses.dataclass
class DiagnosticOperationResult:
  """Result of a operation performed as part of a diagnostic.

  Attributes:
    name: The name of the operation.
    result: The result of the operation.
    payload_description: The description of the payload used for running this
      operation.
  """

  name: str
  result: Dict[any, any]
  payload_description: str | None = None

  def __str__(self) -> str:
    out = io.StringIO()
    out.write('Diagnostic Operation Result\n')
    out.write('Name: {}\n'.format(self.name))
    if self.payload_description:
      out.write('Payload Description: {}\n'.format(self.payload_description))
    out.write('Result: {}\n'.format(self.result))
    return out.getvalue()


@dataclasses.dataclass
class DiagnosticResult:
  """Result of a diagnostic execution.

  Attributes:
    name: The name of the diagnostic.
    operation_results: The results of the operations performed as part of this
      diagnostic.
    metadata: Additional metadata associated with the diagnostic.
  """

  name: str
  operation_results: List[DiagnosticOperationResult]
  metadata: Dict[any, any] | None = None

  def __str__(self) -> str:
    out = io.StringIO()
    out.write('Diagnostic Result\n')
    out.write('Name: {}\n'.format(self.name))
    if self.metadata:
      out.write('Metadata: {}\n'.format(self.metadata))
    out.write('\nOperation Results:\n')
    for operation_result in self.operation_results:
      out.write(str(operation_result) + '\n')
    return out.getvalue()


class Diagnostic(abc.ABC):
  """Base class for storage diagnostics.

  This class provides a framework for writing diagnostics. Subclasses can
  override the pre-processing, diagnostic and post-processing steps as needed.
  The execute method is the entry point for running the diagnostic.
  """

  _old_env_vars = None

  @property
  @abc.abstractmethod
  def name(self) -> str:
    """The name of the diagnostic."""
    pass

  def _pre_process(self):
    """Pre-processing step for the diagnostic.

    This method is called before the diagnostic is run. Implementing child
    classes can override this method to perform actions necessary for
    running diagnostics like file creation, setting configurations etc.
    """
    self._old_env_vars = os.environ.copy()

  @abc.abstractmethod
  def _run(self):
    """Runs the diagnostic.

    This method is called after the pre-processing step and is expected to
    perform the actual diagnostic.
    """
    pass

  def _post_process(self):
    """Post-processing step for the diagnostic.

    This method is called after the diagnostic is run. Implemeneting child
    classes can override this method to perform clean up actions, aggregating
    metrics, etc.
    """
    if self._old_env_vars is not None:
      os.environ = self._old_env_vars

  def execute(self):
    """Executes the diagnostic."""
    log.status.Print(f'Running diagnostic: {self.name}...')
    with execution_utils.RaisesKeyboardInterrupt():
      try:
        self._pre_process()
        self._run()
        # TODO(b/338905869): Add support to optionaly suppress the exception.
      except DiagnosticIgnorableError as e:
        log.error(f'{self.name} Diagnostic execution failed: {e}')
      finally:
        self._post_process()
      log.status.Print(f'Finished running diagnostic: {self.name}')

  def _create_test_files(
      self,
      object_sizes: List[int],
      file_prefix: string,
      chunk_size: int = 1024 * 1024,
  ) -> bool:
    """Creates test files in a temporary directory.

    Args:
      object_sizes: The size of each object to create.
      file_prefix: The prefix to use for the file names.
      chunk_size: The size of each chunk to write to the file.

    Returns:
      True if the files were created successfully, False otherwise.
    """
    object_count = len(object_sizes)

    try:
      self.temp_dir = file_utils.TemporaryDirectory()
      with progress_tracker.ProgressTracker(
          f'Creating {object_count} test files in {self.temp_dir.path}',
          autotick=True,
      ):
        for i in range(object_count):
          with tempfile.NamedTemporaryFile(
              dir=self.temp_dir.path,
              prefix=file_prefix,
              delete=False,
              mode='w+t',
              encoding='utf-8',
          ) as f:
            bytes_remaining = object_sizes[i]
            while bytes_remaining > 0:
              current_chunk_size = min(bytes_remaining, chunk_size)
              f.write(self._generate_random_string(current_chunk_size))
              bytes_remaining -= current_chunk_size
          self._files.append(f.name)
      return True
    except (OSError, EnvironmentError, console_io.OperationCancelledError) as e:
      log.warning('Failed to create test files: {}'.format(e))
    return False

  def _set_env_variable(self, variable_name: str, variable_value: any):
    """Sets the environment variable to the given value.

    Args:
      variable_name: Name of the environment variable.
      variable_value: Value of the environment variable.
    """
    os.environ[variable_name] = str(variable_value)

  def _run_cp(self, source_url: str, destination_url: str, in_str=None):
    """Runs the gcloud cp command.

    Args:
      source_url: Source url for the cp command.
      destination_url: Destination url for the cp command.
      in_str: The input to pass to the gcloud cp command.

    Raises:
      DiagnosticIgnorableError: If the cp command fails.
    """
    args = [
        'storage',
        'cp',
        source_url,
        destination_url,
        '--verbosity=debug',
    ]
    _, err = utils.run_gcloud(args, in_str=in_str)
    if err:
      raise DiagnosticIgnorableError(
          'Failed to copy objects from source {} to {} : {}'.format(
              source_url, destination_url, err
          )
      )

  def _clean_up_objects(self, bucket_url: str, object_prefix: str) -> None:
    """Cleans up objects in the given bucket with the given prefix."""
    args = [
        'storage',
        'rm',
        f'{bucket_url}{object_prefix}*',
    ]
    _, err = utils.run_gcloud(args)
    if err:
      log.warning(
          f'Failed to clean up objects in {bucket_url} with prefix'
          f' {object_prefix} : {err}'
      )

  def _set_parallelism_env_vars(self):
    """Sets the process and thread count environment variables."""
    if self._process_count is not None:
      self._set_env_variable(_PROCESS_COUNT_ENV_VAR, self._process_count)
    if self._thread_count is not None:
      self._set_env_variable(_THREAD_COUNT_ENV_VAR, self._thread_count)

  def _generate_random_string(self, length: int) -> str:
    """Generates a random string of the given length.

    Args:
      length: The length of the string to generate.

    Returns:
      A random string of the given length.
    """
    return ''.join(
        random.choice(string.ascii_letters + string.digits + string.punctuation)
        for _ in range(length)
    )
