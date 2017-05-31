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
"""Base classes for calliope commands and groups.

"""

import abc
from functools import wraps
import itertools
import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import display
from googlecloudsdk.core import log
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.resource import resource_registry


# Common markdown.
MARKDOWN_BOLD = '*'
MARKDOWN_ITALIC = '_'
MARKDOWN_CODE = '`'


class LayoutException(Exception):
  """An exception for when a command or group .py file has the wrong types."""


class DeprecationException(Exception):
  """An exception for when a command or group has been deprecated."""


class ReleaseTrackNotImplementedException(Exception):
  """An exception for when a command or group does not support a release track.
  """


class ReleaseTrack(object):
  """An enum representing the release track of a command or command group.

  The release track controls where a command appears.  The default of GA means
  it will show up under gcloud.  If you enable a command or group for the alpha,
  beta, or preview tracks, those commands will be duplicated under those groups
  as well.
  """

  class _TRACK(object):
    """An enum representing the release track of a command or command group."""

    # pylint: disable=redefined-builtin
    def __init__(self, id, prefix, help_tag, help_note):
      self.id = id
      self.prefix = prefix
      self.help_tag = help_tag
      self.help_note = help_note

    def __str__(self):
      return self.id

    def __eq__(self, other):
      return self.id == other.id

  GA = _TRACK('GA', None, None, None)
  BETA = _TRACK(
      'BETA', 'beta',
      '{0}(BETA){0} '.format(MARKDOWN_BOLD),
      'This command is currently in BETA and may change without notice.')
  ALPHA = _TRACK(
      'ALPHA', 'alpha',
      '{0}(ALPHA){0} '.format(MARKDOWN_BOLD),
      'This command is currently in ALPHA and may change without notice.')
  _ALL = [GA, BETA, ALPHA]

  @staticmethod
  def AllValues():
    """Gets all possible enum values.

    Returns:
      list, All the enum values.
    """
    return list(ReleaseTrack._ALL)

  @staticmethod
  def FromPrefix(prefix):
    """Gets a ReleaseTrack from the given release track prefix.

    Args:
      prefix: str, The prefix string that might be a release track name.

    Returns:
      ReleaseTrack, The corresponding object or None if the prefix was not a
      valid release track.
    """
    for track in ReleaseTrack._ALL:
      if track.prefix == prefix:
        return track
    return None

  @staticmethod
  def FromId(id):  # pylint: disable=redefined-builtin
    """Gets a ReleaseTrack from the given release track prefix.

    Args:
      id: str, The id string that must be a release track name.

    Raises:
      ValueError: For unknown release track ids.

    Returns:
      ReleaseTrack, The corresponding object.
    """
    for track in ReleaseTrack._ALL:
      if track.id == id:
        return track
    raise ValueError('Unknown release track id [{}].'.format(id))


class Action(object):
  """A class that allows you to save an Action configuration for reuse."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, *args, **kwargs):
    """Creates the Action.

    Args:
      *args: The positional args to parser.add_argument.
      **kwargs: The keyword args to parser.add_argument.
    """
    self.args = args
    self.kwargs = kwargs

  @property
  def name(self):
    return self.args[0]

  @abc.abstractmethod
  def AddToParser(self, parser):
    """Adds this Action to the given parser.

    Args:
      parser: The argparse parser.

    Returns:
      The result of adding the Action to the parser.
    """
    pass

  def RemoveFromParser(self, parser):
    """Removes this Action from the given parser.

    Args:
      parser: The argparse parser.
    """
    pass

  def SetDefault(self, parser, default):
    """Sets the default value for this Action in the given parser.

    Args:
      parser: The argparse parser.
      default: The default value.
    """
    pass


class ArgumentGroup(Action):
  """A class that allows you to save an argument group configuration for reuse.
  """

  def __init__(self, *args, **kwargs):
    super(ArgumentGroup, self).__init__(*args, **kwargs)
    self.arguments = []

  def AddArgument(self, arg):
    self.arguments.append(arg)

  def AddToParser(self, parser):
    """Adds this argument group to the given parser.

    Args:
      parser: The argparse parser.

    Returns:
      The result of parser.add_argument().
    """
    group = parser.add_argument_group(*self.args, **self.kwargs)
    for arg in self.arguments:
      arg.AddToParser(group)
    return group


class Argument(Action):
  """A class that allows you to save an argument configuration for reuse."""

  def __GetFlag(self, parser):
    """Returns the flag object in parser."""
    for flag in itertools.chain(parser.flag_args, parser.ancestor_flag_args):
      if self.name in flag.option_strings:
        return flag
    return None

  def AddToParser(self, parser):
    """Adds this argument to the given parser.

    Args:
      parser: The argparse parser.

    Returns:
      The result of parser.add_argument().
    """
    return parser.add_argument(*self.args, **self.kwargs)

  def RemoveFromParser(self, parser):
    """Removes this flag from the given parser.

    Args:
      parser: The argparse parser.
    """
    flag = self.__GetFlag(parser)
    if flag:
      # Remove the flag and its inverse, if it exists, from its container.
      name = flag.option_strings[0]
      conflicts = [(name, flag)]
      no_name = '--no-' + name[2:]
      for no_flag in itertools.chain(parser.flag_args,
                                     parser.ancestor_flag_args):
        if no_name in no_flag.option_strings:
          conflicts.append((no_name, no_flag))
      # pylint: disable=protected-access, argparse, why can't we be friends
      flag.container._handle_conflict_resolve(flag, conflicts)
      # Remove the conflict flags from the calliope argument interceptor.
      for _, flag in conflicts:
        parser.defaults.pop(flag.dest, None)
        if flag.dest in parser.dests:
          parser.dests.remove(flag.dest)
        if flag in parser.flag_args:
          parser.flag_args.remove(flag)

  def SetDefault(self, parser, default):
    """Sets the default value for this flag in the given parser.

    Args:
      parser: The argparse parser.
      default: The default flag value.
    """
    flag = self.__GetFlag(parser)
    if flag:
      kwargs = {flag.dest: default}
      parser.set_defaults(**kwargs)


# Common flag definitions for consistency.

# Common flag categories.

COMMONLY_USED_FLAGS = 'COMMONLY USED'

FLATTEN_FLAG = Argument(
    '--flatten',
    metavar='KEY',
    default=None,
    type=arg_parsers.ArgList(),
    category=COMMONLY_USED_FLAGS,
    help="""\
        Flatten _name_[] output resource slices in _KEY_ into separate records
        for each item in each slice. Multiple keys and slices may be specified.
        This also flattens keys for *--format* and *--filter*. For example,
        *--flatten=abc.def[]* flattens *abc.def[].ghi* references to
        *abc.def.ghi*. A resource record containing *abc.def[]* with N elements
        will expand to N records in the flattened output. This flag interacts
        with other flags that are applied in this order: *--flatten*,
        *--sort-by*, *--filter*, *--limit*.""")

FORMAT_FLAG = Argument(
    '--format',
    default=None,
    category=COMMONLY_USED_FLAGS,
    help="""\
        Sets the format for printing command output resources. The default is a
        command-specific human-friendly output format. The supported formats
        are: `{0}`. For more details run $ gcloud topic formats.""".format(
            '`, `'.join(resource_printer.SupportedFormats())))

LIST_COMMAND_FLAGS = 'LIST COMMAND'

ASYNC_FLAG = Argument(
    '--async',
    action='store_true',
    help="""\
    Display information about the operation in progress, without waiting for
    the operation to complete.""")

FILTER_FLAG = Argument(
    '--filter',
    metavar='EXPRESSION',
    category=LIST_COMMAND_FLAGS,
    help="""\
    Apply a Boolean filter _EXPRESSION_ to each resource item to be listed.
    If the expression evaluates True then that item is listed. For more
    details and examples of filter expressions run $ gcloud topic filters. This
    flag interacts with other flags that are applied in this order: *--flatten*,
    *--sort-by*, *--filter*, *--limit*.""")

LIMIT_FLAG = Argument(
    '--limit',
    type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
    category=LIST_COMMAND_FLAGS,
    help="""\
    The maximum number of resources to list. The default is *unlimited*.
    This flag interacts with other flags that are applied in this order:
    *--flatten*, *--sort-by*, *--filter*, *--limit*.
    """)

PAGE_SIZE_FLAG = Argument(
    '--page-size',
    type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
    category=LIST_COMMAND_FLAGS,
    help="""\
    Some services group resource list output into pages. This flag specifies
    the maximum number of resources per page. The default is determined by the
    service if it supports paging, otherwise it is *unlimited* (no paging).
    Paging may be applied before or after *--filter* and *--limit* depending
    on the service.
    """)

SORT_BY_FLAG = Argument(
    '--sort-by',
    metavar='FIELD',
    type=arg_parsers.ArgList(),
    category=LIST_COMMAND_FLAGS,
    help="""\
    A comma-separated list of resource field key names to sort by. The
    default order is ascending. Prefix a field with ``~'' for descending
    order on that field. This flag interacts with other flags that are applied
    in this order: *--flatten*, *--sort-by*, *--filter*, *--limit*.
    """)

URI_FLAG = Argument(
    '--uri',
    action='store_true',
    category=LIST_COMMAND_FLAGS,
    help='Print a list of resource URIs instead of the default output.')


class _Common(object):
  """Base class for Command and Group.

  Attributes:
    config: {str:object}, A set of key-value pairs that will persist (as long
        as they are JSON-serializable) between command invocations. Can be used
        for caching.
    http_func: function that returns an http object that can be used during
        service requests.
  """

  __metaclass__ = abc.ABCMeta
  _cli_generator = None
  _is_hidden = False
  _is_unicode_supported = False
  _release_track = None
  _valid_release_tracks = None
  _notices = None

  def __init__(self):
    self.exit_code = 0

  @staticmethod
  def FromModule(module, release_track, is_command):
    """Get the type implementing CommandBase from the module.

    Args:
      module: module, The module resulting from importing the file containing a
        command.
      release_track: ReleaseTrack, The release track that we should load from
        this module.
      is_command: bool, True if we are loading a command, False to load a group.

    Returns:
      type, The custom class that implements CommandBase.

    Raises:
      LayoutException: If there is not exactly one type inheriting
          CommonBase.
      ReleaseTrackNotImplementedException: If there is no command or group
        implementation for the request release track.
    """
    return _Common._FromModule(
        module.__file__, module.__dict__.values(), release_track, is_command)

  @staticmethod
  def _FromModule(mod_file, module_attributes, release_track, is_command):
    """Implementation of FromModule() made easier to test."""
    commands = []
    groups = []

    # Collect all the registered groups and commands.
    for command_or_group in module_attributes:
      if issubclass(type(command_or_group), type):
        if issubclass(command_or_group, Command):
          commands.append(command_or_group)
        elif issubclass(command_or_group, Group):
          groups.append(command_or_group)

    if is_command:
      if groups:
        # Ensure that there are no groups if we are expecting a command.
        raise LayoutException(
            'You cannot define groups [{0}] in a command file: [{1}]'
            .format(', '.join([g.__name__ for g in groups]), mod_file))
      if not commands:
        # Make sure we found a command.
        raise LayoutException('No commands defined in file: [{0}]'.format(
            mod_file))
      commands_or_groups = commands
    else:
      # Ensure that there are no commands if we are expecting a group.
      if commands:
        raise LayoutException(
            'You cannot define commands [{0}] in a command group file: [{1}]'
            .format(', '.join([c.__name__ for c in commands]), mod_file))
      if not groups:
        # Make sure we found a group.
        raise LayoutException('No command groups defined in file: [{0}]'.format(
            mod_file))
      commands_or_groups = groups

    # We found a single thing, if it's valid for this track, return it.
    if len(commands_or_groups) == 1:
      command_or_group = commands_or_groups[0]
      valid_tracks = command_or_group.ValidReleaseTracks()
      # If there is a single thing defined, and it does not declare any valid
      # tracks, just assume it is enabled for all tracks that it's parent is.
      if not valid_tracks or release_track in valid_tracks:
        return command_or_group
      raise ReleaseTrackNotImplementedException(
          'No implementation for release track [{0}] in file: [{1}]'
          .format(release_track.id, mod_file))

    # There was more than one thing found, make sure there are no conflicts.
    implemented_release_tracks = set()
    for command_or_group in commands_or_groups:
      valid_tracks = command_or_group.ValidReleaseTracks()
      # When there are multiple definitions, they need to explicitly register
      # their track to keep things sane.
      if not valid_tracks:
        raise LayoutException(
            'Multiple {0}s defined in file: [{1}].  Each must explicitly '
            'declare valid release tracks.'
            .format('command' if is_command else 'group', mod_file))
      # Make sure no two classes define the same track.
      duplicates = implemented_release_tracks & valid_tracks
      if duplicates:
        raise LayoutException(
            'Multiple definitions for release tracks [{0}] in file: [{1}]'
            .format(', '.join([str(d) for d in duplicates]), mod_file))
      implemented_release_tracks |= valid_tracks

    valid_commands_or_groups = [i for i in commands_or_groups
                                if release_track in i.ValidReleaseTracks()]
    # We know there is at most 1 because of the above check.
    if len(valid_commands_or_groups) != 1:
      raise ReleaseTrackNotImplementedException(
          'No implementation for release track [{0}] in file: [{1}]'
          .format(release_track.id, mod_file))

    return valid_commands_or_groups[0]

  @staticmethod
  def Args(parser):
    """Set up arguments for this command.

    Args:
      parser: An argparse.ArgumentParser.
    """
    pass

  @staticmethod
  def _Flags(parser):
    """Adds subclass flags.

    Args:
      parser: An argparse.ArgumentParser object.
    """
    pass

  @classmethod
  def IsHidden(cls):
    return cls._is_hidden

  @classmethod
  def IsUnicodeSupported(cls):
    return cls._is_unicode_supported

  @classmethod
  def ReleaseTrack(cls):
    return cls._release_track

  @classmethod
  def ValidReleaseTracks(cls):
    return cls._valid_release_tracks

  @classmethod
  def GetTrackedAttribute(cls, obj, attribute):
    """Gets the attribute value from obj for tracks.

    The values are checked in ReleaseTrack._ALL order.

    Args:
      obj: The object to extract attribute from.
      attribute: The attribute name in object.

    Returns:
      The attribute value from obj for tracks.
    """
    for track in ReleaseTrack._ALL:  # pylint: disable=protected-access
      if track not in cls._valid_release_tracks:
        continue
      names = []
      names.append(attribute + '_' + track.id)
      if track.prefix:
        names.append(attribute + '_' + track.prefix)
      for name in names:
        if hasattr(obj, name):
          return getattr(obj, name)
    return getattr(obj, attribute, None)

  @classmethod
  def Notices(cls):
    return cls._notices

  @classmethod
  def AddNotice(cls, tag, msg):
    if not cls._notices:
      cls._notices = {}
    cls._notices[tag] = msg

  @classmethod
  def GetExecutionFunction(cls, *args):
    """Get a fully bound function that will call another gcloud command.

    This class method can be called at any time to generate a function that will
    execute another gcloud command.  The function itself can only be executed
    after the gcloud CLI has been built i.e. after all Args methods have
    been called.

    Args:
      *args: str, The args for the command to execute.  Each token should be a
        separate string and the tokens should start from after the 'gcloud'
        part of the invocation.

    Returns:
      A bound function to call the gcloud command.
    """
    def ExecFunc():
      return cls._cli_generator.Generate().Execute(list(args),
                                                   call_arg_complete=False)
    return ExecFunc

  @classmethod
  def GetCLIGenerator(cls):
    """Get a generator function that can be used to execute a gcloud command.

    Returns:
      A bound generator function to execute a gcloud command.
    """
    if cls._cli_generator:
      return cls._cli_generator.Generate
    return None


class Group(_Common):
  """Group is a base class for groups to implement.

  Attributes:
    http_func: function that returns an http object that can be used during
        service requests.
  """

  _command_suggestions = {}

  def __init__(self):
    super(Group, self).__init__()

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    pass

  @classmethod
  def CommandSuggestions(cls):
    return cls._command_suggestions


class Command(_Common):
  """Command is a base class for commands to implement.

  Attributes:
    _cli_power_users_only: calliope.cli.CLI, The CLI object representing this
      command line tool. This should *only* be accessed via commands that
      absolutely *need* introspection of the entire CLI.
    context: {str:object}, A set of key-value pairs that can be used for
        common initialization among commands.
    http_func: function that returns an http object that can be used during
        service requests.
    _uri_cache_enabled: bool, The URI cache enabled state.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, cli, context):
    super(Command, self).__init__()
    self._cli_do_not_use_directly = cli
    self.context = context
    self._uri_cache_enabled = False

  @property
  def _cli_power_users_only(self):
    return self._cli_do_not_use_directly

  def ExecuteCommandDoNotUse(self, args):
    """Execute a command using the given CLI.

    Do not introduce new invocations of this method unless your command
    *requires* it; any such new invocations must be approved by a team lead.

    Args:
      args: list of str, the args to Execute() via the CLI.

    Returns:
      pass-through of the return value from Execute()
    """
    return self._cli_power_users_only.Execute(args, call_arg_complete=False)

  @staticmethod
  def _Flags(parser):
    """Sets the default output format.

    Args:
      parser: The argparse parser.
    """
    parser.display_info.AddFormat('default')

  @abc.abstractmethod
  def Run(self, args):
    """Runs the command.

    Args:
      args: argparse.Namespace, An object that contains the values for the
          arguments specified in the .Args() method.

    Returns:
      A resource object dispatched by display.Displayer().
    """
    pass

  def Collection(self):
    """Returns the default collection path string.

    Should handle all command-specific args. --async is handled by
    ResourceInfo().

    Returns:
      The default collection path string.
    """
    return None

  def ResourceInfo(self, args):
    """Returns the command resource ResourceInfo object.

    Handles the --async flag.

    Args:
      args: argparse.Namespace, An object that contains the values for the
          arguments specified in the ._Flags() and .Args() methods.

    Raises:
      ResourceRegistryAttributeError: If --async is set and the
        resource_registry info does not have an async_collection attribute.
      UnregisteredCollectionError: If the async_collection name is not in the
        resource registry.

    Returns:
      A resource object dispatched by display.Displayer().
    """
    collection = self.Collection()  # pylint: disable=assignment-from-none
    if not collection:
      return None
    info = resource_registry.Get(collection)
    if not getattr(args, 'async', False):
      return info
    if not info.async_collection:
      raise resource_exceptions.ResourceRegistryAttributeError(
          'Collection [{collection}] does not have an async_collection '
          'attribute.'.format(collection=collection))
    info = resource_registry.Get(info.async_collection)
    # One more indirection allowed for commands that have a different operations
    # format for --async and operations list.
    if info.async_collection:
      info = resource_registry.Get(info.async_collection)
    return info

  def DeprecatedFormat(self, args):
    """Returns the default format string.

    Calliope supports a powerful formatting mini-language. It allows running
    things like

        $ my-tool run-foo --format=json
        $ my-tool run-foo --format='value(bar.baz.map().qux().list())'
        $ my-tool run-foo --format='table[box](a, b, c:label=SOME_DESCRIPTION)'

    For the best current documentation on this formatting language, see
    `gcloud topic formats` and `gcloud topic projections`.

    When a command is run with no `--format` flag, this method is run and its
    result is used as the format string.

    This method is deprecated in favor of calling:

        parser.display_info.AddFormat(<format string>)

    in the Args method for the command.

    Args:
      args: the argparse namespace object for this command execution. Not used
        in the default implementation, but available for subclasses to use.

    Returns:
      str, the default format string for this command.
    """
    del args  # Unused in DeprecatedFormat
    return 'default'

  def ListFormat(self, args):
    info = self.ResourceInfo(args)
    if info and info.list_format:
      return info.list_format
    return 'default'

  def Epilog(self, resources_were_displayed):
    """Called after resources are displayed if the default format was used.

    Args:
      resources_were_displayed: True if resources were displayed.
    """
    _ = resources_were_displayed

  def Defaults(self):
    """Returns the command projection defaults."""
    return None

  def GetReferencedKeyNames(self, args):
    """Returns the key names referenced by the filter and format expressions."""
    return display.Displayer(self, args, None).GetReferencedKeyNames()

  def GetUriFunc(self):
    """Returns a function that transforms a command resource item to a URI.

    Returns:
      func(resource) that transforms resource into a URI.
    """
    return None

  @staticmethod
  def GetUriCacheUpdateOp():
    """Returns the URI cache update OP."""
    return None


class TopicCommand(Command):
  """A command that displays its own help on execution."""

  __metaclass__ = abc.ABCMeta

  def Run(self, args):
    self.ExecuteCommandDoNotUse(args.command_path[1:] +
                                ['--document=style=topic'])
    return None


class SilentCommand(Command):
  """A command that produces no output."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def _Flags(parser):
    parser.display_info.AddFormat('none')

  def DeprecatedFormat(self, unused_args):
    return 'none'


class DescribeCommand(Command):
  """A command that prints one resource in the 'default' format."""

  __metaclass__ = abc.ABCMeta


class CacheCommand(Command):
  """A command that affects the resource URI cache."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, *args, **kwargs):
    super(CacheCommand, self).__init__(*args, **kwargs)
    self._uri_cache_enabled = True

  @staticmethod
  @abc.abstractmethod
  def GetUriCacheUpdateOp():
    """Returns the URI cache update OP."""
    pass


class ListCommand(CacheCommand):
  """A command that pretty-prints all resources."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def _Flags(parser):
    """Adds the default flags for all ListCommand commands.

    Args:
      parser: The argparse parser.
    """

    FILTER_FLAG.AddToParser(parser)
    LIMIT_FLAG.AddToParser(parser)
    PAGE_SIZE_FLAG.AddToParser(parser)
    SORT_BY_FLAG.AddToParser(parser)
    URI_FLAG.AddToParser(parser)

  def Epilog(self, resources_were_displayed):
    """Called after resources are displayed if the default format was used.

    Args:
      resources_were_displayed: True if resources were displayed.
    """
    if not resources_were_displayed:
      log.status.Print('Listed 0 items.')

  def DeprecatedFormat(self, args):
    return self.ListFormat(args)

  @staticmethod
  def GetUriCacheUpdateOp():
    return remote_completion.ReplaceCacheOp


class CreateCommand(CacheCommand, SilentCommand):
  """A command that creates resources."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def GetUriCacheUpdateOp():
    return remote_completion.AddToCacheOp


class DeleteCommand(CacheCommand, SilentCommand):
  """A command that deletes resources."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def GetUriCacheUpdateOp():
    return remote_completion.DeleteFromCacheOp


class RestoreCommand(CacheCommand, SilentCommand):
  """A command that restores resources."""

  __metaclass__ = abc.ABCMeta

  @staticmethod
  def GetUriCacheUpdateOp():
    return remote_completion.AddToCacheOp


class UpdateCommand(SilentCommand):
  """A command that updates resources."""

  pass


def Hidden(cmd_class):
  """Decorator for hiding calliope commands and groups.

  Decorate a subclass of base.Command or base.Group with this function, and the
  decorated command or group will not show up in help text.

  Args:
    cmd_class: base._Common, A calliope command or group.

  Returns:
    A modified version of the provided class.
  """
  # pylint: disable=protected-access
  cmd_class._is_hidden = True
  return cmd_class


def CommandSuggestion(command, suggestion):
  """Decorator for adding a suggestion when a command is mistyped.

  This applies to base.Group classes. When a user tries to run the given
  `command` that does not exist, `suggestion` will but suggested as a
  "did you mean".

  Args:
    command: str, The name of the command (just the command itself not including
      the group).
    suggestion: str, The full command name to suggest (excluding the gcloud
      prefix).

  Returns:
    The inner decorator.
  """
  def Inner(cmd_class):
    # pylint: disable=protected-access
    cmd_class._command_suggestions[command] = suggestion
    return cmd_class
  return Inner


def UnicodeIsSupported(cmd_class):
  """Decorator for calliope commands and groups that support unicode.

  Decorate a subclass of base.Command or base.Group with this function, and the
  decorated command or group will not raise the argparse unicode command line
  argument exception.

  Args:
    cmd_class: base._Common, A calliope command or group.

  Returns:
    A modified version of the provided class.
  """
  # pylint: disable=protected-access
  cmd_class._is_unicode_supported = True
  return cmd_class


def ReleaseTracks(*tracks):
  """Mark this class as the command implementation for the given release tracks.

  Args:
    *tracks: [ReleaseTrack], A list of release tracks that this is valid for.

  Returns:
    The decorated function.
  """
  def ApplyReleaseTracks(cmd_class):
    """Wrapper function for the decorator."""
    # pylint: disable=protected-access
    cmd_class._valid_release_tracks = set(tracks)
    return cmd_class
  return ApplyReleaseTracks


def Deprecate(is_removed=True,
              warning='This command is deprecated.',
              error='This command has been removed.'):
  """Decorator that marks a Calliope command as deprecated.

  Decorate a subclass of base.Command with this function and the
  decorated command will be modified as follows:

  - If is_removed is false, a warning will be logged when *command* is run,
  otherwise an *exception* will be thrown containing error message

  -Command help output will be modified to include warning/error message
  depending on value of is_removed

  - Command help text will automatically hidden from the reference documentation
  (e.g. @base.Hidden) if is_removed is True


  Args:
      is_removed: boolean, True if the command should raise an error
      when executed. If false, a warning is printed
      warning: string, warning message
      error: string, error message

  Returns:
    A modified version of the provided class.
  """

  def DeprecateCommand(cmd_class):
    """Wrapper Function that creates actual decorated class.

    Args:
      cmd_class: base.Command or base.Group subclass to be decorated

    Returns:
      The decorated class.
    """
    if is_removed:
      msg = error
      deprecation_tag = '{0}(REMOVED){0} '.format(MARKDOWN_BOLD)
    else:
      msg = warning
      deprecation_tag = '{0}(DEPRECATED){0} '.format(MARKDOWN_BOLD)

    cmd_class.AddNotice(deprecation_tag, msg)

    def RunDecorator(run_func):
      @wraps(run_func)
      def WrappedRun(*args, **kw):
        if is_removed:
          raise DeprecationException(error)
        log.warn(warning)
        return run_func(*args, **kw)
      return WrappedRun

    if issubclass(cmd_class, Group):
      cmd_class.Filter = RunDecorator(cmd_class.Filter)
    else:
      cmd_class.Run = RunDecorator(cmd_class.Run)

    if is_removed:
      return Hidden(cmd_class)

    return cmd_class

  return DeprecateCommand
