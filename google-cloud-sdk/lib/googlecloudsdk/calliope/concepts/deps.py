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

from __future__ import absolute_import
from __future__ import unicode_literals
import abc

from googlecloudsdk.calliope.concepts import util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
import six


class Error(exceptions.Error):
  """Base exception type for this module."""


class FallthroughNotFoundError(Error):
  """Raised when an attribute value is not found by a Fallthrough object."""


class AttributeNotFoundError(Error, AttributeError):
  """Raised when an attribute value cannot be found by a Deps object."""


class _FallthroughBase(six.with_metaclass(abc.ABCMeta, object)):
  """Represents a way to get information about a concept's attribute.

  Specific implementations of Fallthrough objects must implement the method:

    _Call():
      Get a value from information given to the fallthrough.

  GetValue() is used by the Deps object to attempt to find the value of an
  attribute. The hint property is used to provide an informative error when an
  attribute can't be found.
  """

  def __init__(self, hint):
    """Initializes a fallthrough to an arbitrary function.

    Args:
      hint: str, The user-facing message for the fallthrough when it cannot be
        resolved.
    """
    self._hint = hint

  def GetValue(self, parsed_args):
    """Gets a value from information given to the fallthrough.

    Args:
      parsed_args: the argparse namespace.

    Raises:
      FallthroughNotFoundError: If the attribute is not found.

    Returns:
      The value of the attribute.
    """
    value = self._Call(parsed_args)
    if value:
      return value
    raise FallthroughNotFoundError()

  @abc.abstractmethod
  def _Call(self, parsed_args):
    pass

  @property
  def hint(self):
    """String representation of the fallthrough for user-facing messaging."""
    return self._hint


class Fallthrough(_FallthroughBase):
  """A fallthrough that can get an attribute value from an arbitrary function.
  """

  def __init__(self, function, hint):
    """Initializes a fallthrough to an arbitrary function.

    Args:
      function: f() -> value, A no argument function that returns the value of
        the argument or None if it cannot be resolved.
      hint: str, The user-facing message for the fallthrough when it cannot be
        resolved.

    Raises:
      ValueError: if no hint is provided
    """
    if not hint:
      raise ValueError('Hint must be provided.')
    super(Fallthrough, self).__init__(hint)
    self._function = function

  def _Call(self, parsed_args):
    del parsed_args
    return self._function()


class PropertyFallthrough(_FallthroughBase):
  """Gets an attribute from a property."""

  def __init__(self, prop):
    """Initializes a fallthrough for the property associated with the attribute.

    Args:
      prop: googlecloudsdk.core.properties._Property, a property.
    """
    hint = 'Set the property [{}]'.format(prop)
    # Special messaging for the project property, which can be modified by the
    # global --project flag.
    if prop == properties.VALUES.core.project:
      hint += ' or provide the flag [--project] on the command line'

    super(PropertyFallthrough, self).__init__(hint)
    self.property = prop

  def _Call(self, parsed_args):
    del parsed_args  # Not used.
    try:
      return self.property.GetOrFail()
    except (properties.InvalidValueError, properties.RequiredPropertyError):
      return None

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return other.property == self.property


class ArgFallthrough(_FallthroughBase):
  """Gets an attribute from the argparse parsed values for that arg."""

  def __init__(self, arg_name, plural=False):
    """Initializes a fallthrough for the argument associated with the attribute.

    Args:
      arg_name: str, the name of the flag or positional.
      plural: bool, True if the value should be a list. Should be False for
        everything except the "anchor" arguments in a case where a resource
        argument is plural (i.e. parses to a list).
    """
    super(ArgFallthrough, self).__init__(
        'Provide the flag [{}] on the command line'.format(arg_name))
    self.arg_name = arg_name
    self.plural = plural

  def _Call(self, parsed_args):
    arg_value = getattr(parsed_args, util.NamespaceFormat(self.arg_name),
                        None if self.plural else [])
    # Positional arguments will always be stored in argparse as lists, even if
    # nargs=1. If not supposed to be plural, transform into a single value.
    if not self.plural and isinstance(arg_value, list):
      return arg_value[0] if arg_value else None
    else:
      return arg_value

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return other.arg_name == self.arg_name and self.plural == other.plural


class Deps(object):
  """Gets the values for attributes of a resource.

  Stores information about how to look up each attribute name with a series of
  fallthroughs, starting with the arg name that corresponds to that attribute.

  Attributes:
    attribute_to_fallthroughs_map: a map from attribute names to lists of
      fallthroughs.
  """

  def __init__(self, attribute_to_fallthroughs_map, parsed_args=None):
    """Initializes dependencies.

    The deps object stores a list from attributes to their fallthroughs,
    including the "primary" fallthrough (usually the attribute arg name).

    Args:
      attribute_to_fallthroughs_map: a map from attribute names to lists of
      fallthroughs.
      parsed_args: a parsed argparse namespace.
    """
    self.attribute_to_fallthroughs_map = attribute_to_fallthroughs_map
    self.parsed_args = parsed_args

  def Get(self, attribute):
    """Gets the value of an attribute based on fallthrough information.

    If the attribute value is not provided by any of the fallthroughs, an
    error is raised with a list of ways to provide information about the
    attribute.

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
        return fallthrough.GetValue(self.parsed_args)
      except FallthroughNotFoundError:
        continue
    fallthroughs_summary = '\n'.join(
        ['- {}'.format(f.hint) for f in fallthroughs])
    raise AttributeNotFoundError(
        'Failed to find attribute [{}]. The attribute can be set in the '
        'following ways: \n'
        '{}'.format(attribute, fallthroughs_summary))

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return (other.attribute_to_fallthroughs_map ==
            self.attribute_to_fallthroughs_map)
