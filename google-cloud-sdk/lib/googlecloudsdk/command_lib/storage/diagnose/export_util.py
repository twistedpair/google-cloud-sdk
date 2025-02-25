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
"""Utilities for exporting diagnostic results."""

from __future__ import annotations

import datetime
import os
import tarfile
import tempfile
import uuid

from googlecloudsdk.command_lib import info_holder
from googlecloudsdk.command_lib.storage import errors as command_errors
from googlecloudsdk.command_lib.storage.diagnose import diagnostic
from googlecloudsdk.command_lib.storage.diagnose import utils
from googlecloudsdk.core import config
from googlecloudsdk.core import log


def _get_export_bundle_path(destination: str | None) -> str:
  """Returns a unique path for the export bundle."""
  if destination is None:
    destination = config.Paths().logs_dir

  timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
  tarfile_name = f'diagnostic_bundle_{timestamp}_{uuid.uuid4().hex}.tar.gz'
  tarfile_path = os.path.join(destination, tarfile_name)
  return tarfile_path


def _generate_temp_file(content: str) -> str:
  """Generates a temporary file with the given content.

  Args:
    content: The string content to be written to the file.

  Returns:
    The path of the generated file.
  """
  with tempfile.NamedTemporaryFile(
      delete=False,
      mode='w',
  ) as file:
    file.write(content)
  return file.name


def _clean_up_temp_files(temp_files: list[str]) -> None:
  """Cleans up the temporary files."""
  for temp_file in temp_files:
    try:
      if temp_file:
        os.remove(temp_file)
    except (OSError, EnvironmentError) as e:
      log.warning('Failed to clean up temporary file. {}'.format(e))


def export_diagnostic_bundle(
    test_results: list[diagnostic.DiagnosticResult],
    destination: str | None,
) -> str:
  """Exports a diagnostic bundle to the destination file path.

  A diagnostic bundle consists of result of running the diagnose command, output
  of gcloud info command and recent logs.

  Args:
    test_results: List of test results to be included in the bundle.
    destination: The destination file path. If None, the default logs directory
      is used.

  Returns:
    The path of the exported diagnostic bundle.

  Raises:
    command_errors.FatalError: If the export fails.
  """
  tarfile_path = _get_export_bundle_path(destination)

  diagnostic_result_file_name = None
  info_file_name = None
  try:
    with tarfile.open(tarfile_path, 'w:gz') as tar:
      # Add logs.
      tar.add(config.Paths().logs_dir, arcname='gcloud_logs')

      # Add diagnostic results.
      diagnostic_result_content = '\n'.join(
          str(test_result) for test_result in test_results
      )
      diagnostic_result_file_name = _generate_temp_file(
          diagnostic_result_content
      )
      tar.add(
          diagnostic_result_file_name, arcname='storage_diagnostic_results.txt'
      )

      # Add gcloud info anonymized and diagnostic results.
      info_content = str(
          info_holder.InfoHolder(anonymizer=info_holder.Anonymizer())
      )

      stdout, stderr = utils.run_gcloud(['info', '--run-diagnostics'])

      if stdout:
        info_content += stdout
      if stderr:
        info_content += stderr

      info_file_name = _generate_temp_file(info_content)

      tar.add(info_file_name, arcname='gcloud_info.txt')

  except (
      OSError,
      EnvironmentError,
      tarfile.ReadError,
      tarfile.CompressionError,
      tarfile.ExtractError,
  ) as e:
    raise command_errors.FatalError(
        'Failed to export diagnostic bundle at path {}, {}'.format(
            tarfile_path, e
        )
    )

  finally:
    _clean_up_temp_files([diagnostic_result_file_name, info_file_name])

  return tarfile_path
