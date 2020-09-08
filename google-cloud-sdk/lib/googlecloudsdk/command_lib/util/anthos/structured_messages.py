# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Library for marshalling binary output_messages to/from stdout and stderr."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import datetime
import json
import os


from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core import yaml_validator
import ruamel.yaml as ryaml


SCHEMA_VERSION = '1.0.0'
_SCHEMA_PATH = (os.path.join(os.path.dirname(__file__),
                             'structured_output_schema.yaml'))
_MSG_VALIDATOR = yaml_validator.Validator(_SCHEMA_PATH)

_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


class MessageParsingError(core_exceptions.Error):
  """Error Raised if there is a problem converting to/from OutputMessage."""


class InvalidMessageError(core_exceptions.Error):
  """Error Raised if there an input string is not a valid OutputMessage."""


def ParseAndValidateMessage(input_str):
  """Validate that yaml string or object is a valid OutputMessage."""
  try:
    yaml_object = yaml.load(input_str)
    _MSG_VALIDATOR.Validate(yaml_object)
    _ = datetime.datetime.strptime(yaml_object['timestamp'], _TIMESTAMP_FORMAT)
    return yaml_object
  except (yaml.YAMLParseError, ValueError) as e:
    raise MessageParsingError('Error loading YAML message :: [{}].'.format(e))
  except (yaml_validator.ValidationError, ryaml.error.YAMLStreamError) as ve:
    raise InvalidMessageError(
        'Invalid OutputMessage string [{}] :: [{}]'.format(input_str, ve))


class OutputMessage(object):
  """Class representing a structured output message.

  Attributes:
    body: str, message body
    resource_body: Object, YAML/JSON formatted object containing resource output
    error_details: OutputMessage.ErrorDetail, message error details. Only
      present if OutputMessage.isError() == True.
    version: str, message format version
    timestamp: RFC 3339 encoded timestamp
    as_json: bool, if true default string representation of object will be JSON.
     Default is False, which will render this object as YAML.
  """

  def __init__(self, body, timestamp, version=SCHEMA_VERSION,
               resource_body=None, error_details=None, as_json=False):
    self._body = body
    self._resource_body = resource_body
    if isinstance(error_details, dict):
      err = self.ErrorDetails(error_details.get('error'),
                              error_details.get('context'),
                              as_json)
    else:
      err = None
    self._err = err
    self._version = version
    self._ts = timestamp
    self._as_json = as_json

  class ErrorDetails(object):
    """Data class for ErrorDetail sub-messages."""

    def __init__(self, error_msg, context=None, as_json=False):
      self.error = error_msg
      self.context = context
      self.as_json = as_json

    def AsDict(self):
      out = collections.OrderedDict(error=self.error)
      if self.context:
        out['context'] = self.context
      return out

    def __str__(self):
      if self.as_json:
        return json.dumps(self.AsDict())
      return yaml.dump(self.AsDict(), round_trip=True)

    def __eq__(self, other):
      if not isinstance(other, OutputMessage.ErrorDetails):
        return False
      return self.error == other.error and self.context == other.context

  @property
  def body(self):
    return self._body

  @property
  def resource_body(self):
    return self._resource_body

  @property
  def error_details(self):
    return self._err

  @property
  def version(self):
    return self._version

  @property
  def timestamp(self):
    return self._ts

  def AsDict(self):
    out = collections.OrderedDict(version=self.version,
                                  timestamp=self.timestamp,
                                  body=self.body)
    if self.resource_body:
      out['resource_body'] = self.resource_body
    if self.error_details:
      out['error_details'] = self.error_details.AsDict()
    return out

  def IsError(self):
    return self._err is not None

  def ToJSON(self):
    msg = self.AsDict()
    return json.dumps(msg, sort_keys=True)

  def ToYAML(self):
    msg = self.AsDict()
    return yaml.dump(msg)

  def __str__(self):
    serializer = self.ToJSON if self._as_json else self.ToYAML
    return serializer()

  def __eq__(self, other):
    if not isinstance(other, OutputMessage):
      return False
    return (self.error_details == other.error_details and
            self.body == other.body and
            self.resource_body == other.resource_body and
            self.version == other.version and
            self.timestamp == other.timestamp)

  @classmethod
  def FromString(cls, input_str, as_json=False):
    """Parse a YAML/JSON string into an OutputMessage."""
    yaml_msg = ParseAndValidateMessage(input_str)

    return cls(body=yaml_msg.get('body'),
               resource_body=yaml_msg.get('resource_body'),
               error_details=yaml_msg.get('error_details'),
               version=yaml_msg.get('version'),
               timestamp=yaml_msg.get('timestamp'),
               as_json=as_json)
