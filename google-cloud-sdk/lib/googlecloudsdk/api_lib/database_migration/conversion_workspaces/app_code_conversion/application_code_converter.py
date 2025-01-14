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
"""Database Migration Service Application Code Converter."""

import collections
import datetime
import os
from typing import Mapping, Sequence

from googlecloudsdk.api_lib.database_migration.conversion_workspaces import conversion_workspaces_ai_client
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.app_code_conversion import audit_writer
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.app_code_conversion import conversion_params
from googlecloudsdk.api_lib.database_migration.conversion_workspaces.app_code_conversion import conversion_result
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


class ApplicationCodeConverter:
  """Runs Application Code Conversion on a set of files.

  The code conversion is done by calling the Conversion Workspaces AI APIs.

  Attributes:
    params: the parameters for the application code conversion.
    ai_client: the client for the conversion workspaces AI APIs.
  """

  def __init__(
      self,
      params: conversion_params.ApplicationCodeConversionParams,
      ai_client: conversion_workspaces_ai_client.ConversionWorkspacesAIClient,
  ):
    """Initializes the application code converter.

    Args:
      params: the parameters for the application code convertsion.
      ai_client: the client for the conversion workspaces AI APIs.

    Raises:
      exceptions.BadArgumentException: if the provided parameters and invalid.
    """
    self.params = params
    self.params.Validate()
    self.ai_client = ai_client

  @property
  def source_directory_path(self) -> str:
    """The source directory path containing the files to be converted.

    Prioritizes the source_folder parameter if provided.
    If source_file is a directory, it returns source_file. Otherwise, it returns
    the directory containing source_file.

    Returns:
      The source directory path.
    """
    if self.params.source_folder:
      return self.params.source_folder

    if os.path.isdir(self.params.source_file):
      return self.params.source_file

    return os.path.dirname(self.params.source_file)

  @property
  def source_file_paths(self) -> Sequence[str]:
    """The source file paths to be converted.

    If source_file was provided, it is returned as the only source file path.
    Otherwise, all files in the source directory are returned.

    Returns:
      The source file paths.
    """
    if self.params.source_file:
      return [self.params.source_file]
    return sorted([
        os.path.join(self.source_directory_path, filename)
        for filename in os.listdir(self.source_directory_path)
        if os.path.isfile(os.path.join(self.source_directory_path, filename))
    ])

  @property
  def target_directory_path(self) -> str:
    """The target directory path the converted files will be written to.

    If target_path was provided, it is returned. Otherwise,
    source_directory_path is reused as the target directory path.

    Returns:
      The target directory path.
    """
    return self.params.target_path or self.source_directory_path

  def Convert(self) -> None:
    """Converts embedded SQL code in application code (e.g. Java) to PostgreSQL dialect.

    The conversion is done by calling the Conversion Workspaces AI APIs.
    The converted code is written to the target directory path.

    If the target directory path is the same as the source directory path,
    the original source code is saved to a backup file.
    """
    conversion_results: Mapping[conversion_result.ConveresionResult, int] = (
        collections.Counter()
    )

    with audit_writer.AuditWriter(self.source_directory_path) as auditor:
      auditor.WriteAuditLine(audit_line='--------', append_datetime=False)

      for source_filepath in self.source_file_paths:
        if not self._ShouldConvertFile(source_filepath=source_filepath):
          continue

        result = self._ConvertApplicationCodeSingleFile(
            source_filepath=source_filepath,
        )
        conversion_results[result] += 1
        auditor.WriteAuditLine(
            f'File {source_filepath} conversion returned: {result.value}',
        )

      num_convertible_files = sum(conversion_results.values())
      if num_convertible_files == 0:
        auditor.WriteAuditLine('No files found eligible for conversion')

    num_successful_conversions = conversion_results[
        conversion_result.ConveresionResult.SUCCESS
    ]
    log.status.Print(
        f'Sent {num_convertible_files} files for conversion,'
        f' {num_successful_conversions} files were actually converted.',
    )

  def _ShouldConvertFile(self, source_filepath: str) -> bool:
    """Determines if the file should be converted, based on the file name.

    Only Java files are currentlysupported for conversion.

    Args:
      source_filepath: the path of the source file to be converted.

    Returns:
      Whether the file should be converted or skipped.
    """
    if audit_writer.AuditWriter.IsAuditFile(source_filepath):
      return False

    if not source_filepath.endswith('.java'):
      log.status.Print(
          f'Skipping file {source_filepath} since it is not a java file',
      )
      return False

    return True

  def _ConvertApplicationCodeSingleFile(
      self,
      source_filepath: str,
  ) -> conversion_result.ConveresionResult:
    """Converts application code from a source code file.

    The converted code is written to the target directory path.
    If the target directory path is the same as the source directory path,
    the original source code is saved to a backup file.

    Args:
      source_filepath: the path of the source file to be converted.

    Returns:
      the result of the conversion.

    Raises:
      exceptions.BadArgumentException: if the source file does not exist.
    """

    try:
      source_code = files.ReadFileContents(source_filepath)
    except files.MissingFileError:
      raise exceptions.BadArgumentException(
          '--source-file',
          'specified file [{}] does not exist.'.format(source_filepath),
      )

    log.status.Print(f'Sending file {source_filepath} for conversion')
    conversion_response = self.ai_client.ConvertApplicationCode(
        name=self.params.name,
        source_code=source_code,
    )

    if conversion_response.resultMessage:
      log.status.Print(f'Result message: {conversion_response.resultMessage}')

    is_converted_successfully = bool(conversion_response.sourceCode)
    if not is_converted_successfully:
      log.status.Print(f'No changes were made to the file {source_filepath}')
      return conversion_result.ConveresionResult.FAILURE

    target_filepath = self._BuildTargetFilePath(source_filepath)
    if target_filepath == source_filepath:
      self._CreateSourceCodeBackup(
          source_filepath=source_filepath,
          source_code=source_code,
      )
    self._WriteConvertedCode(
        source_filepath=source_filepath,
        target_filepath=target_filepath,
        source_code=conversion_response.sourceCode,
    )
    return conversion_result.ConveresionResult.SUCCESS

  def _BuildTargetFilePath(self, source_filepath: str) -> str:
    """Builds the target file path for the converted file.

    The target file name is the same as the source file name.
    The target directory path is the target_path parameter if provided,
    otherwise, it is the source_directory_path.

    Args:
      source_filepath: the path of the source file to be converted.

    Returns:
      The target file path.
    """
    if not os.path.isdir(self.target_directory_path):
      # Target folder was provided but is a file, and not actually a directory.
      # So that should be returned.
      return self.target_directory_path

    return os.path.join(
        self.target_directory_path,
        os.path.basename(source_filepath),
    )

  def _CreateSourceCodeBackup(
      self,
      source_filepath: str,
      source_code: str,
  ) -> None:
    """Creates a backup file of the source code.

    Backup files are needed when the target file is the same as the source
    file.

    Args:
      source_filepath: the path of the source file to be converted.
      source_code: the source code of the file to be converted.
    """
    datetime_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filepath = f'{source_filepath}_{datetime_str}.bak'
    files.WriteFileContents(backup_filepath, source_code)
    log.status.Print(
        f'The original file content was saved to {backup_filepath}',
    )

  def _WriteConvertedCode(
      self,
      source_filepath: str,
      target_filepath: str,
      source_code: str,
  ) -> None:
    """Writes the converted code to the target file path.

    Args:
      source_filepath: the path of the source file to be converted.
      target_filepath: the path of the target file to be written.
      source_code: the convertedsource code.
    """
    files.WriteFileContents(
        path=target_filepath,
        contents=source_code,
    )
    log.status.Print(
        f'File {source_filepath} was converted and saved in {target_filepath}',
    )
