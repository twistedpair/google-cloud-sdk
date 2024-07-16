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
import contextlib
import dataclasses
import io
import os
import random
import string
import tempfile
import time
from typing import Dict, List, Tuple

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils

_THREAD_COUNT_ENV_VAR = 'CLOUDSDK_STORAGE_THREAD_COUNT'
_PROCESS_COUNT_ENV_VAR = 'CLOUDSDK_STORAGE_PROCESS_COUNT'
# Placeholder value for metrics that are not available or cannot be calculated.
PLACEHOLDER_METRIC_VALUE = 'N/A'


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

  @property
  @abc.abstractmethod
  def name(self) -> str:
    """The name of the diagnostic."""
    pass

  @abc.abstractmethod
  def _pre_process(self):
    """Pre-processing step for the diagnostic.

    This method is called before the diagnostic is run. Implementing child
    classes can override this method to perform actions necessary for
    running diagnostics like file creation, setting configurations etc.
    """
    pass

  @abc.abstractmethod
  def _run(self):
    """Runs the diagnostic.

    This method is called after the pre-processing step and is expected to
    perform the actual diagnostic.
    """
    pass

  @abc.abstractmethod
  def _post_process(self):
    """Post-processing step for the diagnostic.

    This method is called after the diagnostic is run. Implemeneting child
    classes can override this method to perform clean up actions, aggregating
    metrics, etc.
    """
    pass

  def execute(self):
    """Executes the diagnostic."""
    log.status.Print(f'Running diagnostic: {self.name}...')
    try:
      self._pre_process()
      self._run()
    # TODO(b/338905869): Add support to optionaly suppress the exception.
    except DiagnosticIgnorableError as e:
      log.error(f'{self.name} Diagnostic execution failed: {e}')
    finally:
      self._post_process()
    log.status.Print(f'Finished running diagnostic: {self.name}')

  @contextlib.contextmanager
  def _time_recorder(self, key: str, result: Dict[str, float]) -> None:
    """Records the time it takes to run a block of code.

    Args:
      key: The key to use in the result dictionary.
      result: The dictionary to store the result in.

    Yields:
      None
    """
    t0 = time.time()
    yield
    t1 = time.time()
    result[key] = t1 - t0

  def _create_test_files(
      self, object_sizes: List[int], file_prefix: string
  ) -> bool:
    """Creates test files in a temporary directory.

    Args:
      object_sizes: The size of each object to create.
      file_prefix: The prefix to use for the file names.

    Returns:
      True if the files were created successfully, False otherwise.
    """
    object_count = len(object_sizes)

    try:
      self.temp_dir = file_utils.TemporaryDirectory()
      log.status.Print(
          'Creating {} test files in {}'.format(
              object_count, self.temp_dir.path
          )
      )
      for i in range(object_count):
        with tempfile.NamedTemporaryFile(
            dir=self.temp_dir.path,
            prefix=file_prefix,
            delete=False,
            mode='w+t',
            encoding='utf-8',
        ) as f:
          f.write(self._generate_random_string(object_sizes[i]))
        self._files.append(f.name)

      log.status.Print(
          'Finished creating {} test files in {}'.format(
              object_count, self.temp_dir.path
          )
      )
      return True
    except (OSError, EnvironmentError) as e:
      log.warning('Failed to create test files: {}'.format(e))
    return False

  def _set_env_variable(self, variable_name: str, variable_value: any):
    """Sets the environment variable to the given value.

    Args:
      variable_name: Name of the environment variable.
      variable_value: Value of the environment variable.
    """
    os.environ[variable_name] = str(variable_value)

  def _run_gcloud(self, args: List[str], in_str=None) -> Tuple[str, str]:
    """Runs a gcloud command.

    Args:
      args: The arguments to pass to the gcloud command.
      in_str: The input to pass to the gcloud command.

    Returns:
      A tuple containing the stdout and stderr of the command.
    """
    command = execution_utils.ArgsForGcloud()
    command.extend(args)
    out = io.StringIO()
    err = io.StringIO()

    returncode = execution_utils.Exec(
        command,
        no_exit=True,
        out_func=out.write,
        err_func=err.write,
        in_str=in_str,
    )

    if returncode != 0 and not err.getvalue():
      err.write('gcloud exited with return code {}'.format(returncode))
    return (
        out.getvalue() if returncode == 0 else None,
        err.getvalue() if returncode != 0 else None,
    )

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
        '--log-http',
    ]
    output, err = self._run_gcloud(args, in_str=in_str)
    del output  # unused
    if err:
      raise DiagnosticIgnorableError(
          'Failed to copy objects from source {} to {} : {}'.format(
              source_url, destination_url, err
          )
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
