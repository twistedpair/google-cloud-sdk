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
"""Audit log writer for App Code Conversion."""

import datetime
import os

from googlecloudsdk.core.util import files


class AuditWriter:
  """Audit log writer for App Code Conversion.

  This class wraps the FileWriter method, and adds the ability to
  write audit lines to the audit file.

  It should be used as a context manager like so:
  with AuditWriter(source_folder) as auditor:
    ...
    auditor.WriteAuditLine('....')
    ...

  Attributes:
    file_writer: FileWriter, used to write log lines to the audit file.
  """

  _AUDIT_FILE_NAME = 'Conversion-Audit.txt'
  _DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

  def __init__(self, dir_path: str):
    """Initializes the audit writer.

    Args:
      dir_path: str, the directory path to write the audit file to.
    """
    self.file_writer = files.FileWriter(
        path=os.path.join(dir_path, self._AUDIT_FILE_NAME),
        append=True,
    )

  def __enter__(self):
    """Enters the context manager.

    Opens the audit file for writing.

    Returns:
      self, the audit writer.
    """
    self.file_writer.__enter__()
    return self

  def __exit__(self, ex_type, value, traceback):
    """Exits the context manager.

    Closes the audit file.

    Args:
      ex_type: type, the exception type.
      value: str, the exception value.
      traceback: traceback, the exception traceback.
    """
    self.file_writer.__exit__(ex_type, value, traceback)

  def WriteAuditLine(
      self,
      audit_line: str,
      append_datetime: bool = True,
  ) -> None:
    """Writes an audit line to the audit file.

    Args:
      audit_line: str, the audit line to be written.
      append_datetime: bool, whether to prepend the current datetime to the
        audit line.
    """
    if append_datetime:
      datetime_str = datetime.datetime.now().strftime(self._DATETIME_FORMAT)
      audit_line = f'{datetime_str}: {audit_line}'

    self.file_writer.write(audit_line)
    if not audit_line.endswith('\n'):
      self.file_writer.write('\n')

  @classmethod
  def IsAuditFile(cls, filepath: str) -> bool:
    """Returns whether the file is an audit file.

    Args:
      filepath: str, the file path to check.
    """
    return filepath.endswith(cls._AUDIT_FILE_NAME)
