# Copyright 2015 Google Inc. All Rights Reserved.

"""A module for the Cloud SDK CLI tree external representation."""

import argparse
import textwrap

from googlecloudsdk.core.console import console_io


class Flag(object):
  """Flag info.

  Attributes:
    type: str, The flag value type name {'bool', 'int', 'float', 'string'}.
    name: str, The normalized flag name (no leading -, '_' => '-').
    value: str, The flag value documentation name.
    countmin: int, The minimum number of flag values.
    countmax: int, The maximum number of flag values, 0 for unlimited.
    required: int, 1 if the flag must be specified, 0 otherwise.
    description: str, The help text.
    default: (self.type), The default flag value or None if no default.
    group: int, Mutually exclusive flag group id counting from 1, 0 if none.
  """

  def __init__(self, name, description='', default=None):
    self.type = 'string'
    self.name = name
    self.value = ''
    self.countmin = 0
    self.countmax = 0
    self.required = 0
    self.default = default
    self.description = description
    self.group = 0


class Positional(object):
  """Positional info.

  Attributes:
    name: str, The normalized name ('_' => '-').
    value: str, The flag value documentation name.
    countmin: int, The minimum number of positional values.
    countmax: int, The maximum number of positional values.
    required: int, 1 if the flag must be specified, 0 otherwise.
    description: str, The second and following lines of the flag docstring.
  """

  def __init__(self, name, description):
    self.name = name
    self.value = ''
    self.countmin = 0
    self.countmax = 0
    self.capsule = ''
    self.description = description


class Command(object):
  """Command and group info.

  Attributes:
    release: str, The command release name {'internal', 'alpha', 'beta', 'ga'}.
    name: str, The normalized name ('_' => '-').
    capsule: str, The first line of the command docstring.
    description: str, The second and following lines of the command docstring.
    flags: {str:str}, Command flag dict, indexed by normalized flag name.
    positionals: [str], Command positionals list.
    sections: {str:str}, Optional section help dict, indexed by section name.
  """

  def __init__(self, command, parent):

    self.release = command.ReleaseTrack().id
    self.name = command.name.replace('_', '-')
    self.hidden = command.IsHidden()
    self.flags = {}
    self.positionals = []
    self.sections = {}
    self.release, self.capsule = self.__Release(
        command, self.release, getattr(command, 'short_help', ''))
    self.release, self.description = self.__Release(
        command, self.release, getattr(command, 'long_help', ''))
    sections = getattr(command, 'detailed_help', None)
    if sections:
      for s in sections:
        if s == 'brief':
          self.release, self.capsule = self.__Release(
              command, self.release, sections[s])
        else:
          self.sections[s] = console_io.LazyFormat(
              self.__NormalizeDescription(sections[s]),
              command=self.name,
              index=self.capsule,
              description=self.description,
              parent_command=parent.name.replace('_', '-'))
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
          name = name[2:].replace('_', '-')
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
    for arg in args.flag_args:
      for name in arg.option_strings:
        if name.startswith('--'):
          name = name[2:].replace('_', '-')
          # Don't include ancestor flags or auto-generated --no-FLAG flags.
          if not self.__Ancestor(name) and (not name.startswith('no-') or
                                            arg.help != argparse.SUPPRESS):
            flag = Flag(name,
                        description=self.__NormalizeDescription(arg.help),
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
                flag.value = name.upper()
            if arg.required:
              flag.required = 1
            if name in group_name and group_name[name] in group_id:
              flag.group = group_id[group_name[name]]
            self.flags[flag.name] = flag

    # Collect the positionals.
    for arg in args.positional_args:
      name = arg.dest.replace('_', '-')
      positional = Positional(name,
                              description=self.__NormalizeDescription(arg.help))
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

  @staticmethod
  def __NormalizeDescription(description):
    """Normalizes description text.

    argparse.SUPPRESS normalizes to the empty string.

    Args:
      description: str, The text to be normalized.

    Returns:
      str, The normalized text.
    """
    description = textwrap.dedent(description)
    return '' if description == argparse.SUPPRESS else description

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
    description = self.__NormalizeDescription(description)
    path = command.GetPath()
    if len(path) >= 2 and path[1] == 'internal':
      release = 'INTERNAL'
    return release, description
