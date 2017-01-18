# Copyright 2015 Google Inc. All Rights Reserved.
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

"""A module for the Cloud SDK CLI tree external representation."""

import argparse
import textwrap

from googlecloudsdk.core.console import console_io


def _NormalizeDescription(description):
  """Normalizes description text.

  argparse.SUPPRESS normalizes to None.

  Args:
    description: str, The text to be normalized.

  Returns:
    str, The normalized text.
  """
  if description == argparse.SUPPRESS:
    description = None
  elif description:
    description = textwrap.dedent(description)
  return description or ''


class Flag(object):
  """Flag info.

  Attributes:
    type: str, The flag value type name {'bool', 'int', 'float', 'string'}.
    name: str, The normalized flag name ('_' => '-').
    hidden: bool, True if the flag is hidden.
    category: str, Category for help doc flag groupings.
    value: str, The flag value documentation name.
    countmin: int, The minimum number of flag values.
    countmax: int, The maximum number of flag values, 0 for unlimited.
    required: int, 1 if the flag must be specified, 0 otherwise.
    description: str, The help text.
    choices: list, The list of static choices.
    default: (self.type), The default flag value or None if no default.
    group: int, Mutually exclusive flag group id counting from 1, 0 if none.
    resource: str, Flag value resource identifier.
  """

  def __init__(self, name, description='', default=None):
    self.type = 'string'
    self.name = name
    self.hidden = description == argparse.SUPPRESS
    self.category = None
    self.value = ''
    self.countmin = 0
    self.countmax = 0
    self.required = 0
    self.choices = []
    self.default = default
    self.description = _NormalizeDescription(description)
    self.group = 0
    self.resource = ''


class Positional(object):
  """Positional info.

  Attributes:
    name: str, The normalized name ('_' => '-').
    value: str, The positional value documentation name.
    countmin: int, The minimum number of positional values.
    countmax: int, The maximum number of positional values.
    required: int, 1 if the positional must be specified, 0 otherwise.
    description: str, The help text.
    resource: str, Positional value resource identifier.
  """

  def __init__(self, name, description):
    self.name = name
    self.value = ''
    self.countmin = 0
    self.countmax = 0
    self.capsule = ''
    self.description = description
    self.resource = ''


class Command(object):
  """Command and group info.

  Attributes:
    release: str, The command release name {'internal', 'alpha', 'beta', 'ga',
      'preview'}.
    name: str, The normalized name ('_' => '-').
    hidden: bool, True if the command is hidden.
    capsule: str, The first line of the command docstring.
    description: str, The second and following lines of the command docstring.
    flags: {str:str}, Command flag dict, indexed by normalized flag name.
    positionals: [str], Command positionals list.
    sections: {str:str}, Optional section help dict, indexed by section name.
  """

  def __init__(self, command, parent, include_hidden_flags=True):

    self.release = command.ReleaseTrack().id
    self.path = command.GetPath()
    self.name = command.name.replace('_', '-')
    self.hidden = command.IsHidden()
    self.flags = {}
    self.positionals = []
    self.sections = {}
    parent_command = parent.name.replace('_', '-') if parent else ''
    self.release, capsule = self.__Release(
        command, self.release, getattr(command, 'short_help', ''))
    self.capsule = console_io.LazyFormat(
        _NormalizeDescription(capsule),
        command=self.name,
        parent_command=parent_command)
    self.release, description = self.__Release(
        command, self.release, getattr(command, 'long_help', ''))
    self.description = console_io.LazyFormat(
        _NormalizeDescription(description),
        command=self.name,
        index=self.capsule,
        parent_command=parent_command)
    sections = getattr(command, 'detailed_help', None)
    if sections:
      for s in sections:
        if s == 'brief':
          self.release, self.capsule = self.__Release(
              command, self.release, sections[s])
        else:
          self.sections[s] = console_io.LazyFormat(
              _NormalizeDescription(sections[s]),
              command=self.name,
              index=self.capsule,
              description=self.description,
              parent_command=parent_command)
    self.commands = {}
    # _parent is explicitly private so it won't appear in serialized output.
    self._parent = parent
    if parent:
      parent.commands[self.name] = self
    args = command.ai

    # Initialize the mutually exclusive flag groups.
    group_count = {}
    group_name = {}
    for arg in args.flag_args:
      for name in arg.option_strings:
        if name.startswith('--'):
          name = name.replace('_', '-')
          if not self.__Ancestor(name):
            g = args.mutex_groups.get(arg.dest, None)
            if g:
              group_name[name] = g
              if g in group_count:
                group_count[g] += 1
              else:
                group_count[g] = 1
    group_id_count = 0
    group_id = {}
    # Sorted iteration preserves group_id[] indices across separate invocations
    # where the mutex groups do not change.
    for _, g in sorted(group_name.iteritems()):
      if group_count[g] > 1:
        group_count[g] = 0  # Don't check this group again!
        group_id_count += 1
        group_id[g] = group_id_count

    # Collect the flags.
    for arg in sorted(args.flag_args):
      for name in arg.option_strings:
        if name.startswith('--'):
          name = name.replace('_', '-')
          # Don't include ancestor flags.
          if not self.__Ancestor(name):
            flag = Flag(
                name,
                description=arg.help,
                default=arg.default)
            # ArgParse does not have an explicit Boolean flag type. By
            # convention a flag with arg.nargs=0 and action='store_true' or
            # action='store_false' is a Boolean flag. arg.type gives no hint
            # (arg.type=bool would have been so easy) and we don't have access
            # to args.action here. Even then the flag can take on non-Boolean
            # values. If arg.default is not specified then it will be None, but
            # it can be set to anything. So we do a conservative 'truthiness'
            # test here.
            if arg.nargs == 0:
              flag.type = 'bool'
              flag.default = True if arg.default else False
            else:
              if arg.type == int:
                flag.type = 'int'
              elif arg.type == float:
                flag.type = 'float'
              if arg.nargs == '*':
                pass
              elif arg.nargs == '?':
                flag.countmax = 1
              elif arg.nargs == '+':
                flag.countmin = 1
              elif type(arg.nargs) in (int, long):
                flag.countmin = arg.nargs
                flag.countmax = arg.nargs
              if arg.metavar:
                flag.value = arg.metavar
              else:
                flag.value = name[2:].upper()
            if arg.choices:
              choices = sorted(arg.choices)
              if choices == ['false', 'true']:
                flag.type = 'bool'
              else:
                flag.choices = choices
            flag.category = arg.category
            if arg.required:
              flag.required = 1
            flag.resource = getattr(arg, 'completion_resource', '')
            if name in group_name and group_name[name] in group_id:
              flag.group = group_id[group_name[name]]
            if include_hidden_flags or not flag.hidden:
              self.flags[flag.name] = flag

    # Collect the positionals.
    for arg in args.positional_args:
      name = arg.dest.replace('_', '-')
      positional = Positional(name, description=_NormalizeDescription(arg.help))
      if arg.metavar:
        positional.value = arg.metavar
      if arg.nargs != 0:
        if arg.nargs == '*':
          pass
        elif arg.nargs == '?':
          positional.countmax = 1
        elif arg.nargs == '+':
          positional.countmin = 1
        elif type(arg.nargs) in (int, long):
          positional.countmin = arg.nargs
          positional.countmax = arg.nargs
      positional.resource = getattr(arg, 'completion_resource', '')
      self.positionals.append(positional)

  def __Ancestor(self, flag):
    """Determines if flag is provided by an ancestor command.

    Args:
      flag: str, The flag name (no leading '-').

    Returns:
      bool, True if flag provided by an ancestor command, false if not.
    """
    command = self._parent
    while command:
      if flag in command.flags:
        return True
      command = command._parent  # pylint: disable=protected-access
    return False

  def __Release(self, command, release, description):
    """Determines the release type from the description text.

    Args:
      command: Command, The CLI command/group description.
      release: int, The default release type.
      description: str, The command description markdown.

    Returns:
      (release, description): (int, str), The actual release and description
        with release prefix omitted.
    """
    description = _NormalizeDescription(description)
    path = command.GetPath()
    if len(path) >= 2 and path[1] == 'internal':
      release = 'INTERNAL'
    return release, description
