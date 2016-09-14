# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Parse cloudbuild config files.

"""

import json
import os.path

from apitools.base.protorpclite import messages as proto_messages
from apitools.base.py import encoding as apitools_encoding

from googlecloudsdk.core import exceptions
import yaml
import yaml.parser


class UnsupportedEncodingException(exceptions.Error):

  def __init__(self, path, encoding):
    msg = ('{path} has unsupported encoding type "{encoding}". Must be ".json" '
           'or ".yaml".').format(
               path=path,
               encoding=encoding)
    super(UnsupportedEncodingException, self).__init__(msg)


class NotFoundException(exceptions.Error):

  def __init__(self, path):
    msg = '{path} could not be found'.format(
        path=path,
    )
    super(NotFoundException, self).__init__(msg)


class FileReadException(exceptions.Error):

  def __init__(self, path):
    msg = '{path} could not be read'.format(
        path=path,
    )
    # TODO(user): Add a test to confirm that we get this exception when
    # expected.
    super(FileReadException, self).__init__(msg)


class ParserError(exceptions.Error):

  def __init__(self, path, msg):
    msg = 'parsing {path}: {msg}'.format(
        path=path,
        msg=msg,
    )
    super(ParserError, self).__init__(msg)


class BadConfigException(exceptions.Error):

  def __init__(self, path, msg):
    msg = '{path}: {msg}'.format(
        path=path,
        msg=msg,
    )
    super(BadConfigException, self).__init__(msg)


def _UnpackCheckUnused(obj, msg_type):
  """Stuff a dict into a proto message, and fail if there are unused values.

  Args:
    obj: dict(), The structured data to be reflected into the message type.
    msg_type: type, The proto message type.

  Raises:
    ValueError: If there is an unused value in obj.

  Returns:
    Proto message, The message that was created from obj.
  """
  msg = apitools_encoding.DictToMessage(obj, msg_type)

  def _CheckForUnusedFields(obj):
    """Check for any unused fields in nested messages or lists."""
    if isinstance(obj, proto_messages.Message):
      unused_fields = obj.all_unrecognized_fields()
      if unused_fields:
        if len(unused_fields) > 1:
          # Because this message shows up in a dotted path, use braces.
          # eg .foo.bar.{x,y,z}
          unused_msg = '{%s}' % ','.join(sorted(unused_fields))
        else:
          # For single items, omit the braces.
          # eg .foo.bar.x
          unused_msg = unused_fields[0]
        raise ValueError('.%s: unused' % unused_msg)
      for used_field in obj.all_fields():
        try:
          field = getattr(obj, used_field.name)
          _CheckForUnusedFields(field)
        except ValueError as e:
          raise ValueError('.%s%s' % (used_field.name, e))
    if isinstance(obj, list):
      for i, item in enumerate(obj):
        try:
          _CheckForUnusedFields(item)
        except ValueError as e:
          raise ValueError('[%d]%s' % (i, e))

  _CheckForUnusedFields(msg)

  return msg


def LoadCloudbuildConfig(path, messages):
  """Load a cloudbuild config file into a Build message.

  Args:
    path: str, The path to a JSON or YAML file to be decoded. The file
        extension (.json or .yaml) indicates which encoding will be used.
    messages: module, The messages module that has a Build type.

  Raises:
    UnsupportedEncodingException: If the file type is not one of the supported
        encodings.
    NotFoundException: If the file does not exist.
    ParserError: If there was a problem parsing the file.
    BadConfigException: If the config file has illegal values.

  Returns:
    Build message, The build that got decoded.
  """
  if not os.path.exists(path):
    raise NotFoundException(path)

  _, ext = os.path.splitext(path)
  ext = ext.lower()

  # First, turn the file into a dict.
  if ext == '.json':
    try:
      structured_data = json.load(open(path))
    except ValueError as ve:
      raise ParserError(path, ve)
    except EnvironmentError:
      # EnvironmentError is parent of IOError, OSError and WindowsError.
      # Raised when file does not exist or can't be opened/read.
      raise FileReadException(path)
  elif ext == '.yaml':
    try:
      structured_data = yaml.load(open(path))
    except yaml.parser.ParserError as pe:
      raise ParserError(path, pe)
    except EnvironmentError:
      # EnvironmentError is parent of IOError, OSError and WindowsError.
      # Raised when file does not exist or can't be opened/read.
      raise FileReadException(path)
  else:
    raise UnsupportedEncodingException(path, ext)

  # Then, turn the dict into a proto message.
  try:
    build = _UnpackCheckUnused(structured_data, messages.Build)
  except ValueError as e:
    raise BadConfigException(path, '%s' % e)

  # Some problems can be caught before talking to the cloudbuild service.
  if build.source:
    raise BadConfigException(path, 'config cannot specify source')
  if not build.steps:
    raise BadConfigException(path, 'config must list at least one step')

  return build
