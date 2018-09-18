# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Classes that manage concepts and dependencies."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools

from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.command_lib.concepts import base
from googlecloudsdk.command_lib.concepts import names

import six


class DependencyManager(object):
  """Holds dependency info for a single overall concept and creates views.

  Attributes:
    node: the DependencyNode at the root of the dependency tree for this
      concept.
  """

  def __init__(self, node):
    self.node = node

  def ParseConcept(self, parsed_args):
    """Parse the concept recursively by building the dependencies in a DFS.

    Args:
      parsed_args: the raw parsed argparse namespace.

    Raises:
      googlecloudsdk.command_lib.concepts.exceptions.Error: if parsing fails.

    Returns:
      the parsed top-level concept.
    """

    def _ParseConcept(node):
      """Recursive parsing."""
      if not node.dependencies:
        fallthroughs = []
        if node.arg_name:
          fallthroughs.append(deps_lib.ArgFallthrough(node.arg_name))
        fallthroughs += node.fallthroughs
        return node.concept.Parse(
            DependencyViewFromValue(
                functools.partial(
                    deps_lib.GetFromFallthroughs, fallthroughs, parsed_args)))
      return node.concept.Parse(
          DependencyView(
              {name: _ParseConcept(child)
               for name, child in six.iteritems(node.dependencies)}))

    return _ParseConcept(self.node)


class DependencyView(object):
  """Simple namespace used by concept.Parse."""

  def __init__(self, values_dict):
    for key, value in six.iteritems(values_dict):
      setattr(self, names.ConvertToNamespaceName(key), value)


class DependencyViewFromValue(object):
  """Simple namespace for single value."""

  def __init__(self, value_getter):
    self._value_getter = value_getter

  @property
  def value(self):
    """Lazy value getter.

    Returns:
      the value of the attribute, from its fallthroughs.

    Raises:
      deps_lib.AttributeNotFoundError: if the value cannot be found.
    """
    return self._value_getter()


class DependencyNode(object):
  """A node of a dependency tree.

  Attributes:
    name: the name that will be used to look up the dependency from higher
      in the tree. Corresponds to the "key" of the attribute.
    concept: the concept of the attribute.
    dependencies: {str: DependencyNode}, a map from dependency names to
      sub-dependency trees.
    arg_name: str, the argument name of the attribute.
    fallthroughs: [deps_lib._Fallthrough], the list of fallthroughs for the
      dependency.
  """

  def __init__(self, name, concept=None, dependencies=None, arg_name=None,
               fallthroughs=None):
    self.name = name
    self.concept = concept
    self.dependencies = dependencies
    self.arg_name = arg_name
    self.fallthroughs = fallthroughs or []

  @classmethod
  def FromAttribute(cls, attribute):
    """Builds the dependency tree from the attribute."""
    if isinstance(attribute, base.Attribute):
      return DependencyNode(attribute.concept.key, concept=attribute.concept,
                            arg_name=attribute.arg_name,
                            fallthroughs=attribute.fallthroughs)
    return DependencyNode(attribute.concept.key, concept=attribute.concept,
                          dependencies={
                              a.concept.key: DependencyNode.FromAttribute(a)
                              for a in attribute.attributes})
