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
import json
import os
import pprint
import re
import sys
import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.calliope import walker
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import module_util
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.resource import resource_projector
from googlecloudsdk.core.util import files


# This module is the CLI tree generator. VERSION is a stamp that is used to
# detect breaking changes. If an external CLI tree version does not exaclty
# match VERSION then it is incompatible and must be regenerated or ignored.
# Any changes to the serialized CLI dict attribute names or value semantics
# must increment VERSION. For this reason it's a monotonically increasing
# integer string and not a semver.
VERSION = '1'
DEFAULT_CLI_NAME = 'gcloud'

LOOKUP_ARGUMENTS = 'arguments'
LOOKUP_CLI_VERSION = 'CLI_VERSION'
LOOKUP_VERSION = 'VERSION'

LOOKUP_ATTR = 'attr'
LOOKUP_CAPSULE = 'capsule'
LOOKUP_CATEGORY = 'category'
LOOKUP_CHOICES = 'choices'
LOOKUP_COMMANDS = 'commands'
LOOKUP_COMPLETER = 'completer'
LOOKUP_CONSTRAINTS = 'constraints'
LOOKUP_DEFAULT = 'default'
LOOKUP_DESCRIPTION = 'description'
LOOKUP_FLAGS = 'flags'
LOOKUP_GROUP = 'group'
LOOKUP_GROUPS = 'groups'
LOOKUP_INVERTED_SYNOPSIS = 'inverted_synopsis'
LOOKUP_IS_GLOBAL = 'is_global'
LOOKUP_IS_GROUP = 'is_group'
LOOKUP_IS_HIDDEN = 'is_hidden'
LOOKUP_IS_MUTEX = 'is_mutex'
LOOKUP_IS_POSITIONAL = 'is_positional'
LOOKUP_IS_REQUIRED = 'is_required'
LOOKUP_NAME = 'name'
LOOKUP_NARGS = 'nargs'
LOOKUP_PATH = 'path'
LOOKUP_POSITIONALS = 'positionals'
LOOKUP_PROPERTY = 'property'
LOOKUP_RELEASE = 'release'
LOOKUP_REQUIRED = 'required'
LOOKUP_SECTIONS = 'sections'
LOOKUP_TYPE = 'type'
LOOKUP_VALUE = 'value'


class Error(exceptions.Error):
  """Base exception for this module."""


class SdkRootNotFoundError(Error):
  """Raised if no SDK root can be found."""


class CliTreeVersionError(Error):
  """Loaded CLI tree version mismatch."""


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
  """Group, Flag or Positional argument.

  Attributes:
    attr: dict, Miscellaneous {name: value} attributes.
    description: str, The help text.
    is_hidden: bool, True if the argument help text is disabled.
    is_group: bool, True if this is an argument group.
    is_positional: bool, True if this is a positional argument.
    is_mutex: bool, True if this is a mutex group.
    is_required: bool, The argument must be specified.
  """

  def __init__(self, arg):

    self.attr = {}
    self.description = _NormalizeDescription(_GetDescription(arg))
    self.is_group = False
    self.is_hidden = arg.help == argparse.SUPPRESS
    self.is_positional = False
    self.is_mutex = getattr(arg, 'is_mutex', getattr(arg, 'mutex', False))
    self.is_required = arg.is_required

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


class FlagOrPositional(Argument):
  """Group, Flag or Positional argument.

  Attributes:
    category: str, The argument help category name.
    completer: str, Resource completer module path.
    default: (self.type), The default flag value or None if no default.
    description: str, The help text.
    name: str, The normalized name ('_' => '-').
    nargs: {0, 1, '?', '*', '+'}
    value: str, The argument value documentation name.
  """

  def __init__(self, arg, name):

    super(FlagOrPositional, self).__init__(arg)
    self.category = getattr(arg, LOOKUP_CATEGORY, '')
    completer = getattr(arg, LOOKUP_COMPLETER, None)
    if completer:
      try:
        # A calliope.parser_completer.ArgumentCompleter object.
        completer_class = completer.completer_class
      except AttributeError:
        # An argparse callable completer.
        completer_class = completer
      completer = module_util.GetModulePath(completer_class)
    self.completer = completer
    self.default = arg.default
    self.description = _NormalizeDescription(_GetDescription(arg))
    self.name = name
    self.nargs = str(arg.nargs or 0)
    if arg.metavar:
      self.value = arg.metavar
    else:
      self.value = name.lstrip('-').replace('-', '_').upper()
    self._Scrub()


class Flag(FlagOrPositional):
  """Flag info.

  Attributes:
    choices: list|dict, The list of static choices.
    is_global: bool, True if the flag is global (inherited from the root).
    type: str, The flag value type name.
  """

  def __init__(self, flag, name):

    super(Flag, self).__init__(flag, name)
    self.choices = []
    self.is_global = flag.is_global
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

    if getattr(flag, LOOKUP_INVERTED_SYNOPSIS, False):
      self.attr[LOOKUP_INVERTED_SYNOPSIS] = True
    prop, kind, value = getattr(flag, 'store_property', (None, None, None))
    if prop:
      # This allows actions.Store*Property() to be reconstituted.
      attr = {LOOKUP_NAME: str(prop)}
      if kind == 'bool':
        flag.type = 'bool'
      if value:
        attr[LOOKUP_VALUE] = value
      self.attr[LOOKUP_PROPERTY] = attr


class Positional(FlagOrPositional):
  """Positional info."""

  def __init__(self, positional, name):

    super(Positional, self).__init__(positional, name)
    self.is_positional = True
    if positional.nargs is None:
      self.nargs = '1'
    self.is_required = positional.nargs not in (0, '?', '*', '...')


class Group(Argument):
  """Makes a constraint group from a command argument interceptor.

  Attributes:
    arguments: [Argument], The list of arguments in the argument group.
  """

  def __init__(self, group, arguments=None):
    super(Group, self).__init__(group)
    self.is_group = True
    self.arguments = arguments


class Constraint(Group):
  """Argument constraint group info."""

  def __init__(self, group):
    arguments = []
    for arg in group.arguments:
      if arg.is_group:
        arguments.append(Constraint(arg))
      elif arg.is_positional:
        name = arg.dest.replace('_', '-')
        arguments.append(Positional(arg, name))
      else:
        for name in arg.option_strings:
          if name.startswith('--'):
            name = name.replace('_', '-')
            arguments.append(Flag(arg, name))
    super(Constraint, self).__init__(group, arguments=arguments)


class Command(object):
  """Command/group info.

  Attributes:
    capsule: str, The first line of the command docstring.
    commands: {name:Command}, The subcommands in a command group.
    constraints: [Argument], Argument constraint tree.
    flags: {str:Flag}, Command flag dict, indexed by normalized flag name.
    is_global: bool, True if the command is the root command.
    is_hidden: bool, True if the command is hidden.
    name: str, The normalized name ('_' => '-').
    positionals: [dict], Command positionals list.
    release: str, The command release name {'internal', 'alpha', 'beta', 'ga'}.
    sections: {str:str}, Section help dict, indexed by section name. At minimum
      contains the DESCRIPTION section.
  """

  def __init__(self, command, parent):

    self.commands = {}
    self.flags = {}
    self.is_global = not bool(parent)
    self.is_group = command.is_group
    self.is_hidden = command.IsHidden()
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
              index=capsule,
              description=description,
              parent_command=parent_path_string)
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

    # Collect the command specific flags.
    for arg in args.flag_args:
      for name in arg.option_strings:
        if name.startswith('--'):
          # Don't include ancestor flags, with the exception of --help.
          if name != '--help' and self.__Ancestor(name):
            continue
          name = name.replace('_', '-')
          flag = Flag(arg, name)
          self.flags[flag.name] = flag

    # Collect the ancestor flags.
    for arg in args.ancestor_flag_args:
      for name in arg.option_strings:
        if name.startswith('--'):
          name = name.replace('_', '-')
          flag = Flag(arg, name)
          self.flags[flag.name] = flag

    # Collect the positionals.
    for arg in args.positional_args:
      name = arg.dest.replace('_', '-')
      positional = Positional(arg, name)
      self.positionals.append(positional)

    # Collect the arg group constraints.
    self.constraints = Constraint(args)

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


class CliTreeGenerator(walker.Walker):
  """Generates an external representation of the gcloud CLI tree.

  This implements the resource generator for gcloud meta list-gcloud.
  """

  def __init__(self, cli=None, branch=None, *args, **kwargs):
    """branch is the command path of the CLI subtree to generate."""
    super(CliTreeGenerator, self).__init__(*args, cli=cli, **kwargs)
    self._branch = branch

  def Visit(self, node, parent, is_group):
    """Visits each node in the CLI command tree to construct the external rep.

    Args:
      node: group/command CommandCommon info.
      parent: The parent Visit() return value, None at the top level.
      is_group: True if node is a command group.

    Returns:
      The subtree parent value, used here to construct an external rep node.
    """
    if self._Prune(node):
      return parent
    return Command(node, parent)

  def _Prune(self, command):
    """Returns True if command should be pruned from the CLI tree.

    Branch pruning is mainly for generating static unit test data. The static
    tree for the entire CLI would be an unnecessary burden on the depot.

    self._branch, if not None, is already split into a path with the first
    name popped. If branch is not a prefix of command.GetPath()[1:] it will
    be pruned.

    Args:
      command: The calliope Command object to check.

    Returns:
      True if command should be pruned from the CLI tree.
    """
    # Only prune if branch is not empty.
    if not self._branch:
      return False
    path = command.GetPath()
    # The top level command is never pruned.
    if len(path) < 2:
      return False
    path = path[1:]
    # All tracks in the branch are active.
    if path[0] in ('alpha', 'beta'):
      path = path[1:]
    for name in self._branch:
      # branch is longer than path => don't prune.
      if not path:
        return False
      # prefix mismatch => prune.
      if path[0] != name:
        return True
      path.pop(0)
    # branch is a prefix of path => don't prune.
    return False


_LOOKUP_SERIALIZED_FLAG_LIST = 'SERIALIZED_FLAG_LIST'


def _Serialize(tree):
  """Returns the CLI tree optimized for serialization.

  Serialized data does not support pointers. The CLI tree can have a lot of
  redundant data, especially with ancestor flags included with each command.
  This function collects the flags into the _LOOKUP_SERIALIZED_FLAG_LIST array
  in the root node and converts the flags dict values to indices into that
  array.

  Serialization saves a lot of space and allows the ancestor flags to be
  included in the LOOKUP_FLAGS dict of each command. It also saves time for
  users of the tree because the LOOKUP_FLAGS dict also contains the ancestor
  flags.

  Apply this function to the CLI tree just before dumping. For the 2017-03
  gcloud CLI with alpha and beta included and all ancestor flags included in
  each command node this function reduces the generation time from
  ~2m40s to ~35s and the dump file size from 35Mi to 4.3Mi.

  Args:
    tree: The CLI tree to be optimized.

  Returns:
    The CLI tree optimized for serialization.
  """
  # If tree is already serialized we're done.
  if getattr(tree, _LOOKUP_SERIALIZED_FLAG_LIST, None):
    return tree

  # Collect the dict of all flags.
  all_flags = {}

  class _FlagIndex(object):
    """Flag index + definition."""

    def __init__(self, flag):
      self.flag = flag
      self.index = 0

  def _FlagIndexKey(flag):
    return '::'.join([
        str(flag.name),
        str(flag.attr),
        str(flag.category),
        str(flag.choices),
        str(flag.completer),
        str(flag.default),
        str(flag.description),
        str(flag.is_hidden),
        str(flag.is_global),
        str(flag.is_group),
        str(flag.is_required),
        str(flag.nargs),
        str(flag.type),
        str(flag.value),
    ])

  def _CollectAllFlags(command):
    for flag in command.flags.values():
      all_flags[_FlagIndexKey(flag)] = _FlagIndex(flag)
    for subcommand in command.commands.values():
      _CollectAllFlags(subcommand)

  _CollectAllFlags(tree)

  # Order the dict into the ordered tree _LOOKUP_SERIALIZED_FLAG_LIST list and
  # assign ordered indices to the all_flags dict entry. The indices are ordered
  # for reproducable serializations for testing.
  all_flags_list = []
  for index, key in enumerate(sorted(all_flags)):
    fi = all_flags[key]
    fi.index = index
    all_flags_list.append(fi.flag)

  # Replace command flags dict values by the _LOOKUP_SERIALIZED_FLAG_LIST index.
  # Negative indices index into the command positionals.

  def _ReplaceConstraintFlagWithIndex(arguments):
    positional_index = 0
    for i, arg in enumerate(arguments):
      if isinstance(arg, int):
        pass
      elif arg.is_group:
        _ReplaceConstraintFlagWithIndex(arg.arguments)
      elif arg.is_positional:
        positional_index -= 1
        arguments[i] = positional_index
      else:
        try:
          arguments[i] = all_flags[_FlagIndexKey(arg)].index
        except KeyError:
          pass

  def _ReplaceFlagWithIndex(command):
    for name, flag in command.flags.iteritems():
      command.flags[name] = all_flags[_FlagIndexKey(flag)].index
      _ReplaceConstraintFlagWithIndex(command.constraints.arguments)
    for subcommand in command.commands.values():
      _ReplaceFlagWithIndex(subcommand)

  _ReplaceFlagWithIndex(tree)

  setattr(tree, _LOOKUP_SERIALIZED_FLAG_LIST, all_flags_list)
  setattr(tree, LOOKUP_VERSION, VERSION)

  return tree


def _DumpToFile(tree, name, f):
  """Dump helper."""
  f.write('''\
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

"""{} CLI tree."""

# pylint: disable=bad-continuation,line-too-long

LOOKUP_ARGUMENTS = '{}'
LOOKUP_COMMANDS = '{}'
LOOKUP_CONSTRAINTS = '{}'
LOOKUP_FLAGS = '{}'
LOOKUP_IS_GROUP = '{}'
LOOKUP_POSITIONALS = '{}'
_LOOKUP_SERIALIZED_FLAG_LIST = '{}'

_SERIALIZED_TREE = '''.format(
    name,
    LOOKUP_ARGUMENTS,
    LOOKUP_COMMANDS,
    LOOKUP_CONSTRAINTS,
    LOOKUP_FLAGS,
    LOOKUP_IS_GROUP,
    LOOKUP_POSITIONALS,
    _LOOKUP_SERIALIZED_FLAG_LIST))
  pprint.pprint(resource_projector.MakeSerializable(_Serialize(tree)), stream=f)
  f.write('''

def _Deserialize(tree):
  """Returns the deserialization of a serialized CLI tree."""
  all_flags_list = tree.get(_LOOKUP_SERIALIZED_FLAG_LIST)
  if not all_flags_list:
    # If tree wasn't serialized we're done.
    return tree
  tree[_LOOKUP_SERIALIZED_FLAG_LIST] = None
  del tree[_LOOKUP_SERIALIZED_FLAG_LIST]

  def _ReplaceConstraintIndexWithArgReference(arguments, positionals):
    for i, arg in enumerate(arguments):
      if isinstance(arg, int):
        if arg < 0:  # a positional index
          arguments[i] = positionals[-(arg + 1)]
        else:  # a flag index
          arguments[i] = all_flags_list[arg]
      elif arg.get(LOOKUP_IS_GROUP, False):
        _ReplaceConstraintIndexWithArgReference(
            arg.get(LOOKUP_ARGUMENTS), positionals)

  def _ReplaceIndexWithFlagReference(command):
    flags = command[LOOKUP_FLAGS]
    for name, index in flags.iteritems():
      flags[name] = all_flags_list[index]
    arguments = command[LOOKUP_CONSTRAINTS][LOOKUP_ARGUMENTS]
    _ReplaceConstraintIndexWithArgReference(
        arguments, command[LOOKUP_POSITIONALS])
    for subcommand in command[LOOKUP_COMMANDS].values():
      _ReplaceIndexWithFlagReference(subcommand)

  _ReplaceIndexWithFlagReference(tree)

  return tree


TREE = _Deserialize(_SERIALIZED_TREE)
''')


def CliTreeDir():
  """Creates if necessary and returns the CLI tree default directory.

  This directory is part of the installation and its contents are managed
  by the installer/updater.

  Raises:
    SdkRootNotFoundError: If the SDK root directory does not exist.

  Returns:
    The directory path.
  """
  paths = config.Paths()
  if paths.sdk_root is None:
    raise SdkRootNotFoundError('SDK root not found for this installation. '
                               'CLI tree cannot be generated.')
  directory = os.path.join(paths.sdk_root, paths.CLOUDSDK_STATE_DIR, 'cli')
  # Ensure directory exists.
  files.MakeDir(directory)
  return directory


def CliTreeConfigDir():
  """Returns the CLI tree config directory.

  This directory is part of the user config directory its contents are stable
  across releases/installations/updates.

  Returns:
    The directory path.
  """
  return os.path.join(config.Paths().global_config_dir, 'cli')


def CliTreePath(name=DEFAULT_CLI_NAME):
  """Returns the default CLI tree module path for name."""
  return os.path.join(CliTreeDir(), name + '.py')


def _GenerateRoot(cli, path=None, name=DEFAULT_CLI_NAME, branch=None):
  """Generates and returns the CLI root for name."""
  if path == '-':
    message = 'Generating the {} CLI'.format(name)
  elif path:
    message = 'Generating the {} CLI and caching in [{}]'.format(name, path)
  else:
    message = 'Generating the {} CLI for one-time use (no SDK root)'.format(
        name)
  with progress_tracker.ProgressTracker(message):
    return CliTreeGenerator(cli, branch=branch).Walk(hidden=True)


def Dump(cli, path=None, name=DEFAULT_CLI_NAME, branch=None):
  """Dumps the CLI tree to a Python file.

  The tree is processed by cli_tree._Serialize() to minimize the JSON file size
  and generation time.

  Args:
    cli: The CLI.
    path: The Python file path to dump to, the standard output if '-', the
      default CLI tree path if None.
    name: The CLI name.
    branch: The path of the CLI subtree to generate.

  Returns:
    The generated CLI tree.
  """
  if path is None:
    path = CliTreePath()
  tree = _GenerateRoot(cli=cli, path=path, name=name, branch=branch)
  if path == '-':
    _DumpToFile(tree, name, sys.stdout)
  else:
    with open(path, 'w') as f:
      _DumpToFile(tree, name, f)
    module_util.CompileAll(os.path.dirname(path))
  return resource_projector.MakeSerializable(tree)


def Load(path=None, cli=None, one_time_use_ok=False):
  """Loads a CLI tree from the Python file path.

  Args:
    path: The path name of the Python file the CLI tree was dumped to. None
      for the default CLI tree path.
    cli: The CLI. If not None and path fails to import, a new CLI tree is
      generated, written to path, and returned.
    one_time_use_ok: If True and the load fails then the CLI tree is generated
      on the fly for one time use.

  Raises:
    CliTreeVersionError: loaded tree version mismatch
    ImportModuleError: import errors

  Returns:
    The CLI tree.
  """
  if path is None:
    try:
      path = CliTreePath()
    except SdkRootNotFoundError:
      if cli and one_time_use_ok:
        tree = _GenerateRoot(cli)
        setattr(tree, LOOKUP_VERSION, VERSION)
        return resource_projector.MakeSerializable(tree)
      raise
  while True:
    # This loop executes 1 or 2 times, the second time either succeeds in
    # loading the newly created CLI tree or fails with an import exception.
    try:
      tree = module_util.ImportPath(path).TREE
      version = tree.get(LOOKUP_VERSION)
      if version == VERSION:
        return tree
      del tree
      if not cli:
        raise CliTreeVersionError(
            'CLI tree [{}] version is [{}], expected [{}]'.format(
                path, version, VERSION))
      # The CLI tree exists but doesn't match VERSION. Clobber path to make
      # sure it's regenerated.
      try:
        os.remove(path)
      except OSError:
        pass
    except module_util.ImportModuleError:
      if not cli:
        raise
    Dump(cli=cli, path=path)
    cli = None


def Node(command=None, commands=None, constraints=None, flags=None, path=None,
         positionals=None, description=None):
  """Creates and returns a CLI tree node dict."""
  path = []
  if command:
    path.append(command)
    if not description:
      description = 'The {} command.'.format(command)
  return {
      LOOKUP_CAPSULE: '',
      LOOKUP_COMMANDS: commands or {},
      LOOKUP_CONSTRAINTS: constraints or {},
      LOOKUP_FLAGS: flags or {},
      LOOKUP_IS_GROUP: True,
      LOOKUP_IS_HIDDEN: False,
      LOOKUP_PATH: path,
      LOOKUP_POSITIONALS: positionals or {},
      LOOKUP_RELEASE: 'GA',
      LOOKUP_SECTIONS: {'DESCRIPTION': description},
  }


def LoadAll(directory=None, root=None, cli=None):
  """Loads all CLI trees in directory and adds them to tree.

  Args:
    directory: The config directory containing the CLI tree modules.
    root: dict, The CLI root to update. A new root is created if None.
    cli: The CLI. If not None and DEFAULT_CLI_NAME fails to import, a new CLI
    tree is generated, written to path, and added to clis.

  Raises:
    CliTreeVersionError: loaded tree version mismatch
    ImportModuleError: import errors

  Returns:
    The CLI tree.
  """
  # Create the root node if needed.
  if root is None:
    root = Node(description='The CLI tree root.')

  # Always load the default CLI.
  if DEFAULT_CLI_NAME not in root[LOOKUP_COMMANDS]:
    root[LOOKUP_COMMANDS][DEFAULT_CLI_NAME] = Load(
        cli=cli, one_time_use_ok=True)

  # Load extra CLIs by searching directories in order. .py, .pyc, and .json
  # files are treated as CLI modules/data, where the file base name is the name
  # of the CLI root command.
  directories = [
      directory,  # Explicit caller override dir
      CliTreeConfigDir(),  # User config dir shared across installations
      CliTreeDir(),  # Installation dir controlled by the updater
  ]

  loaded = {DEFAULT_CLI_NAME}  # Already loaded this above.
  for directory in directories:
    if not directory or not os.path.exists(directory):
      continue
    for (dirpath, _, filenames) in os.walk(directory):
      for filename in sorted(filenames):  # For stability across runs.
        base, extension = os.path.splitext(filename)
        if base in loaded:
          # Already loaded. Earlier directory hits take precedence.
          continue
        loaded.add(base)
        path = os.path.join(dirpath, filename)
        if extension == '.py':
          tree = Load(path)
        elif extension == '.json':
          with open(path, 'r') as f:
            tree = json.loads(f.read())
          version = tree.get(LOOKUP_VERSION)
          if version != VERSION:
            del tree
            raise CliTreeVersionError(
                'CLI tree [{}] version is [{}], expected [{}].'.format(
                    path, version, VERSION))
        root[LOOKUP_COMMANDS][base] = tree
      # Don't search subdirectories.
      break

  return root
