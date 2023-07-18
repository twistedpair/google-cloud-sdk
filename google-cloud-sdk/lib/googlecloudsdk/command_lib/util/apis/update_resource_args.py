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
from googlecloudsdk.core import resources


# TODO(b/280653078) The UX is still under review. These utilities are
# liable to change and should not be used in new surface yet.

# TODO(b/283949482): Place this file in util/args and replace the duplicate
# logic in the util files.


class UpdateResourceArgumentGenerator(update_args.UpdateArgumentGenerator):
  """Update flag generator for resource args."""

  @classmethod
  def FromArgData(
      cls, arg_data, method, shared_resource_args=None
  ):
    if arg_data.repeated:
      gen_cls = UpdateListResourceArgumentGenerator
    else:
      gen_cls = UpdateDefaultResourceArgumentGenerator

    def ArgGen(arg_name):
      return arg_data.GenerateResourceArg(
          method, arg_name, shared_resource_args)

    arg_name = arg_data.GetAnchorArgName(method)
    is_primary = arg_data.IsPrimaryResource(
        method and method.resource_argument_collection
    )
    if is_primary:
      raise util.InvalidSchemaError(
          '{} is a primary resource. Primary resources are required and '
          'cannot be listed as clearable.'.format(arg_name)
      )

    api_fields = [
        key
        for key, value in arg_data.resource_method_params.items()
        if util.REL_NAME_FORMAT_KEY in value
    ]

    if not api_fields:
      raise util.InvalidSchemaError(
          '{} does not specify the message field where the relative name is '
          'mapped in resource_method_params. Message field name is needed '
          'in order add update args. Please update '
          'resource_method_params.'.format(arg_name)
      )

    api_field = api_fields[0]

    return gen_cls(
        arg_name=arg_name,
        arg_gen=ArgGen,
        api_field=api_field,
        repeated=arg_data.repeated,
        collection=arg_data.collection,
        is_primary=is_primary
    )

  def __init__(
      self,
      arg_name,
      arg_gen=None,
      is_hidden=False,
      api_field=None,
      repeated=False,
      collection=None,
      is_primary=None,
  ):
    super(UpdateResourceArgumentGenerator, self).__init__()
    self.arg_name = format_util.NormalizeFormat(arg_name)
    self.arg_gen = arg_gen
    self.is_hidden = is_hidden
    self.api_field = api_field
    self.repeated = repeated
    self.collection = collection
    self.is_primary = is_primary

  def _CreateResourceFlag(self, flag_prefix=None):
    flag_name = self._GetFlagName(self.arg_name, flag_prefix=flag_prefix)
    return self.arg_gen(flag_name)

  def _RelativeName(self, value):
    return resources.REGISTRY.ParseRelativeName(
        value, self.collection.full_name)

  def GetArgFromNamespace(self, namespace, arg):
    """Retrieves namespace value associated with flag.

    Args:
      namespace: The parsed command line argument namespace.
      arg: base.Argument, used to get namespace value

    Returns:
      value parsed from namespace
    """
    if arg is None:
      return None

    if isinstance(arg, base.Argument):
      return arg_utils.GetFromNamespace(namespace, arg.name)

    value = arg_utils.GetFromNamespace(namespace.CONCEPTS, self.arg_name)
    if value:
      value = value.Parse()

    return value

  def GetFieldValueFromMessage(self, existing_message):
    value = arg_utils.GetFieldValueFromMessage(existing_message, self.api_field)
    if not value:
      return None

    if isinstance(value, list):
      return [self._RelativeName(v) for v in value]
    return self._RelativeName(value)


class UpdateDefaultResourceArgumentGenerator(UpdateResourceArgumentGenerator):
  """Update flag generator for resource args."""

  @property
  def _empty_value(self):
    return None

  @property
  def set_arg(self):
    return self._CreateResourceFlag()

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix='clear',
        action='store_true',
        help_text='Clear {} value and set to {}.'.format(
            self.arg_name, self._GetTextFormatOfEmptyValue(self._empty_value)),
    )

  def ApplySetFlag(self, output, set_val):
    if set_val:
      return set_val
    return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    return output


class UpdateListResourceArgumentGenerator(UpdateResourceArgumentGenerator):
  """Update flag generator for list resource args."""

  @property
  def _empty_value(self):
    return []

  @property
  def set_arg(self):
    return self._CreateResourceFlag()

  @property
  def clear_arg(self):
    return self._CreateFlag(
        self.arg_name,
        flag_prefix='clear',
        action='store_true',
        help_text='Clear {} value and set to {}.'.format(
            self.arg_name, self._GetTextFormatOfEmptyValue(self._empty_value)),
    )

  def ApplySetFlag(self, output, set_val):
    if set_val:
      return set_val
    return output

  def ApplyClearFlag(self, output, clear_flag):
    if clear_flag:
      return self._empty_value
    return output

