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

import abc
import contextlib
import random
import string
import tempfile
import time
from typing import Dict, List

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils


class DiagnosticIgnorableError(errors.Error):
  """Ignorable Exception thrown during the diagnostic execution."""


class Diagnostic(abc.ABC):
  """Base class for storage diagnostics.

  This class provides a framework for writing diagnostics. Subclasses can
  override the pre-processing, diagnostic and post-processing steps as needed.
  The execute method is the entry point for running the diagnostic.
  """

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
    try:
      self._pre_process()
      self._run()
    # TODO(b/338905869): Add support to optionaly suppress the exception.
    except DiagnosticIgnorableError as e:
      log.error('Diagnostic execution failed: {}'.format(e))
    finally:
      self._post_process()

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
