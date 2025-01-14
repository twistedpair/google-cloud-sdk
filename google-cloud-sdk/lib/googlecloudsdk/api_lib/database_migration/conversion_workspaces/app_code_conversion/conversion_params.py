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
"""Application code conversion parameters."""

import dataclasses
import os
from typing import Optional

from googlecloudsdk.calliope import exceptions


@dataclasses.dataclass(frozen=True)
class ApplicationCodeConversionParams:
  """Parameters for the application code converter.

  Attributes:
    name: str, the name of the conversion workspace.
    source_dialect: Optional[str], the source dialect of the application code to
      be converted.
    target_dialect: Optional[str], the target dialect of the application code to
      be converted.
    source_folder: Optional[str], the source folder of the application code to
      be converted.
    target_path: Optional[str], the target path of the application code to be
      converted.
    source_file: Optional[str], the source file of the application code to be
      converted.
  """

  name: str
  source_dialect: Optional[str]
  target_dialect: Optional[str]
  source_folder: Optional[str]
  target_path: Optional[str]
  source_file: Optional[str]

  def Validate(self) -> None:
    """Validates the parameters for the application code converter.

    Raises:
      exceptions.BadArgumentException: if the parameters are invalid.
    """
    self._ValidateDialects()
    self._ValidateDirectories()

  def _ValidateDialects(self) -> None:
    """Validates the dialects specified by the user exist.

    Currently, only ORACLE -> POSTGRESQL conversions are supported.

    Raises:
      exceptions.BadArgumentException: if the specified source or target
      dialects are not supported.
    """
    if self.target_dialect and self.target_dialect.upper() != 'POSTGRESQL':
      raise exceptions.BadArgumentException(
          '--target-dialect',
          f'specified target dialect [{self.target_dialect}] is not'
          ' supported. Only POSTGRESQL is supported',
      )

    if self.source_dialect and self.source_dialect.upper() != 'ORACLE':
      raise exceptions.BadArgumentException(
          '--source-dialect',
          f'specified source dialect [{self.source_dialect}] is not'
          ' supported. Only ORACLE is supported',
      )

  def _ValidateDirectories(self) -> None:
    """Validates the directories specified by the user exist.

    if a specific source file is provided, the source directory is not
    required.

    Raises:
      exceptions.BadArgumentException: if the source directory or target
      directory does not exist.
    """

    if self.source_file and self.source_folder:
      raise exceptions.BadArgumentException(
          '--source-file',
          f'specified source file [{self.source_file}] while source'
          f' folder [{self.source_folder}] is also specified.',
      )

    if not (self.source_file or self.source_folder):
      raise exceptions.BadArgumentException(
          '--source-folder',
          'at least one of --source-file or --source-folder must be specified',
      )

    if not self.source_file:
      # source_dir must be specified, validate it exists
      if not os.path.isdir(self.source_folder):
        raise exceptions.BadArgumentException(
            '--source-folder',
            'specified source folder [{}] is not a directory.'.format(
                self.source_folder,
            ),
        )

      # If target_dir is specified, it must be a directory as the
      # source is a directory.
      if self.target_path and not os.path.isdir(self.target_path):
        raise exceptions.BadArgumentException(
            '--target-path',
            'specified target path [{}] is not a directory while source folder'
            ' is specified.'.format(self.target_path),
        )
