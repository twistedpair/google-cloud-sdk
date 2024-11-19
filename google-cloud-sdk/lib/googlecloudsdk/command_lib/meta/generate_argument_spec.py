# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Library for generating argument specifications for current implementations."""

from typing import Any, Dict
import uuid

from googlecloudsdk.calliope import cli_tree

MUTEX = 'mutex'
HIDDEN = 'hidden'
NAME = 'name'
NODE_ID = 'node_id'
ARGUMENTS = 'arguments'
REQUIRED = 'required'
GROUP = 'group'
TYPE = 'type'
CHOICES = 'choices'
POSITIONAL = 'positional'
OPTIONAL_NARGS = (0, '?', '*', '...')
GLOBAL = 'global'
UNDERSCORE = '_'
HYPHEN = '-'
FLAG_PREFIX = HYPHEN * 2
SHORT_FLAG_PREFIX = HYPHEN


def GenerateArgumentSpecifications(command_node=None) -> Dict[str, Any]:
  """Generates the argument specifications for the calliope cli command node.

  Args:
    command_node: calliope command node cli object.

  Returns:
    The argument specifications for the command node.
  """
  command_node = cli_tree.Command(command_node, None)
  if not command_node:
    return None
  argument_tree = {}
  args = _AddArgsToGroup(command_node.constraints)
  if args:
    argument_tree[ARGUMENTS] = args
  return argument_tree


def _AddArgsToGroup(arguments):
  """Add the given arguments to the given arguments group spec.

  Args:
    arguments: iterable: calliope objects representing the arguments group.

  Returns:
    The list of arguments added to the group spec.
  """
  args_group_spec = []
  for arg in arguments.arguments:
    if arg.is_group:
      child_args_group_spec = {ARGUMENTS: []}
      if arg.is_mutex:
        child_args_group_spec[MUTEX] = True
      if arg.is_required:
        child_args_group_spec[REQUIRED] = True
      if arg.is_hidden:
        child_args_group_spec[HIDDEN] = True
      child_args_group_spec[NODE_ID] = str(uuid.uuid4())
      child_args_group_spec[ARGUMENTS] = _AddArgsToGroup(arg)
      # Only retain non-empty arg groups.
      if child_args_group_spec[ARGUMENTS]:
        args_group_spec.append({GROUP: child_args_group_spec})
    elif arg.is_positional:
      args_group_spec.append(_GetPositionalSpec(arg))
    else:
      args_group_spec.append(_GetFlagSpec(arg))
  return args_group_spec


def _GetFlagSpec(flag):
  """Get the flag spec for the given flag.

  Args:
    flag: The calliope object representing the flag.

  Returns:
    The flag spec for the given flag.
  """
  flag_name = flag.name
  if flag_name.startswith(FLAG_PREFIX):
    flag_prefix = FLAG_PREFIX
  elif flag_name.startswith(SHORT_FLAG_PREFIX):
    flag_prefix = SHORT_FLAG_PREFIX
  else:
    flag_prefix = ''

  flag_name = flag_name[len(flag_prefix) :]
  flag_name = flag_name.replace(UNDERSCORE, HYPHEN)

  flag_spec = {NAME: flag_name}
  flag_spec[TYPE] = flag.type
  flag_spec[REQUIRED] = flag.is_required
  if flag.is_global:
    flag_spec[GLOBAL] = True
  if flag.choices:
    flag_spec[CHOICES] = list(flag.choices)
  flag_spec[NODE_ID] = str(uuid.uuid4())
  return flag_spec


def _GetPositionalSpec(positional):
  """Get the positional spec for the given positional.

  Args:
    positional: The calliope object representing the positional.

  Returns:
    The positional spec for the given positional.
  """
  positional_name = positional.name.replace(HYPHEN, UNDERSCORE).upper()
  positional_spec = {NAME: positional_name, POSITIONAL: True}

  # Include required if it is non-default i.e. true.
  positional_required = positional.nargs not in OPTIONAL_NARGS
  if positional_required:
    positional_spec[REQUIRED] = positional_required
  positional_spec[NODE_ID] = str(uuid.uuid4())
  return positional_spec
