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
import re
import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import backend
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import module_util
from googlecloudsdk.core.console import console_io


def _GetDescription(arg):
  """Returns the most detailed description from arg."""
  if arg.help == argparse.SUPPRESS:
    return ''
  return usage_text.GetArgDetails(arg)


def _NormalizeDescription(description):
  """Normalizes description text.

  argparse.SUPPRESS normalizes to None.

  Args:
    description: str, The text to be normalized.

  Returns:
    str, The normalized text.
  """
  if callable(description):
    description = description()
  if description == argparse.SUPPRESS:
    description = None
  elif description:
    description = textwrap.dedent(description)
  return description or ''


class Argument(object):
  """Positional or flag argument.

  Attributes:
    completer: str, Resource completer name.
    default: (self.type), The default flag value or None if no default.
    description: str, The help text.
    name: str, The normalized name ('_' => '-').
    nargs: {0, 1, '?', '*', '+'}
    required: bool, The argument must be specified.
    value: str, The argument value documentation name.
  """

  def __init__(self, arg, name):

    completer = getattr(arg, 'completer', None)
    if isinstance(completer, type):
      self.completer = module_util.GetModulePath(completer) or ''
    else:
      # Legacy completer.
      self.completer = None
    self.default = arg.default
    self.description = _NormalizeDescription(_GetDescription(arg))
    self.name = name
    self.nargs = str(arg.nargs or 0)
    self.required = False
    if arg.metavar:
      self.value = arg.metavar
    else:
      self.value = name.lstrip('-').replace('-', '_').upper()
    self._Scrub()

  def _Scrub(self):
    """Scrubs private paths in the default value and description.

    Argument default values and "The default is ..." description text are the
    only places where dynamic private file paths can leak into the cli_tree.
    This method is called on all args.

    The test is rudimentary but effective. Any default value that looks like an
    absolute path on unix or windows is scrubbed. The default value is set to
    None and the trailing "The default ... is ..." sentence in the description,
    if any, is deleted. It's OK to be conservative here and match aggressively.
    """
    if not isinstance(self.default, basestring):
      return
    if not re.match(r'/|[A-Za-z]:\\', self.default):
      return
    self.default = None
    match = re.match(
        r'(.*\.) The default (value )?is ', self.description, re.DOTALL)
    if match:
      self.description = match.group(1)


class Flag(Argument):
  """Flag info.

  Attributes:
    attr: dict, Miscellaneous attributes.
    category: str, Category for help doc flag groupings.
    choices: list|dict, The list of static choices.
    description: str, The help text.
    group: str, Mutually exclusive flag group id, unique across all flags.
    hidden: bool, True if the flag is hidden.
    type: str, The flag value type name.
  """

  def __init__(self, flag, name):

    super(Flag, self).__init__(flag, name)
    self.attr = {}
    self.category = flag.category or ''
    self.choices = []
    self.group = ''
    self.hidden = flag.help == argparse.SUPPRESS
    # ArgParse does not have an explicit Boolean flag type. By
    # convention a flag with arg.nargs=0 and action='store_true' or
    # action='store_false' is a Boolean flag. arg.type gives no hint
    # (arg.type=bool would have been so easy) and we don't have access
    # to args.action here. Even then the flag can take on non-Boolean
    # values. If arg.default is not specified then it will be None, but
    # it can be set to anything. So we do a conservative 'truthiness'
    # test here.
    if flag.nargs == 0:
      self.type = 'bool'
      self.default = bool(flag.default)
    else:
      if (isinstance(flag.type, (int, long)) or
          isinstance(flag.default, (int, long))):
        self.type = 'int'
      elif isinstance(flag.type, float) or isinstance(flag.default, float):
        self.type = 'float'
      elif isinstance(flag.type, arg_parsers.ArgDict):
        self.type = 'dict'
      elif isinstance(flag.type, arg_parsers.ArgList):
        self.type = 'list'
      else:
        self.type = module_util.GetModulePath(flag.type) or 'string'
    if flag.choices:
      choices = sorted(flag.choices)
      if choices == ['false', 'true']:
        self.type = 'bool'
      else:
        self.choices = flag.choices
    self.required = flag.required

    if getattr(flag, 'inverted_synopsis', False):
      self.attr['inverted_synopsis'] = True
    prop, kind, value = getattr(flag, 'store_property', (None, None, None))
    if prop:
      # This allows actions.Store*Property() to be reconstituted.
      attr = {'name': str(prop)}
      if kind == 'bool':
        flag.type = 'bool'
      if value:
        attr['value'] = value
      self.attr['property'] = attr


class Positional(Argument):
  """Positional info."""

  def __init__(self, positional, name):

    super(Positional, self).__init__(positional, name)
    if positional.nargs is None:
      self.nargs = '1'
    self.required = positional.nargs not in (0, '?', '*', '...')


class Command(object):
  """Command and group info.

  Attributes:
    capsule: str, The first line of the command docstring.
    flags: {str:dict}, Command flag dict, indexed by normalized flag name.
    groups: {str:{str:...}}, Flag group attributes.
    hidden: bool, True if the command is hidden.
    name: str, The normalized name ('_' => '-').
    positionals: [dict], Command positionals list.
    release: str, The command release name {'internal', 'alpha', 'beta', 'ga'}.
    sections: {str:str}, Section help dict, indexed by section name. At minimum
      contains the DESCRIPTION section.
  """

  def __init__(self, command, parent, include_hidden_flags=True):

    self.group = isinstance(command, backend.CommandGroup)
    self.commands = {}
    self.flags = {}
    self.groups = {}
    self.hidden = command.IsHidden()
    self.name = command.name.replace('_', '-')
    self.path = command.GetPath()
    self.positionals = []
    self.release = command.ReleaseTrack().id
    self.sections = {}
    command_path_string = ' '.join(self.path)
    parent_path_string = ' '.join(parent.path) if parent else ''
    self.release, capsule = self.__Release(
        command, self.release, getattr(command, 'short_help', ''))

    # This code block must be meticulous on when and where LazyFormat expansion
    # is applied to the markdown snippets. First, no expanded text should be
    # passed as a LazyFormat kwarg. Second, no unexpanded text should appear
    # in the CLI tree. The LazyFormat calls are ordered to make sure that
    # doesn't happen.
    capsule = _NormalizeDescription(capsule)
    sections = {}
    self.release, description = self.__Release(
        command, self.release, getattr(command, 'long_help', ''))
    detailed_help = getattr(command, 'detailed_help', {})
    sections.update(detailed_help)
    description = _NormalizeDescription(description)
    if 'DESCRIPTION' not in sections:
      sections['DESCRIPTION'] = description
    notes = command.GetNotesHelpSection()
    if notes:
      sections['NOTES'] = notes
    if sections:
      for name, contents in sections.iteritems():
        # islower() section names were used to convert markdown in command
        # docstrings into the static self.section[] entries seen here.
        if name.isupper():
          self.sections[name] = console_io.LazyFormat(
              _NormalizeDescription(contents),
              command=command_path_string,
              man_name='.'.join(self.path),
              top_command=self.path[0] if self.path else '',
              parent_command=parent_path_string,
              index=capsule,
              description=description,
              **sections)
    self.capsule = console_io.LazyFormat(
        capsule,
        command=command_path_string,
        man_name='.'.join(self.path),
        top_command=self.path[0] if self.path else '',
        parent_command=parent_path_string,
        **sections)

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
        group_id[g] = '{}.{}'.format(self.name, group_id_count)
        self.groups[group_id[g]] = command.ai.group_attr[g]

    # Collect the flags.
    for arg in sorted(args.flag_args):
      for name in arg.option_strings:
        if name.startswith('--'):
          name = name.replace('_', '-')
          # Don't include ancestor flags.
          if not self.__Ancestor(name):
            flag = Flag(arg, name)
            if flag.name in group_name and group_name[flag.name] in group_id:
              flag.group = group_id[group_name[flag.name]]
            if include_hidden_flags or not flag.hidden:
              self.flags[flag.name] = flag

    # Collect the positionals.
    for arg in args.positional_args:
      name = arg.dest.replace('_', '-')
      positional = Positional(arg, name)
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
