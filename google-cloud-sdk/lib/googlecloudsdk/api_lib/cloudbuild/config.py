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
import os
import re

from apitools.base.protorpclite import messages as proto_messages
from apitools.base.py import encoding as apitools_encoding

from googlecloudsdk.core import exceptions
import yaml
import yaml.parser


# These are the variable names currently used for server-side substitutions.
_SERVER_SUBSTITION_VARIABLES = [
    'PROJECT_ID',
    'BUILD_ID',
    'REPO_NAME',
    'BRANCH_NAME',
    'TAG_NAME',
    'REVISION_ID',
    'COMMIT_SHA'
]


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


class ParameterSubstitutionError(exceptions.Error):
  """Indicates user error in templating (either an invalid key or template)."""


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


def _Substitute(template, params):
  r"""Replaces variables in a string according to params.

  Works like environment variable substitution with envsubst, but a little
  simpler (we can't use envsubst because it doesn't come included on Windows):

  - Templates may not contain the string '\$' (reserved for future escaping).
  - Variable names must consist solely of uppercase letters and underscores.
  - No variable name may be a prefix of any other variable name (both provided
    variable names and known server-side substitutions).
  - For every key in params, look for that key preceded by a '$', and in every
    case substitute it with the corresponding value (verbatim). This is done in
    multiple passes, sorted by variable name (length descending, then
    lexically).
  - Unmatched keys (either in the parameter list, or the template) are ignored.

  For example:

  >>> _Substitute('FOO $BAR $BAZ $QUX', {'BAR': 'bar', 'BAZ': 'baz'})
  'FOO bar baz $QUX'

  Args:
    template: str or None, the template to replace params in (or None, in which
      case None is returned).
    params: dict (str->str), The parameter substitutions. Keys may only contain
      uppercase letters and underscores.

  Returns:
    str or None, the given template with the given parameters substituted in.

  Raises:
    ParameterSubstitutionError: if the template is invalid (see main docstring
      body). These should only be shown to internal users.
  """
  if template is None:
    return template
  # First, perform validations.
  if r'\$' in template:
    raise ParameterSubstitutionError(
        r'Template may not contain [\$] (reserved for possible future escape '
        r'sequences): [{}]'.format(template))
  if not params.keys():
    return template

  pattern = re.compile(r'\$({})'.format('|'.join(params.keys())))
  position = 0  # The position in template to start the next $key search.
  processed = []  # Already expanded segments of template.
  while True:
    match = pattern.search(template, position)
    if not match:
      break
    # Accumulate the segment that has no $key references.
    processed.append(template[position:match.start(0)])
    # Extract the key name.
    key = template[match.start(1):match.end(1)]
    # Accumulate the key value and don't process it again.
    processed.append(params[key])
    # Check for more expansions just after $key.
    position = match.end(0)
  # Don't forget the remainder that has no $key references.
  processed.append(template[position:])
  return ''.join(processed)


def _PerformParameterSubstitution(build, params):
  """Performs variable substitution on build with the parameters in params.

  See _Substitute docs for details. Only performed on certain subfields of the
  Build message.

  The output of this gets passed to the server, which does another pass with a
  restricted set of variables. The spec (outlined in _Substitute) aims to be
  compatible both with the server and future iterations.

  Args:
    build: cloudbuild_v1_messages.Build message. The data to template. It will
      be modified.
    params: dict (str->str). The parameter substitutions
      ({variable name: replacement value}).

  Raises:
    ParameterSubstitutionError: if any of the keys in `params` is invalid (see
      main docstring body). These should only be shown to internal users.
  """
  # Perform all of the validation of key names up-front, rather than for each
  # field.
  for key in params:
    if not re.match('^_[A-Z_]+$', key, re.MULTILINE):
      raise ParameterSubstitutionError(
          'Key [{}] may only contain uppercase letters and underscores, and '
          'must begin with an underscore.'.format(key))
    if key in _SERVER_SUBSTITION_VARIABLES:
      raise ParameterSubstitutionError(
          'Key [{}] is a known server-side substitution and may not be '
          'specified in the client.'.format(key))
  # Check for the condition where one key is a prefix of another. Sorting and
  # checking adjacent is okay here since lexical sorting puts any prefix of an
  # element next to that element.
  all_keys = sorted(params.keys() + _SERVER_SUBSTITION_VARIABLES)
  for prev, curr in zip(all_keys, all_keys[1:]):
    if curr.startswith(prev):
      raise ParameterSubstitutionError(
          'Key [{}] is a prefix of key [{}], which is not permitted.'.format(
              prev, curr))

  # The server only does this substitution for 'steps' and certain subfields of
  # 'images'; we want to match this behavior.
  build.images = [_Substitute(i, params) for i in build.images]
  for step in build.steps:
    step.args = [_Substitute(a, params) for a in step.args]
    step.dir = _Substitute(step.dir, params)
    step.env = [_Substitute(e, params) for e in step.env]


def LoadCloudbuildConfig(path, messages, params=None):
  """Load a cloudbuild config file into a Build message.

  Args:
    path: str, The path to a JSON or YAML file to be decoded.
    messages: module, The messages module that has a Build type.
    params: dict, parameters to substitute into a templated YAML file. This
        feature should only be consumed internally and not exposed directly to
        users until the format is fully specced out. See docstring for
        _Substitute for details.

  Raises:
    NotFoundException: If the file does not exist.
    ParserError: If there was a problem parsing the file.
    BadConfigException: If the config file has illegal values.

  Returns:
    Build message, The build that got decoded.
  """
  if not os.path.exists(path):
    raise NotFoundException(path)

  # Turn the data into a dict
  try:
    with open(path) as f:
      structured_data = yaml.safe_load(f)
    if not isinstance(structured_data, dict):
      raise ParserError(path, 'Could not parse into a message.')
  except yaml.parser.ParserError as pe:
    raise ParserError(path, pe)
  except EnvironmentError:
    # EnvironmentError is parent of IOError, OSError and WindowsError.
    # Raised when file does not exist or can't be opened/read.
    raise FileReadException(path)

  # Then, turn the dict into a proto message.
  try:
    build = _UnpackCheckUnused(structured_data, messages.Build)
  except ValueError as e:
    raise BadConfigException(path, '%s' % e)

  # Substitute in parameters, if given. For now, only internal users may use
  # these substitutions.
  if params:
    # The server will take another pass at the build message after this; the
    # substitution logic was chosen to be compatible.
    _PerformParameterSubstitution(build, params)

  # Some problems can be caught before talking to the cloudbuild service.
  if build.source:
    raise BadConfigException(path, 'config cannot specify source')
  if not build.steps:
    raise BadConfigException(path, 'config must list at least one step')

  return build
