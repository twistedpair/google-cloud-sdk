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
"""Utilities for Pub/Sub."""

import enum
from typing import Any
from typing import List

from apitools.base.py import encoding
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files
import six


class ErrorCause(enum.Enum):
  LIST = 'list'
  YAML_OR_JSON = 'yaml_or_json'
  UNRECOGNIZED_FIELDS = 'unrecognized_fields'
  MULTIPLE_SMTS_VALIDATE = 'multiple_smts_validate'


class MessageTransformsMissingFileError(exceptions.Error):
  """Error when the message transforms file is missing."""

  def __init__(self, message, path: str):
    super().__init__(message)
    self.path = path


class MessageTransformsEmptyFileError(exceptions.Error):
  """Error when the message transforms file is empty."""

  def __init__(self, path: str, message: str = ''):
    super().__init__(message)
    self.path = path


class MessageTransformsInvalidFormatError(exceptions.Error):
  """Error when the message transforms file has an invalid format."""

  def __init__(self, path: str, error_cause: ErrorCause, message: str = ''):
    super().__init__(message)
    self.path = path
    self.error_cause = error_cause


def GetErrorMessage(err: Exception) -> str:
  """Returns the formatted error string for an error type.

  Args:
    err: Error raised during the GetMessageTransformsFromFile execution.

  Returns:
    Formatted error message as a string.
  """

  if isinstance(err, MessageTransformsMissingFileError):
    return 'Message transforms file [{0}] is missing or does not exist'.format(
        err.path
    )
  elif isinstance(err, MessageTransformsEmptyFileError):
    return 'Empty message transforms file [{0}]'.format(err.path)
  elif isinstance(err, MessageTransformsInvalidFormatError):
    if err.error_cause == ErrorCause.LIST:
      return (
          'Message transforms file [{0}] not properly formatted as a list'
          .format(err.path)
      )
    elif err.error_cause == ErrorCause.YAML_OR_JSON:
      return (
          'Message transforms file [{0}] is not properly formatted in YAML'
          ' or JSON due to [{1}]'.format(err.path, six.text_type(err))
      )
    elif err.error_cause == ErrorCause.MULTIPLE_SMTS_VALIDATE:
      return (
          'Message transform file [{0}] contains a list of message transforms'
          ' instead of a single (1) message transform. Please edit your'
          ' message-transform-file to contain a single element.'.format(
              err.path
          )
      )
    else:
      return (
          'Message transforms file [{0}] contains unrecognized fields: [{1}]'
          .format(err.path, six.text_type(err))
      )
  else:
    return str(err)


def ValidateMessageTransformMessage(message: Any, path: str) -> None:
  """Validate all parsed message from file are valid."""
  errors = encoding.UnrecognizedFieldIter(message)
  unrecognized_field_paths = []
  for edges_to_message, field_names in errors:
    message_field_path = '.'.join(six.text_type(e) for e in edges_to_message)
    for field_name in field_names:
      unrecognized_field_paths.append(
          '{}.{}'.format(message_field_path, field_name)
      )
  if unrecognized_field_paths:
    raise MessageTransformsInvalidFormatError(
        path,
        ErrorCause.UNRECOGNIZED_FIELDS,
        '\n'.join(unrecognized_field_paths),
    )


def GetMessageTransformsFromFile(message, path) -> List[Any]:
  """Reads a YAML or JSON object of type message from local path.

  Args:
    message: The message type to be parsed from the file.
    path: A local path to an object specification in YAML or JSON format.

  Returns:
    List of object of type message, if successful.
  Raises:
    MessageTransformsMissingFileError: If file is missing.
    MessageTransformsEmptyFileError: If file is empty.
    MessageTransformsInvalidFormat: If file's format is invalid.
  """
  try:
    in_text = files.ReadFileContents(path)
  except files.MissingFileError as e:
    raise MessageTransformsMissingFileError(e, path)

  if not in_text:
    raise MessageTransformsEmptyFileError(path=path)

  # Parsing YAML or JSON file
  try:
    # yaml.load() is able to parse YAML and JSON files
    message_transforms = yaml.load(in_text)
    if not isinstance(message_transforms, list):
      raise MessageTransformsInvalidFormatError(
          path=path, error_cause=ErrorCause.LIST
      )
    result = []
    for py_value in message_transforms:
      transform = encoding.PyValueToMessage(message, py_value)
      ValidateMessageTransformMessage(transform, path)
      result.append(transform)
  except (
      TypeError,
      ValueError,
      AttributeError,
      yaml.YAMLParseError,
  ) as e:
    raise MessageTransformsInvalidFormatError(path, ErrorCause.YAML_OR_JSON, e)
  return result


def GetMessageTransformFromFile(message, path) -> Any:
  """Reads a YAML or JSON object of type message from local path.

  Args:
    message: The message type to be parsed from the file.
    path: A local path to an object specification in YAML or JSON format.

  Returns:
    Object of type message, if successful.
  Raises:
    MessageTransformsMissingFileError: If file is missing.
    MessageTransformsEmptyFileError: If file is empty.
    MessageTransformsInvalidFormat: If file's format is invalid.
  """
  try:
    in_text = files.ReadFileContents(path)
  except files.MissingFileError as e:
    raise MessageTransformsMissingFileError(e, path)

  if not in_text:
    raise MessageTransformsEmptyFileError(path=path)

  # Parsing YAML or JSON file
  try:
    # yaml.load() is able to parse YAML and JSON files
    message_transform = yaml.load(in_text)
    if isinstance(message_transform, list):
      if len(message_transform) == 1:
        message_transform = message_transform[0]
      else:
        raise MessageTransformsInvalidFormatError(
            path, ErrorCause.MULTIPLE_SMTS_VALIDATE
        )
    result = encoding.PyValueToMessage(message, message_transform)
    ValidateMessageTransformMessage(result, path)
  except (
      TypeError,
      ValueError,
      AttributeError,
      yaml.YAMLParseError,
  ) as e:
    raise MessageTransformsInvalidFormatError(path, ErrorCause.YAML_OR_JSON, e)
  return result
