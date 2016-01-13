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


def ForceParamEquality(param, resources, resolver=None):
  """Ensure that a set of resources all have the same value for a paramter.

  After this function is called, every resource will have the same value for the
  parameter. That value will be None if no resource had the parameter already
  set. If any had the value set, they will all have that value, and if there is
  disagreement an exception will be raised.

  Args:
    param: str, The name of the parameter that is being forced to equalize.
    resources: [Resource], A list of the resources that need to be in agreement.
    resolver: str or func->str, There is no value set in any resources and this
        resolver is provided, use the resolver to figure out the value.

  Raises:
     InconsistentArgumentError: If one or more resources has the parameter set
         and there is disagreement.
  """

  all_values = set()
  for resource in resources:
    r_value = getattr(resource, param)
    if r_value:
      all_values.add(r_value)
  if len(all_values) > 1:
    raise InconsistentArgumentError(param, list(all_values))
  if all_values:
    value = all_values.pop()
  else:
    value = resolver() if callable(resolver) else resolver
  if value:
    for resource in resources:
      setattr(resource, param, value)
