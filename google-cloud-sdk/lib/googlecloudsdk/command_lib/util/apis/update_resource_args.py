# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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

"""Utilities for creating/parsing update resource argument groups."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import util as format_util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.apis import update_args
from googlecloudsdk.command_lib.util.apis import yaml_command_schema_util as util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import resources


# TODO(b/280653078) The UX is still under review. These utilities are
# liable to change and should not be used in new surface yet.

# TODO(b/283949482): Place this file in util/args and replace the duplicate
# logic in the util files.


def _GetRelativeNameField(arg_data):
  """Gets message field where the resource's relative name is mapped."""
  api_fields = [
      key
      for key, value in arg_data.resource_method_params.items()
      if util.REL_NAME_FORMAT_KEY in value
  ]
  if not api_fields:
    return None

  return api_fields[0]


def _GetSharedAttributeFlags(arg_data, shared_resource_flags):
  """Gets a list of all shared resource attributes."""
  ignored_flags = set()
  anchor_names = set(attr.name for attr in arg_data.anchors)

  for attr_name, flag_name in arg_data.attribute_to_flag_map.items():
    if (flag_name in arg_data.ignored_flags or
        flag_name in shared_resource_flags or
        attr_name in anchor_names):
      continue
    ignored_flags.add(flag_name)

  return list(ignored_flags)


def _GetResourceArgGenerator(
    arg_data, resource_collection, ignored_flags):
  """Gets a function to generate a resource arg."""
  def ArgGen(name, group_help, flag_name_override):
    group_help += '\n\n'
    if arg_data.group_help:
      group_help += arg_data.group_help

    return arg_data.GenerateResourceArg(
        resource_collection,
        presentation_flag_name=name,
        flag_name_override=flag_name_override,
        shared_resource_flags=ignored_flags,
        group_help=group_help)
  return ArgGen


def _GenerateSharedFlags(
    arg_data, resource_collection, shared_flag_names):
  """Generates a list of flags needed to generate more than one resource arg."""
  arg_gen = _GetResourceArgGenerator(
      arg_data, resource_collection, None)

  # Generate a fake resource arg where none of the flags are filtered out.
  resource_arg_info = arg_gen(
      '--current', '', None).GetInfo('--current')

  return [
      arg for arg in resource_arg_info.GetAttributeArgs()
      if arg.name in shared_flag_names
  ]


class UpdateResourceArgumentGenerator(update_args.UpdateArgumentGenerator):
  """Update flag generator for resource args."""

  @classmethod
  def FromArgData(
      cls, arg_data, method_resource_collection, is_list_method=False,
      shared_resource_flags=None
  ):
    if arg_data.multitype and arg_data.repeated:
      gen_cls = UpdateMultitypeListResourceArgumentGenerator
    elif arg_data.multitype:
      gen_cls = UpdateMultitypeResourceArgumentGenerator
    elif arg_data.repeated:
      gen_cls = UpdateListResourceArgumentGenerator
    else:
      gen_cls = UpdateDefaultResourceArgumentGenerator

    presentation_flag_name = arg_data.GetPresentationFlagName(
        method_resource_collection, is_list_method)
    is_primary = arg_data.IsPrimaryResource(method_resource_collection)
    if is_primary:
      raise util.InvalidSchemaError(
          '{} is a primary resource. Primary resources are required and '
          'cannot be listed as clearable.'.format(presentation_flag_name)
      )

    api_field = _GetRelativeNameField(arg_data)
    if not api_field:
      raise util.InvalidSchemaError(
          '{} does not specify the message field where the relative name is '
          'mapped in resource_method_params. Message field name is needed '
          'in order add update args. Please update '
          'resource_method_params.'.format(presentation_flag_name)
      )

    shared_flags = shared_resource_flags or []
    shared_attribute_flags = _GetSharedAttributeFlags(
        arg_data, shared_flags)
    # All of the flags the resource arg should not generate
    all_shared_flags = shared_attribute_flags + shared_flags

    return gen_cls(
        presentation_flag_name=presentation_flag_name,
        arg_gen=_GetResourceArgGenerator(
            arg_data, method_resource_collection, all_shared_flags),
        api_field=api_field,
        repeated=arg_data.repeated,
        collections=arg_data.collections,
        is_primary=is_primary,
        # attributes shared between update args we need to generate and
        # add to the root.
        shared_attribute_flags=_GenerateSharedFlags(
            arg_data, method_resource_collection, shared_attribute_flags),
        anchor_names=[attr.name for attr in arg_data.anchors],
    )

  def __init__(
      self,
      presentation_flag_name,
      arg_gen=None,
      is_hidden=False,
      api_field=None,
      repeated=False,
      collections=None,
      is_primary=None,
      shared_attribute_flags=None,
      anchor_names=None,
  ):
    super(UpdateResourceArgumentGenerator, self).__init__()
    self.arg_name = format_util.NormalizeFormat(
        presentation_flag_name)
    self.arg_gen = arg_gen
    self.is_hidden = is_hidden
    self.api_field = api_field
    self.repeated = repeated
    self.collections = collections or []
    self.is_primary = is_primary
    self.shared_attribute_flags = shared_attribute_flags or []
    self.anchor_names = anchor_names or []

  def _GetAnchorFlag(self, attr_name, flag_prefix_value):
    if len(self.anchor_names) > 1:
      base_name = attr_name
    else:
      base_name = self.arg_name
    return arg_utils.GetFlagName(base_name, flag_prefix=flag_prefix_value)

  def _CreateResourceFlag(self, flag_prefix=None, group_help=None):
    prefix = flag_prefix and flag_prefix.value
    flag_name = arg_utils.GetFlagName(
        self.arg_name,
        flag_prefix=prefix)

    flag_name_override = {
        anchor_name: self._GetAnchorFlag(anchor_name, prefix)
        for anchor_name in self.anchor_names
    }

    return self.arg_gen(
        flag_name, group_help=group_help, flag_name_override=flag_name_override)

  def _RelativeName(self, value):
    resource = None
    for collection in self.collections:
      try:
        resource = resources.REGISTRY.ParseRelativeName(
            value,
            collection.full_name,
            api_version=collection.api_version)
      except resources.Error:
        continue

    return resource

  def GetArgFromNamespace(self, namespace, arg):
    """Retrieves namespace value associated with flag.

    Args:
      namespace: The parsed command line argument namespace.
      arg: base.Argument|concept_parsers.ConceptParser|None, used to get
        namespace value

    Returns:
      value parsed from namespace
    """
    if isinstance(arg, base.Argument):
      return arg_utils.GetFromNamespace(namespace, arg.name)

    if isinstance(arg, concept_parsers.ConceptParser):
      all_anchors = list(arg.specs.keys())
      if len(all_anchors) != 1:
        raise ValueError(
            'ConceptParser must contain exactly one spec for clearable '
            'but found specs {}. {} cannot parse the namespace value if more '
            'than or less than one spec is added to the '
            'ConceptParser.'.format(all_anchors, type(self).__name__))
      name = all_anchors[0]
      value = arg_utils.GetFromNamespace(namespace.CONCEPTS, name)
      if value:
        value = value.Parse()
      return value

    return None

  def GetFieldValueFromMessage(self, existing_message):
    value = arg_utils.GetFieldValueFromMessage(existing_message, self.api_field)
    if not value:
      return None

    if isinstance(value, list):
      relative_names = (self._RelativeName(v) for v in value)
      return [name for name in relative_names if name]
    else:
      return self._RelativeName(value)

  def Generate(self):
    return super(UpdateResourceArgumentGenerator, self).Generate(
        self.shared_attribute_flags)


class UpdateDefaultResourceArgumentGenerator(UpdateResourceArgumentGenerator):
  """Update flag generator for resource args."""

  @property
  def _empty_value(self):
    return None

  @property
  def set_arg(self):
    return self._CreateResourceFlag(
        group_help='Set {} to new value.'.format(self.arg_name))

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix=update_args.Prefix.CLEAR,
        action='store_true',
        help_text=(
            f'Clear {self.arg_name} value and set '
            f'to {self._GetTextFormatOfEmptyValue(self._empty_value)}.'),
    )

  def ApplySetFlag(self, output, set_val):
    if set_val:
      return set_val
    return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    return output


class UpdateMultitypeResourceArgumentGenerator(UpdateResourceArgumentGenerator):
  """Update flag generator for multitype resource args."""

  @property
  def _empty_value(self):
    return None

  @property
  def set_arg(self):
    return self._CreateResourceFlag(
        group_help='Set {} to new value.'.format(self.arg_name))

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix=update_args.Prefix.CLEAR,
        action='store_true',
        help_text=(
            f'Clear {self.arg_name} value and set '
            f'to {self._GetTextFormatOfEmptyValue(self._empty_value)}.'),
    )

  def ApplySetFlag(self, output, set_val):
    if result := (set_val and set_val.result):
      return result
    else:
      return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    else:
      return output


class UpdateListResourceArgumentGenerator(UpdateResourceArgumentGenerator):
  """Update flag generator for list resource args."""

  @property
  def _empty_value(self):
    return []

  @property
  def set_arg(self):
    return self._CreateResourceFlag(
        group_help=f'Set {self.arg_name} to new value.')

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix=update_args.Prefix.CLEAR,
        action='store_true',
        help_text=(
            f'Clear {self.arg_name} value and set '
            f'to {self._GetTextFormatOfEmptyValue(self._empty_value)}.'),
    )

  @property
  def update_arg(self):
    return self._CreateResourceFlag(
        flag_prefix=update_args.Prefix.ADD,
        group_help=f'Add new value to {self.arg_name} list.')

  @property
  def remove_arg(self):
    return self._CreateResourceFlag(
        flag_prefix=update_args.Prefix.REMOVE,
        group_help=f'Remove value from {self.arg_name} list.')

  def ApplySetFlag(self, output, set_val):
    if set_val:
      return set_val
    return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    return output

  def ApplyRemoveFlag(self, existing_val, remove_val):
    value = existing_val or self._empty_value
    if remove_val:
      return [x for x in value if x not in remove_val]
    else:
      return value

  def ApplyUpdateFlag(self, existing_val, update_val):
    value = existing_val or self._empty_value
    if update_val:
      return existing_val + [x for x in update_val if x not in value]
    else:
      return value


class UpdateMultitypeListResourceArgumentGenerator(
    UpdateResourceArgumentGenerator):
  """Update flag generator for multitype list resource args."""

  @property
  def _empty_value(self):
    return []

  @property
  def set_arg(self):
    return self._CreateResourceFlag(
        group_help=f'Set {self.arg_name} to new value.')

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix=update_args.Prefix.CLEAR,
        action='store_true',
        help_text=(
            f'Clear {self.arg_name} value and set '
            f'to {self._GetTextFormatOfEmptyValue(self._empty_value)}.'),
    )

  @property
  def update_arg(self):
    return self._CreateResourceFlag(
        flag_prefix=update_args.Prefix.ADD,
        group_help=f'Add new value to {self.arg_name} list.')

  @property
  def remove_arg(self):
    return self._CreateResourceFlag(
        flag_prefix=update_args.Prefix.REMOVE,
        group_help=f'Remove value from {self.arg_name} list.')

  def ApplySetFlag(self, output, set_val):
    resource_list = [val.result for val in set_val if val.result]
    if resource_list:
      return resource_list
    else:
      return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    else:
      return output

  def ApplyRemoveFlag(self, existing_val, remove_val):
    value = existing_val or self._empty_value
    if remove_resources := set(val.result for val in remove_val if val.result):
      return [x for x in value if x not in remove_resources]
    else:
      return value

  def ApplyUpdateFlag(self, existing_val, update_val):
    value = existing_val or self._empty_value
    if update_val:
      return value + [
          x.result for x in update_val if x.result not in value]
    else:
      return value
