# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Validates config file."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import os

from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core import yaml_validator
from googlecloudsdk.core.feature_flags import parse

SCHEMA_PATH = (
    os.path.join(os.path.dirname(__file__), 'feature_flags_config_schema.yaml'))


class ValidationBaseError(Exception):
  """Base class for validation errors.

  Attributes:
    message: str, the error message.
    file_path: the path to the config_file.
    header: str, description of the error, which may include the
      section/property where there is an error.
  """

  def __init__(self, msg, file_path, header):
    self.message = msg
    self.file_path = file_path
    self.header = header
    super(ValidationBaseError, self).__init__(self.message)


class ValidationFailedError(Exception):
  """Validation failed.

  Attributes:
    errors: list, errors to be raised.
  """

  def __init__(self, errors):
    errors_in_config_file = collections.defaultdict(list)
    for error in errors:
      errors_in_config_file[error.file_path].append(error)
    msg_lines = ['']
    num_errors = 0
    for file_path, file_errors in sorted(errors_in_config_file.items()):
      msg_lines.extend(['', file_path])
      errors_by_property = collections.OrderedDict()
      for error in file_errors:
        error_string = str(error)
        if error_string not in errors_by_property:
          errors_by_property[error_string] = []
        errors_by_property[error_string].append(error.header)
      for i, (error_string, header) in enumerate(errors_by_property.items()):
        num_errors += 1
        msg_lines.extend([
            '{}) {}'.format(i + 1, ', '.join(sorted(set(header)))),
            '{}'.format(error_string), ''
        ])

    msg_lines[0] = '{} error(s) found in the Feature Flag Config File!'.format(
        num_errors)

    super(ValidationFailedError, self).__init__('\n'.join(msg_lines))


class InvalidOrderError(ValidationBaseError):
  """Raised when the properties are not in alphabetical order.

  Attributes:
    header: str, general description of the error.
  """

  def __init__(self, file_path, properties_list):
    """Instantiates the InvalidOrderError class.

    Args:
      file_path: path to the config file.
      properties_list: str, list of all properties in the config file.
    """
    msg = ('The properties {properties_list} are not in alphabetical order.'
          ).format(properties_list=properties_list)
    self.header = ('The properties in the Feature Flag Config File '
                   'should be in alphabetical order.')
    super(InvalidOrderError, self).__init__(
        msg=msg, file_path=file_path, header=self.header)


class InvalidSchemaError(ValidationBaseError):
  """Raised when the config file doesnt satisfy the schema.

  Attributes:
    header: str, general description of the error.
  """

  def __init__(self, invalid_schema_reasons, file_path):
    """Instantiates the InvalidSchemaError class.

    Args:
      invalid_schema_reasons: str, list of all reasons why the config file does
        not satisfy the schema.
      file_path: path to the config file.
    """
    schema = 'googlecloudsdk/core/feature_flags/feature_flags_config_schema.yaml'
    msg = ('Config file does not follow schema because:\n{reasons}.'
          ).format(reasons='.\n'.join(invalid_schema_reasons))
    self.header = ('The Feature Flag Config File should match the schema at '
                   '{schema}.').format(schema=schema)
    super(InvalidSchemaError, self).__init__(
        msg=msg, file_path=file_path, header=self.header)


class InvalidValueError(ValidationBaseError):
  """Raised when a value does not follow the property's validator.

  Attributes:
    header: str, general description of the error.
  """

  def __init__(self, property_name, invalid_values, file_path):
    """Instantiates the InvalidValueError class.

    Args:
      property_name: str, the section/property where there is an invalid value.
      invalid_values: str, list of values in the section/property that are
        invalid.
      file_path: path to the config file.
    """
    msg = ('The following values are invalid: {value}').format(
        value=invalid_values)
    self.header = (
        'The Feature Flag Config File\'s values in [{}] should be valid.'
    ).format(property_name)
    super(InvalidValueError, self).__init__(
        msg=msg, file_path=file_path, header=self.header)


class InconsistentValuesError(ValidationBaseError):
  """Raised when the values in a property are not of the same type.

  Attributes:
    header: str, general description of the error.
  """

  def __init__(self, values, property_name, file_path):
    """Instantiates the InconsistentValuesError class.

    Args:
      values: str, list of values in the property with inconsistent values.
      property_name: str, the section/property with inconsistent values.
      file_path: path to the config file.
    """
    msg = ('The value types in [{property_name}] are not consistent.\n'
           'Make the values {values} the same type.').format(
               property_name=property_name, values=values)
    self.header = ('The Feature Flag Config File\'s values in [{}] should be of'
                   ' the same type.').format(property_name)
    super(InconsistentValuesError, self).__init__(
        msg=msg, file_path=file_path, header=self.header)


class Validator(object):
  """A class that checks for the validity of the config file.

  Attributes:
    config_path: str, the path to the configuration file.
    parsed_yaml: dict, the parsed YAML representation of the configuration file.
    list_of_errors: list, the list of all errors from the config file.
  """

  def __init__(self, config_file_path):
    self.parsed_yaml = yaml.load_path(path=config_file_path, round_trip=True)
    self.config_path = config_file_path
    self.list_of_errors = []

  def ValidateAlphabeticalOrder(self):
    """Validates whether the properties in the config file are in alphabetical order.

    If the properties in config file are not in alphabetical order, this method
    adds InvalidOrderError to list_of_errors.
    """
    properties_list = list(self.parsed_yaml.keys())
    if properties_list != sorted(properties_list):
      self.list_of_errors.append(
          InvalidOrderError(
              file_path=self.config_path, properties_list=properties_list))

  def ValidateConfigFile(self):
    """Validates the config file.

    If the config file has any errors, this method compiles them and then
    returns an easy to read sponge log.

    Raises:
      ValidationFailedError: Error raised when validation fails.
    """
    self.ValidateAlphabeticalOrder()
    self.ValidateSchema()
    self.ValidateValueTypes()
    self.ValidateValues()
    if self.list_of_errors:
      raise ValidationFailedError(self.list_of_errors)

  def ValidateSchema(self):
    """Validates the parsed_yaml against JSON schema.

    This method ensures that the config file follows the schema. If the YAML
    data does not match the schema, this method appends InvalidSchemaError to
    list_of_errors.
    """
    schema_errors = []
    list_of_invalid_schema = yaml_validator.Validator(SCHEMA_PATH).Iterate(
        self.parsed_yaml)
    for errors in list_of_invalid_schema:
      schema_errors.append(str(errors.args[0]))
    if schema_errors:
      self.list_of_errors.append(
          InvalidSchemaError(
              invalid_schema_reasons=schema_errors, file_path=self.config_path))

  def ValidateValueTypes(self):
    """Validates the values of each property in the config file.

    This method ensures that the values of each property are of the same type.
    If the values are not of the same type, this method appends
    InconsistentValuesError to list_of_errors.
    """
    for section_property in self.parsed_yaml:
      values_list = parse.FeatureFlagsConfig(
          self.config_path).properties[section_property].values
      first_value_type = type(values_list[0])
      for value in values_list:
        if not isinstance(value, first_value_type):
          self.list_of_errors.append(
              InconsistentValuesError(
                  values=str(values_list),
                  property_name=section_property,
                  file_path=self.config_path))

  def ValidateValues(self):
    """Validates the values of each property in the config file.

    This method ensures that the values of each property correspond to the
    property's validator. If the values dont satisfy the property's validator,
    this method appends InvalidValueError to list_of_errors.
    """
    for section_property in self.parsed_yaml:
      values_list = parse.FeatureFlagsConfig(
          self.config_path).properties[section_property].values
      section_name, property_name = section_property.split('/')
      section_instance = getattr(properties.VALUES, section_name)
      property_instance = getattr(section_instance, property_name)
      list_of_invalid_values = []
      for value in values_list:
        try:
          property_instance.Validate(value)
        except properties.InvalidValueError:
          list_of_invalid_values.append(value)
      if list_of_invalid_values:
        self.list_of_errors.append(
            InvalidValueError(
                property_name=section_property,
                invalid_values=str(list_of_invalid_values),
                file_path=self.config_path))
