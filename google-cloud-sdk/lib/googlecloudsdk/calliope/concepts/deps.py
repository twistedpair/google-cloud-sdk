# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Classes to handle dependencies for concepts.

At runtime, resources can be parsed and initialized using the information given
in the Deps object. All the information given by the user in the command line is
available in the Deps object. It may also access other information (such as
information provided by the user during a prompt or properties that are changed
during runtime before the Deps object is used) when Get() is called for a given
attribute, depending on the fallthroughs.
"""

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


class Error(exceptions.Error):
  """Base exception type for this module."""


class FallthroughNotFoundError(Error):
  """Raised when an attribute value is not found by a Fallthrough object."""


class AttributeNotFoundError(Error, AttributeError):
  """Raised when an attribute value cannot be found by a Deps object."""


class Fallthrough(object):
  """Represents a way to get information about a concept's attribute.

  Fallthrough objects have a simple interface, both of which must be
  implemented in subclasses.

    GetValue():
      Get a value from information given to the fallthrough.

    @property
    hint:
      A string message informing the user how to give information accessible to
      the fallthrough, such as setting a property or a command-line flag.

  GetValue() is used by the Deps object to attempt to find the value of an
  attribute. The hint property is used to provide an informative error when an
  attribute can't be found.
  """

  def GetValue(self):
    """Gets a value from information given to the fallthrough.

    Raises:
      FallthroughNotFoundError, if the attribute is not found.
    """
    raise NotImplementedError

  @property
  def hint(self):
    """String representation of the fallthrough for user-facing messaging.
    """
    raise NotImplementedError


class PropertyFallthrough(Fallthrough):
  """Gets an attribute from a property."""

  def __init__(self, prop=None):
    """Initializes a fallthrough for the property associated with the attribute.

    Args:
      prop: googlecloudsdk.core.properties._Property, a property.
    """
    self.property = prop

  def GetValue(self):
    try:
      return self.property.GetOrFail()
    except (properties.InvalidValueError, properties.RequiredPropertyError):
      raise FallthroughNotFoundError

  @property
  def hint(self):
    hint = 'Set the property [{}]'.format(self.property)
    # Special messaging for the project property, which can be modified by the
    # global --project flag.
    if self.property == properties.VALUES.core.project:
      hint += ' or provide the flag [--project] on the command line'
    return hint

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return other.property == self.property


class ArgFallthrough(Fallthrough):
  """Gets an attribute from the argparse parsed values for that arg."""

  def __init__(self, arg_name, arg_value):
    """Initializes a fallthrough for the argument associated with the attribute.

    Args:
      arg_name: str, the name of the flag or positional.
      arg_value: a parsed value (usually string, for resource argument flags)
        provided by argparse.
    """
    self.arg_name = arg_name
    self.arg_value = arg_value

  def GetValue(self):
    if self.arg_value:
      return self.arg_value
    raise FallthroughNotFoundError

  @property
  def hint(self):
    return 'Provide the flag [{}] on the command line'.format(self.arg_name)

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return (other.arg_name == self.arg_name
            and other.arg_value == self.arg_value)


class Deps(object):
  """Gets the values for attributes of a resource.

  Stores information about how to look up each attribute name with a series of
  fallthroughs, starting with the arg name that corresponds to that attribute.

  Attributes:
    attribute_to_fallthroughs_map: a map from attribute names to lists of
      fallthroughs.
  """

  def __init__(self, attribute_to_fallthroughs_map):
    """Initializes dependencies.

    The deps object stores a list from attributes to their fallthroughs,
    including the "primary" fallthrough (usually the attribute arg name).

    Args:
      attribute_to_fallthroughs_map: a map from attribute names to lists of
      fallthroughs.
    """
    self.attribute_to_fallthroughs_map = attribute_to_fallthroughs_map

  def Get(self, attribute):
    """Gets the value of an attribute based on fallthrough information.

    If the attribute value is not provided by any of the fallthroughs, an
    InitializeError is raised with a list of ways to provide information about
    the attribute.

    Args:
      attribute: (str), the name of the desired attribute.

    Returns:
      the value of the attribute (usually a string for resources).

    Raises:
      AttributeNotFoundError: if the fallthroughs cannot provide a value for the
        attribute.
    """
    fallthroughs = self.attribute_to_fallthroughs_map.get(attribute, [])
    for fallthrough in fallthroughs:
      try:
        return fallthrough.GetValue()
      except FallthroughNotFoundError:
        continue
    fallthroughs_summary = '\n'.join(
        ['- {}'.format(fallthrough.hint) for fallthrough in fallthroughs])
    raise AttributeNotFoundError(
        'Failed to find attribute [{}]. The attribute can be set in the '
        'following ways: \n'
        '{}'.format(attribute, fallthroughs_summary))

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return (other.attribute_to_fallthroughs_map ==
            self.attribute_to_fallthroughs_map)
