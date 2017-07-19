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
import base64
import os

from apitools.base.protorpclite import messages as proto_messages
from apitools.base.py import encoding as apitools_encoding

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.core import exceptions
import yaml
import yaml.parser


# Don't apply camel case to keys for dict or list values with these field names.
# These correspond to map fields in our proto message, where we expect keys to
# be sent exactly as the user typed them, without transformation to camelCase.
_SKIP_CAMEL_CASE = ['secretEnv', 'secret_env', 'substitutions']


class NotFoundException(exceptions.Error):

  def __init__(self, path):
    msg = '{path} could not be found'.format(
        path=path or 'Cloud Build configuration',
    )
    super(NotFoundException, self).__init__(msg)


class FileReadException(exceptions.Error):

  def __init__(self, path):
    msg = '{path} could not be read'.format(
        path=path or 'Cloud Build configuration',
    )
    super(FileReadException, self).__init__(msg)


class ParserError(exceptions.Error):

  def __init__(self, path, msg):
    msg = 'parsing {path}: {msg}'.format(
        path=path or 'Cloud Build configuration',
        msg=msg,
    )
    super(ParserError, self).__init__(msg)


class BadConfigException(exceptions.Error):

  def __init__(self, path, msg):
    msg = '{path}: {msg}'.format(
        path=path or 'Cloud Build configuration',
        msg=msg,
    )
    super(BadConfigException, self).__init__(msg)


def _SnakeToCamelString(field_name):
  """Change a snake_case string into a camelCase string.

  Args:
    field_name: str, the string to be transformed.

  Returns:
    str, the transformed string.
  """
  parts = field_name.split('_')
  if not parts:
    return field_name

  # Handle field_name with leading '_'s by collapsing them into the next part.
  # Legit field names will never look like this, but completeness of the
  # function is important.
  leading_blanks = 0
  for p in parts:
    if not p:
      leading_blanks += 1
    else:
      break
  if leading_blanks:
    parts = parts[leading_blanks:]
    if not parts:
      # If they were all blanks, then we over-counted by one because of split
      # behavior.
      return '_'*(leading_blanks-1)
    parts[0] = '_'*leading_blanks + parts[0]

  return ''.join(parts[:1] + [s.capitalize() for s in parts[1:]])


def _SnakeToCamel(msg):
  """Transform all dict field names that are snake_case to camelCase.

  If a field is in _SKIP_CAMEL_CASE then its value is not further transformed.

  Args:
    msg: dict, list, or other. If 'other', the function returns immediately.

  Returns:
    Same type as message, except all field names except "secrets" that were
    snake_case are now camelCase.
  """
  if isinstance(msg, dict):
    return {
        _SnakeToCamelString(key):
        _SnakeToCamel(val) if key not in _SKIP_CAMEL_CASE else val
        for key, val in msg.iteritems()
    }
  elif isinstance(msg, list):
    return [_SnakeToCamel(elem) for elem in msg]
  else:
    return msg


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


def LoadCloudbuildConfigFromStream(stream, messages, params=None,
                                   path=None):
  """Load a cloudbuild config file into a Build message.

  Args:
    stream: file-like object containing the JSON or YAML data to be decoded
    messages: module, The messages module that has a Build type.
    params: dict, parameters to substitute into the Build spec.
    path: str or None. Optional path to be used in error messages.

  Raises:
    NotFoundException: If the file does not exist.
    ParserError: If there was a problem parsing the file.
    BadConfigException: If the config file has illegal values.

  Returns:
    Build message, The build that got decoded.
  """
  # Turn the data into a dict
  try:
    structured_data = yaml.safe_load(stream)
    if not isinstance(structured_data, dict):
      raise ParserError(path, 'Could not parse into a message.')
  except yaml.parser.ParserError as pe:
    raise ParserError(path, pe)

  # Transform snake_case into camelCase.
  structured_data = _SnakeToCamel(structured_data)

  # Then, turn the dict into a proto message.
  try:
    build = _UnpackCheckUnused(structured_data, messages.Build)
  except ValueError as e:
    raise BadConfigException(path, '%s' % e)

  subst = structured_data.get('substitutions', {})
  if params:
    subst.update(params)
  build.substitutions = cloudbuild_util.EncodeSubstitutions(subst, messages)

  # Re-base64-encode secrets[].secretEnv values, which apitools' DictToMessage
  # "helpfully" base64-decodes since it can tell it's a bytes field. We need to
  # send a base64-encoded string in the JSON request, not raw bytes.
  for s in build.secrets:
    for i in s.secretEnv.additionalProperties:
      i.value = base64.b64encode(i.value)

  # Some problems can be caught before talking to the cloudbuild service.
  if build.source:
    raise BadConfigException(path, 'config cannot specify source')
  if not build.steps:
    raise BadConfigException(path, 'config must list at least one step')

  return build


def LoadCloudbuildConfigFromPath(path, messages, params=None):
  """Load a cloudbuild config file into a Build message.

  Args:
    path: str. Path to the JSON or YAML data to be decoded.
    messages: module, The messages module that has a Build type.
    params: dict, parameters to substitute into a templated Build spec.

  Raises:
    NotFoundException: If the file does not exist.
    ParserError: If there was a problem parsing the file.
    BadConfigException: If the config file has illegal values.

  Returns:
    Build message, The build that got decoded.
  """
  if not os.path.exists(path):
    raise NotFoundException(path)

  try:
    with open(path) as f:
      return LoadCloudbuildConfigFromStream(f, messages, params, path=path)
  except EnvironmentError:
    # EnvironmentError is parent of IOError, OSError and WindowsError.
    # Raised when file does not exist or can't be opened/read.
    raise FileReadException(path)
