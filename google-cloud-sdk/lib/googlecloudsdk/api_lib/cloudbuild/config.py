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

import os.path

from apitools.base.py import encoding as apitools_encoding

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
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


def _SubstituteVars(build):
  """Substitute $VARS in text inside a build message.

  $PROJECT_ID gets the core/project property.

  Args:
    build: Build message, The build whose values are translated.

  Returns:
    Build message, The build with translated values.
  """
  replacements = {
      '$PROJECT_ID': properties.VALUES.core.project.Get(),
  }

  def MapValue(v):
    if not v:
      return v
    for pat, val in replacements.iteritems():
      if not val:
        continue
      v = v.replace(pat, val)
    return v

  for step in build.steps:
    step.name = MapValue(step.name)
    step.args = map(MapValue, step.args)
    step.env = map(MapValue, step.env)
    step.dir = MapValue(step.dir)
  build.images = map(MapValue, build.images)

  return build


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

  if ext == '.json':
    json_data = open(path).read()
    try:
      build = apitools_encoding.JsonToMessage(messages.Build, json_data)
    except ValueError as ve:
      raise ParserError(path, ve)
  elif ext == '.yaml':
    try:
      structured_data = yaml.load(open(path))
    except yaml.parser.ParserError as pe:
      raise ParserError(path, pe)
    build = apitools_encoding.DictToMessage(structured_data, messages.Build)
  else:
    raise UnsupportedEncodingException(path, ext)

  # Some problems can be caught before talking to the cloudbuild service.
  if build.source:
    raise BadConfigException(path, 'config cannot specify source')
  if not build.steps:
    raise BadConfigException(path, 'config must list at least one step')

  build = _SubstituteVars(build)

  return build
