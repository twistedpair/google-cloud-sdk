# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Resolvers for resource parameters."""

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Errors for this module."""


class InconsistentArgumentError(Error):

  def __init__(self, param, values):
    super(InconsistentArgumentError, self).__init__(
        'got multiple values for [{param}]: {values}'.format(
            param=param,
            values=', '.join(values)))


class UnsetArgumentError(Error):

  def __init__(self, visible_name):
    super(UnsetArgumentError, self).__init__(
        'resource is ambiguous, try specifying [{name}]'.format(
            name=visible_name))


def FromProperty(prop):
  """Get a default value from a property.

  Args:
    prop: properties._Property, The property to fetch.

  Returns:
    A niladic function that fetches the property.
  """
  def DefaultFunc():
    return prop.Get(required=True)
  return DefaultFunc


def FromArgument(visible_name, value):
  """Infer a parameter from a flag, or explain what's wrong.

  Args:
    visible_name: str, The flag as it would be typed by the user. eg, '--zone'.
    value: The value of that flag taken from the command-line arguments.

  Returns:
    A niladic function that returns the value.
  """
  def DefaultFunc():
    if value is None:
      raise UnsetArgumentError(visible_name)
    return value
  return DefaultFunc
