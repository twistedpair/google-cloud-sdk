# -*- coding: utf-8 -*- #
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
"""Classes to define multitype concept specs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import operator
import enum

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps as deps_lib
from googlecloudsdk.core import exceptions
import six


class Error(exceptions.Error):
  """Base class for errors in this module."""


class ConfigurationError(Error):
  """Raised if the spec is misconfigured."""


class ConflictingTypesError(Error):
  """Raised if there are multiple or no possible types for the spec."""

  def __init__(self, specified_attributes=None):
    message = 'No types found: You specified [{}]'.format(
        ', '.join([attribute.name for attribute in specified_attributes or []]))
    super(ConflictingTypesError, self).__init__(message)


class MultitypeConceptSpec(concepts.ConceptSpec):
  """A concept spec that can have multiple possible types.

  Creating a multitype concept spec requires a name and a list of
  concept specs. For example, to create a spec out of two other specs, a
  project_foo_spec and an organization_foo_spec:

    proj_org_foo_spec = MultitypeConceptSpec(
        'projorgfoo', project_foo_spec, organization_foo_spec)

  The command should parse the concept in the same way as always, obtaining a
  TypedConceptResult:

    result = args.CONCEPTS.proj_org_foo.Parse()

  To check the type of the result and use it, the user might do:

    if result.type_ == type(result.type_).PROJFOO:
      _HandleProjectResource(result.result)
    else:
     _HandleOrgResource(result.result)

  Attributes:
    name: str, the name of the concept
    plural_name: str, the pluralized name. Will be pluralized by default rules
      if not given in cases where the resource is referred to in the plural.
    attributes: [concepts._Attribute], a list of attributes of the concept.
    type_enum: enum.Enum, an Enum class representing the available types.
  """

  def __init__(self, name, *concept_specs, **kwargs):
    self._name = name
    self._plural_name = kwargs.get('plural_name', None)
    self._concept_specs = concept_specs
    self._attributes = []
    self._attribute_to_types_map = {}
    self.disable_auto_completers = True

    # If any names are repeated, rename the concept as
    # '{concept_name}_{attribute1}_{attribute2}_...'
    self._name_to_concepts = {}
    final_names = []
    for concept_spec in self._concept_specs:
      name = self._GetUniqueNameForSpec(concept_spec)
      final_names.append(name)
      self._name_to_concepts[name] = concept_spec

    self.type_enum = enum.Enum('Type', final_names)

    for spec in self._concept_specs:
      for attribute in spec.attributes:
        if attribute not in self._attributes:
          if attribute.name in [existing.name for existing in self._attributes]:
            raise ConfigurationError(
                'Multiple non-equivalent attributes found with name [{}]'
                .format(attribute.name))
          self._attributes.append(attribute)
        self._attribute_to_types_map.setdefault(attribute.name, []).append(
            (self.type_enum[self._ConceptToName(spec)]))

  def _GetUniqueNameForSpec(self, concept_spec):
    names = [spec.name for spec in self._concept_specs]
    if sum([concept_spec.name == n for n in names]) > 1:
      return '{}_{}'.format(
          concept_spec.name,
          '_'.join([a.name for a in concept_spec.attributes]))
    else:
      return concept_spec.name

  @property
  def name(self):
    return self._name

  @property
  def attributes(self):
    return self._attributes

  def _ConceptToName(self, concept_spec):
    """Helper to get the type enum name for a concept spec."""
    for name, spec in six.iteritems(self._name_to_concepts):
      if spec == concept_spec:
        return name

  def _GetActivelySpecifiedAttributes(self, fallthroughs_map, parsed_args=None):
    """Get a list of attributes that are actively specified in runtime."""
    specified = []
    final_map = {
        attr: filter(operator.attrgetter('active'), fallthroughs)
        for attr, fallthroughs in six.iteritems(fallthroughs_map)
    }
    for attribute in self.attributes:
      try:
        value = deps_lib.Get(attribute.name, final_map, parsed_args=None)
      except deps_lib.AttributeNotFoundError:
        continue
      if value:
        specified.append(attribute)
    return specified

  def _GetPossibleTypes(self, attributes, type_filter=None):
    """Helper method to get all types that match a set of attributes."""
    # We can't just attempt to parse each subtype because we are distinguishing
    # between "actively" and "passively" specified attributes. A concept that is
    # not fully specified on the command line directly, but which is parseable
    # using both active and other means (such as properties), should still be
    # viable. Thus, we just use each available attribute to *narrow down*
    # the possible types.
    possible_types = []
    for candidate in self.type_enum:
      possible = True
      if type_filter and not type_filter(candidate):
        possible = False
      for attribute in attributes:
        if candidate not in self._attribute_to_types_map.get(
            attribute.name, []):
          possible = False
      if possible:
        possible_types.append(
            (candidate, self._name_to_concepts[candidate.name]))
    return possible_types

  def _GetActiveType(self, fallthroughs_map, parsed_args=None,
                     type_filter=None):
    """Helper method to get the type based on actively specified info."""
    actively_specified = self._GetActivelySpecifiedAttributes(
        fallthroughs_map, parsed_args=parsed_args)

    active_types = self._GetPossibleTypes(actively_specified,
                                          type_filter=type_filter)

    if not active_types:
      raise ConflictingTypesError(actively_specified)

    if len(active_types) == 1:
      return active_types[0]

    for i in range(len(active_types)):
      active_type = active_types[i]
      if all(
          [set(active_type[1].attributes).issubset(
              set(other_type[1].attributes))
           for j, other_type in enumerate(active_types) if i != j]):
        return active_type
    raise ConflictingTypesError(actively_specified)

  def Initialize(self, fallthroughs_map, parsed_args=None, type_filter=None):
    """Initializes the concept.

    Determines which attributes are actively specified (i.e. on the command
    line) in order to determine which type of concept is being specified by the
    user. The rules are:
      1) If no contained concept spec is compatible with *all* actively
         specified attributes, fail.
      2) If *exactly one* contained concept spec is compatible with all actively
         specified attributes, initialize that concept spec with all available
         data. If that concept spec can't be initialized, fail.
      3) If more than one concept spec is compatible, but one has a list of
         required attributes that is a *subset* of the attributes of each of
         the others, initialize that concept spec with all available data.
         (Useful for parent-child concepts where extra information can be
         specified, but is optional.) If that concept spec can't be initialized,
         fail.
      4) Otherwise, we can't tell what type of concept the user wanted to
         specify, so fail.

    Args:
      fallthroughs_map: {str: [deps_lib._FallthroughBase]}, a dict of finalized
        fallthroughs for the resource.
      parsed_args: the argparse namespace.
      type_filter: a function object that takes a single type enum and returns
        a boolean value (True if that type is acceptable, False if not).

    Raises:
      ConflictingTypesError, if more than one possible type exists.
      concepts.InitializationError, if the concept cannot be initialized from
        the data.

    Returns:
      A TypedConceptResult that stores the type of the parsed concept and the
        raw parsed concept (such as a resource reference).
    """
    type_ = self._GetActiveType(fallthroughs_map, parsed_args=parsed_args,
                                type_filter=type_filter)
    return TypedConceptResult(
        type_[1].Initialize(fallthroughs_map, parsed_args=parsed_args),
        type_[0])


class TypedConceptResult(object):
  """A small wrapper to hold the results of parsing a multityped concept."""

  def __init__(self, result, type_):
    """Initializes.

    Args:
      result: the parsed concept, such as a resource reference.
      type_: the enum value of the type of the result.
    """
    self.result = result
    self.type_ = type_


class MultitypeResourceSpec(MultitypeConceptSpec, concepts.ResourceSpec):
  """A resource spec that contains multiple possible types."""

  def IsAnchor(self, attribute):
    """Convenience method."""
    return any([attribute == spec.anchor
                for spec in self._concept_specs])

  def _GetUniqueNameForSpec(self, resource_spec):
    """Overrides this functionality from generic multitype concept specs."""
    # If all resources have different names, use their names.
    resource_names = [spec.name for spec in self._concept_specs]
    if len(set(resource_names)) == len(resource_names):
      return resource_spec.name
    # Otherwise, use the collection name.
    collection_names = [spec.collection for spec in self._concept_specs]
    if sum([resource_spec.collection == n for n in collection_names]) > 1:
      raise ValueError('Attempting to create a multitype spec with duplicate '
                       'collections. Collection name: [{}]'.format(
                           resource_spec.collection))
    else:
      return resource_spec.collection

  def _GetAttributeAnchorFallthroughs(self, anchor_fallthroughs, attribute):
    """Helper to get anchor-dependent fallthroughs for a given attribute."""
    anchor_based_fallthroughs = []
    for spec in self._concept_specs:
      # Only add fallthroughs for attributes that are not the anchor but do
      # belong to the relevant concept.
      if attribute not in spec.attributes or attribute == spec.anchor:
        continue
      parameter_name = spec.ParamName(attribute.name)
      anchor_based_fallthroughs += [
          deps_lib.FullySpecifiedAnchorFallthrough(
              anchor_fallthrough, spec.collection_info,
              parameter_name)
          for anchor_fallthrough in anchor_fallthroughs]
    return anchor_based_fallthroughs
