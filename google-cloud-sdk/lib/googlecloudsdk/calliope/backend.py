# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Backend stuff for the calliope.cli module.

Not to be used by mortals.

"""

import argparse
import os
import re
import sys

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import display
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core.util import pkg_resources


class LayoutException(Exception):
  """LayoutException is for problems with module directory structure."""
  pass


class CommandLoadFailure(Exception):
  """An exception for when a command or group module cannot be imported."""

  def __init__(self, command, root_exception):
    self.command = command
    self.root_exception = root_exception
    super(CommandLoadFailure, self).__init__(
        'Problem loading {command}: {issue}.'.format(
            command=command, issue=str(root_exception)))


class CommandCommon(object):
  """A base class for CommandGroup and Command.

  It is responsible for extracting arguments from the modules and does argument
  validation, since this is always the same for groups and commands.
  """

  def __init__(self, common_type, path, release_track, cli_generator,
               parser_group, allow_positional_args, parent_group):
    """Create a new CommandCommon.

    Args:
      common_type: base._Command, The actual loaded user written command or
        group class.
      path: [str], Similar to module_path, but is the path to this command or
        group with respect to the CLI itself.  This path should be used for
        things like error reporting when a specific element in the tree needs
        to be referenced.
      release_track: base.ReleaseTrack, The release track (ga, beta, alpha,
        preview) that this command group is in.  This will apply to all commands
        under it.
      cli_generator: cli.CLILoader, The builder used to generate this CLI.
      parser_group: argparse.Parser, The parser that this command or group will
        live in.
      allow_positional_args: bool, True if this command can have positional
        arguments.
      parent_group: CommandGroup, The parent of this command or group. None if
        at the root.
    """
    self._parent_group = parent_group

    self.name = path[-1]
    # For the purposes of argparse and the help, we should use dashes.
    self.cli_name = self.name.replace('_', '-')
    log.debug('Loaded Command Group: %s', path)
    path[-1] = self.cli_name
    self._path = path
    self.dotted_name = '.'.join(path)
    self._cli_generator = cli_generator

    # pylint: disable=protected-access
    self._common_type = common_type
    self._common_type._cli_generator = cli_generator
    self._common_type._release_track = release_track

    if parent_group:
      # Propagate down the hidden attribute.
      if parent_group.IsHidden():
        self._common_type._is_hidden = True
      # Propagate down the unicode supported attribute.
      if parent_group.IsUnicodeSupported():
        self._common_type._is_unicode_supported = True
      # Propagate down notices from the deprecation decorator.
      if parent_group.Notices():
        for tag, msg in parent_group.Notices().iteritems():
          self._common_type.AddNotice(tag, msg)

    self.detailed_help = getattr(self._common_type, 'detailed_help', {})
    self._ExtractHelpStrings(self._common_type.__doc__)

    self._AssignParser(
        parser_group=parser_group,
        allow_positional_args=allow_positional_args)

  def Notices(self):
    """Gets the notices of this command or group."""
    return self._common_type.Notices()

  def ReleaseTrack(self):
    """Gets the release track of this command or group."""
    return self._common_type.ReleaseTrack()

  def IsHidden(self):
    """Gets the hidden status of this command or group."""
    return self._common_type.IsHidden()

  def IsUnicodeSupported(self):
    """Gets the unicode supported status of this command or group."""
    return self._common_type.IsUnicodeSupported()

  def IsRoot(self):
    """Returns True if this is the root element in the CLI tree."""
    return not self._parent_group

  def _TopCLIElement(self):
    """Gets the top group of this CLI."""
    if self.IsRoot():
      return self
    # pylint: disable=protected-access
    return self._parent_group._TopCLIElement()

  def _ExtractHelpStrings(self, docstring):
    """Extracts short help, long help and man page index from a docstring.

    Sets self.short_help, self.long_help and self.index_help and adds release
    track tags if needed.

    Args:
      docstring: The docstring from which short and long help are to be taken
    """
    self.short_help, self.long_help = usage_text.ExtractHelpStrings(docstring)

    if 'brief' in self.detailed_help:
      self.short_help = re.sub(r'\s', ' ', self.detailed_help['brief']).strip()
    if self.short_help and not self.short_help.endswith('.'):
      self.short_help += '.'

    # Append any notice messages to command description and long_help
    if self.Notices():
      all_notices = ('\n\n' +
                     '\n\n'.join(sorted(self.Notices().values())) +
                     '\n\n')
      if 'DESCRIPTION' in self.detailed_help:
        self.detailed_help['DESCRIPTION'] = (self.short_help +
                                             all_notices +
                                             self.detailed_help['DESCRIPTION'])
      if self.short_help == self.long_help:
        self.long_help += all_notices
      else:
        self.long_help = self.short_help + all_notices + self.long_help

    self.index_help = self.short_help
    if len(self.index_help) > 1:
      if self.index_help[0].isupper() and not self.index_help[1].isupper():
        self.index_help = self.index_help[0].lower() + self.index_help[1:]
      if self.index_help[-1] == '.':
        self.index_help = self.index_help[:-1]

    # Add an annotation to the help strings to mark the release stage.
    # TODO(user):b/32361958: Clean Up ReleaseTracks to Leverage Notices().
    tag = self.ReleaseTrack().help_tag
    if self.Notices():
      notice_tags = ' '.join(sorted(self.Notices().keys()))
      tag = tag +' '+ notice_tags if tag else notice_tags

    if tag:
      self.short_help = tag + self.short_help
      self.long_help = tag + self.long_help
      # TODO(user): Work around related to b/32361958 to avoid overwriting
      # all help files
      if 'DESCRIPTION' in self.detailed_help and self.Notices():
        self.detailed_help['DESCRIPTION'] = (tag +
                                             self.detailed_help['DESCRIPTION'])
      # TODO(user):b/21208128: Drop these 4 lines.
      prefix = self.ReleaseTrack().prefix
      if len(self._path) < 2 or self._path[1] != prefix:
        self.index_help = tag + self.index_help

  def _AssignParser(self, parser_group, allow_positional_args):
    """Assign a parser group to model this Command or CommandGroup.

    Args:
      parser_group: argparse._ArgumentGroup, the group that will model this
          command or group's arguments.
      allow_positional_args: bool, Whether to allow positional args for this
          group or not.

    """
    if not parser_group:
      # This is the root of the command tree, so we create the first parser.
      self._parser = parser_extensions.ArgumentParser(
          description=self.long_help,
          add_help=False,
          prog=self.dotted_name,
          calliope_command=self)
    else:
      # This is a normal sub group, so just add a new subparser to the existing
      # one.
      self._parser = parser_group.add_parser(
          self.cli_name,
          help=self.short_help,
          description=self.long_help,
          add_help=False,
          prog=self.dotted_name,
          calliope_command=self)

    self._sub_parser = None

    self.ai = parser_arguments.ArgumentInterceptor(
        parser=self._parser,
        is_root=not parser_group,
        cli_generator=self._cli_generator,
        allow_positional=allow_positional_args)

    self.ai.add_argument(
        '-h', action=actions.ShortHelpAction(self),
        is_replicated=True,
        category=base.COMMONLY_USED_FLAGS,
        help='Print a summary help and exit.')
    self.ai.add_argument(
        '--help', action=actions.RenderDocumentAction(self, '--help'),
        is_replicated=True,
        category=base.COMMONLY_USED_FLAGS,
        help='Display detailed help.')
    self.ai.add_argument(
        '--document', action=actions.RenderDocumentAction(self),
        is_replicated=True,
        nargs=1,
        metavar='ATTRIBUTES',
        type=arg_parsers.ArgDict(),
        help=argparse.SUPPRESS)

    self._AcquireArgs()

  def IsValidSubPath(self, command_path):
    """Determines if the given sub command path is valid from this node.

    Args:
      command_path: [str], The pieces of the command path.

    Returns:
      True, if the given path parts exist under this command or group node.
      False, if the sub path does not lead to a valid command or group.
    """
    current = self
    for part in command_path:
      current = current.LoadSubElement(part)
      if not current:
        return False
    return True

  def AllSubElements(self):
    """Gets all the sub elements of this group.

    Returns:
      set(str), The names of all sub groups or commands under this group.
    """
    return []

  def LoadAllSubElements(self, recursive=False):
    """Load all the sub groups and commands of this group."""
    pass

  def LoadSubElement(self, name, allow_empty=False):
    """Load a specific sub group or command.

    Args:
      name: str, The name of the element to load.
      allow_empty: bool, True to allow creating this group as empty to start
        with.

    Returns:
      _CommandCommon, The loaded sub element, or None if it did not exist.
    """
    pass

  def LoadSubElementByPath(self, path):
    """Load a specific sub group or command by path.

    If path is empty, returns the current element.

    Args:
      path: list of str, The names of the elements to load down the hierarchy.

    Returns:
      _CommandCommon, The loaded sub element, or None if it did not exist.
    """
    curr = self
    for part in path:
      curr = curr.LoadSubElement(part)
      if curr is None:
        return None
    return curr

  def GetPath(self):
    return self._path

  def GetUsage(self):
    return usage_text.GetUsage(self, self.ai)

  def GetSubCommandHelps(self):
    return {}

  def GetSubGroupHelps(self):
    return {}

  def _GetModuleFromPath(self, module_dir, module_path, path, construction_id):
    """Import the module and dig into it to return the namespace we are after.

    Import the module relative to the top level directory.  Then return the
    actual module corresponding to the last bit of the path.

    Args:
      module_dir: str, The path to the tools directory that this command or
        group lives within.
      module_path: [str], The command group names that brought us down to this
        command group or command from the top module directory.
      path: [str], The same as module_path but with the groups named as they
        will be in the CLI.
      construction_id: str, A unique identifier for the CLILoader that is
        being constructed.

    Returns:
      The imported module.
    """
    # Make sure this module name never collides with any real module name.
    # Use the CLI naming path, so values are always unique.
    name_to_give = '__calliope__command__.{construction_id}.{name}'.format(
        construction_id=construction_id,
        name='.'.join(path).replace('-', '_'))
    try:
      return pkg_resources.GetModuleFromPath(
          name_to_give, os.path.join(module_dir, *module_path))
    # pylint:disable=broad-except, We really do want to catch everything here,
    # because if any exceptions make it through for any single command or group
    # file, the whole CLI will not work. Instead, just log whatever it is.
    except Exception as e:
      _, _, exc_traceback = sys.exc_info()
      raise CommandLoadFailure('.'.join(path), e), None, exc_traceback

  def _AcquireArgs(self):
    """Calls the functions to register the arguments for this module."""
    # A Command subclass can define a _Flags() method.
    # Calliope sets up _Flags() and should not affect the legacy setting.
    legacy = self.ai.display_info.legacy
    self._common_type._Flags(self.ai)  # pylint: disable=protected-access
    self.ai.display_info.legacy = legacy
    # A command implementation can optionally define an Args() method.
    self._common_type.Args(self.ai)

    if self._parent_group:
      # Add parent flags to children, if they aren't represented already
      for flag in self._parent_group.GetAllAvailableFlags():
        if flag.is_replicated:
          # Each command or group gets its own unique help flags.
          continue
        if flag.do_not_propagate:
          # Don't propagate down flags that only apply to the group but not to
          # subcommands.
          continue
        if flag.required:
          # It is not easy to replicate required flags to subgroups and
          # subcommands, since then there would be two+ identical required
          # flags, and we'd want only one of them to be necessary.
          continue
        try:
          self.ai.AddFlagActionFromAncestors(flag)
        except argparse.ArgumentError:
          raise parser_errors.ArgumentException(
              'repeated flag in {command}: {flag}'.format(
                  command=self.dotted_name,
                  flag=flag.option_strings))
      # Update parent display_info in children, children take precedence.
      self.ai.display_info.AddLowerDisplayInfo(
          self._parent_group.ai.display_info)

  def GetAllAvailableFlags(self):
    return self.ai.flag_args + self.ai.ancestor_flag_args

  def GetSpecificFlags(self, include_hidden=True):
    if include_hidden:
      return self.ai.flag_args
    return [f for f in self.ai.flag_args if f.help != argparse.SUPPRESS]


class CommandGroup(CommandCommon):
  """A class to encapsulate a group of commands."""

  def __init__(self, module_dir, module_path, path, release_track,
               construction_id, cli_generator, parser_group, parent_group=None,
               allow_empty=False):
    """Create a new command group.

    Args:
      module_dir: always the root of the whole command tree
      module_path: a list of command group names that brought us down to this
        command group from the top module directory
      path: similar to module_path, but is the path to this command group
        with respect to the CLI itself.  This path should be used for things
        like error reporting when a specific element in the tree needs to be
        referenced
      release_track: base.ReleaseTrack, The release track (ga, beta, alpha) that
        this command group is in.  This will apply to all commands under it.
      construction_id: str, A unique identifier for the CLILoader that is
        being constructed.
      cli_generator: cli.CLILoader, The builder used to generate this CLI.
      parser_group: the current argparse parser, or None if this is the root
        command group.  The root command group will allocate the initial
        top level argparse parser.
      parent_group: CommandGroup, The parent of this group. None if at the
        root.
      allow_empty: bool, True to allow creating this group as empty to start
        with.

    Raises:
      LayoutException: if the module has no sub groups or commands
    """
    # pylint:disable=protected-access, The base module is effectively an
    # extension of calliope, and we want to leave _Common private so people
    # don't extend it directly.
    common_type = base._Common.FromModule(
        self._GetModuleFromPath(module_dir, module_path, path, construction_id),
        release_track,
        is_command=False)
    super(CommandGroup, self).__init__(
        common_type,
        path=path,
        release_track=release_track,
        cli_generator=cli_generator,
        allow_positional_args=False,
        parser_group=parser_group,
        parent_group=parent_group)

    self._module_dir = module_dir
    self._module_path = module_path
    self._construction_id = construction_id

    # find sub groups and commands
    self.groups = {}
    self.commands = {}
    self._groups_to_load = {}
    self._commands_to_load = {}
    self._unloadable_elements = set()
    self._FindSubElements()
    if (not allow_empty and
        not self._groups_to_load and not self._commands_to_load):
      raise LayoutException('Group %s has no subgroups or commands'
                            % self.dotted_name)
    # Initialize the sub-parser so sub groups can be found.
    self.SubParser()

  def _FindSubElements(self):
    """Final all the sub groups and commands under this group.

    Raises:
      LayoutException: if there is a command or group with an illegal name.
    """
    location = os.path.join(self._module_dir, *self._module_path)
    groups, commands = pkg_resources.ListPackage(location)

    for collection in [groups, commands]:
      for name in collection:
        if re.search('[A-Z]', name):
          raise LayoutException('Commands and groups cannot have capital '
                                'letters: %s.' % name)

    for group_info in self._GetSubPathForNames(groups):
      self.AddSubGroup(group_info)
    for command_info in self._GetSubPathForNames(commands):
      self.AddSubCommand(command_info)

  def _GetSubPathForNames(self, names):
    """Gets a list of (module path, path) for the sub names.

    Args:
      names: [str], The names of the sub groups or commands the paths are for.

    Returns:
      A list of tuples of (module_dir, module_path, name, release_track) for the
      given names. These terms are that as used by the constructor of
      CommandGroup and Command.
    """
    return [(self._module_dir, self._module_path + [name], name,
             self.ReleaseTrack())
            for name in names]

  def AddSubGroup(self, group_info):
    """Merges another command group under this one.

    If we load command groups for alternate locations, this method is used to
    make those extra sub groups fall under this main group in the CLI.

    Args:
      group_info: A tuple of (module_dir, module_path, name, release_track).
        The arguments used by the LoadSubElement() method for lazy loading this
        group.
    """
    name = group_info[2]
    self._groups_to_load[name] = group_info

  def AddSubCommand(self, command_info):
    """Merges another command group under this one.

    If we load commands for alternate locations, this method is used to
    make those extra sub commands fall under this main group in the CLI.

    Args:
      command_info: A tuple of (module_dir, module_path, name, release_track).
        The arguments used by the LoadSubElement() method for lazy loading this
        command.
    """
    name = command_info[2]
    self._commands_to_load[name] = command_info

  def CopyAllSubElementsTo(self, other_group, ignore):
    """Copies all the sub groups and commands from this group to the other.

    Args:
      other_group: CommandGroup, The other group to populate.
      ignore: set(str), Names of elements not to copy.
    """
    # pylint: disable=protected-access
    collections_to_update = [
        (self._groups_to_load, other_group._groups_to_load),
        (self._commands_to_load, other_group._commands_to_load)]

    for src, dst in collections_to_update:
      for name, info in src.iteritems():
        if name in ignore:
          continue
        (module_dir, module_path, name, unused_track) = info
        dst[name] = (module_dir, module_path, name,
                     other_group.ReleaseTrack())

  def SubParser(self):
    """Gets or creates the argparse sub parser for this group.

    Returns:
      The argparse subparser that children of this group should register with.
          If a sub parser has not been allocated, it is created now.
    """
    if not self._sub_parser:
      # pylint: disable=protected-access
      self._sub_parser = self._parser.add_subparsers(
          action=parser_extensions.CloudSDKSubParsersAction,
          calliope_command=self)
    return self._sub_parser

  def AllSubElements(self):
    """Gets all the sub elements of this group.

    Returns:
      set(str), The names of all sub groups or commands under this group.
    """
    return (set(self._groups_to_load.keys()) |
            set(self._commands_to_load.keys()))

  def IsValidSubElement(self, name):
    """Determines if the given name is a valid sub group or command.

    Args:
      name: str, The name of the possible sub element.

    Returns:
      bool, True if the name is a valid sub element of this group.
    """
    return bool(self.LoadSubElement(name))

  def LoadAllSubElements(self, recursive=False):
    """Load all the sub groups and commands of this group."""
    for name in self.AllSubElements():
      element = self.LoadSubElement(name)
      if element and recursive:
        element.LoadAllSubElements(recursive=recursive)

  def LoadSubElement(self, name, allow_empty=False):
    """Load a specific sub group or command.

    Args:
      name: str, The name of the element to load.
      allow_empty: bool, True to allow creating this group as empty to start
        with.

    Returns:
      _CommandCommon, The loaded sub element, or None if it did not exist.
    """
    name = name.replace('-', '_')

    # See if this element has already been loaded.
    existing = self.groups.get(name, None)
    if not existing:
      existing = self.commands.get(name, None)
    if existing:
      return existing
    if name in self._unloadable_elements:
      return None

    element = None
    try:
      if name in self._groups_to_load:
        (module_dir, module_path, name, track) = self._groups_to_load[name]
        element = CommandGroup(
            module_dir, module_path, self._path + [name], track,
            self._construction_id, self._cli_generator, self.SubParser(),
            parent_group=self, allow_empty=allow_empty)
        self.groups[element.name] = element
      elif name in self._commands_to_load:
        (module_dir, module_path, name, track) = self._commands_to_load[name]
        element = Command(
            module_dir, module_path, self._path + [name], track,
            self._construction_id, self._cli_generator, self.SubParser(),
            parent_group=self)
        self.commands[element.name] = element
    except base.ReleaseTrackNotImplementedException as e:
      self._unloadable_elements.add(name)
      log.debug(e)
    return element

  def GetSubCommandHelps(self):
    return dict(
        (item.cli_name,
         usage_text.HelpInfo(help_text=item.short_help,
                             is_hidden=item.IsHidden(),
                             release_track=item.ReleaseTrack))
        for item in self.commands.values())

  def GetSubGroupHelps(self):
    return dict(
        (item.cli_name,
         usage_text.HelpInfo(help_text=item.short_help,
                             is_hidden=item.IsHidden(),
                             release_track=item.ReleaseTrack()))
        for item in self.groups.values())

  def RunGroupFilter(self, context, args):
    """Constructs and runs the Filter() method of all parent groups.

    This recurses up to the root group and then constructs each group and runs
    its Filter() method down the tree.

    Args:
      context: {}, The context dictionary that Filter() can modify.
      args: The argparse namespace.
    """
    if self._parent_group:
      self._parent_group.RunGroupFilter(context, args)
    self._common_type().Filter(context, args)


class Command(CommandCommon):
  """A class that encapsulates the configuration for a single command."""

  def __init__(self, module_dir, module_path, path, release_track,
               construction_id, cli_generator, parser_group, parent_group=None):
    """Create a new command.

    Args:
      module_dir: str, The root of the command tree.
      module_path: a list of command group names that brought us down to this
        command from the top module directory
      path: similar to module_path, but is the path to this command with respect
        to the CLI itself.  This path should be used for things like error
        reporting when a specific element in the tree needs to be referenced.
      release_track: base.ReleaseTrack, The release track (ga, beta, alpha) that
        this command group is in.  This will apply to all commands under it.
      construction_id: str, A unique identifier for the CLILoader that is
        being constructed.
      cli_generator: cli.CLILoader, The builder used to generate this CLI.
      parser_group: argparse.Parser, The parser to be used for this command.
      parent_group: CommandGroup, The parent of this command.
    """
    # pylint:disable=protected-access, The base module is effectively an
    # extension of calliope, and we want to leave _Common private so people
    # don't extend it directly.
    common_type = base._Common.FromModule(
        self._GetModuleFromPath(module_dir, module_path, path, construction_id),
        release_track,
        is_command=True)
    super(Command, self).__init__(
        common_type,
        path=path,
        release_track=release_track,
        cli_generator=cli_generator,
        allow_positional_args=True,
        parser_group=parser_group,
        parent_group=parent_group)

    self._parser.set_defaults(calliope_command=self, command_path=self._path)

  def Run(self, cli, args):
    """Run this command with the given arguments.

    Args:
      cli: The cli.CLI object for this command line tool.
      args: The arguments for this command as a namespace.

    Returns:
      The object returned by the module's Run() function.

    Raises:
      exceptions.Error: if thrown by the Run() function.
      exceptions.ExitCodeNoError: if the command is returning with a non-zero
        exit code.
    """
    metrics.Loaded()

    tool_context = {}
    if self._parent_group:
      self._parent_group.RunGroupFilter(tool_context, args)

    command_instance = self._common_type(cli=cli, context=tool_context)

    log.debug('Running %s with %s.', self.dotted_name, args)
    resources = command_instance.Run(args)
    resources = display.Displayer(command_instance, args, resources,
                                  display_info=self.ai.display_info).Display()
    metrics.Ran()

    if command_instance.exit_code != 0:
      raise exceptions.ExitCodeNoError(exit_code=command_instance.exit_code)

    return resources
