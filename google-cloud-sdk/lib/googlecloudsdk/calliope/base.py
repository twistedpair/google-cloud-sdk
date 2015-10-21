# Copyright 2013 Google Inc. All Rights Reserved.
"""Base classes for calliope commands and groups.

"""

import abc

from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import log
from googlecloudsdk.core import resource_printer


class LayoutException(Exception):
  """An exception for when a command or group .py file has the wrong types."""


class ReleaseTrackNotImplementedException(Exception):
  """An exception for when a command or group does not support a release track.
  """


class ReleaseTrack(object):
  """An enum representing the release track of a command or command group.

  The release track controls where a command appears.  The default of GA means
  it will show up under gcloud.  If you enable a command or group for the alpha
  or beta tracks, those commands will be duplicated under those groups as well.
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
      '{0}(BETA){0} '.format(usage_text.MARKDOWN_BOLD),
      'This command is currently in BETA and may change without notice.')
  ALPHA = _TRACK(
      'ALPHA', 'alpha',
      '{0}(ALPHA){0} '.format(usage_text.MARKDOWN_BOLD),
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
  _release_track = None
  # TODO(markpell): Remove this once commands are only allowed to show up under
  # the correct track (b/19406151)
  _legacy_release_track = None
  _valid_release_tracks = None

  def __init__(self, http_func):
    self._http_func = http_func
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
      parser: An argparse.ArgumentParser-like object. It is mocked out in order
          to capture some information, but behaves like an ArgumentParser.
    """
    pass

  @classmethod
  def IsHidden(cls):
    return cls._is_hidden

  @classmethod
  def ReleaseTrack(cls, for_help=False):
    # TODO(markpell): Remove for_help once commands are only allowed to show up
    # under the correct track (b/19406151).
    if for_help and cls._legacy_release_track:
      return cls._legacy_release_track
    return cls._release_track

  @classmethod
  def ValidReleaseTracks(cls):
    return cls._valid_release_tracks

  @classmethod
  def GetExecutionFunction(cls, *args):
    """Get a fully bound function that will call another gcloud command.

    This class method can be called at any time to generate a function that will
    execute another gcloud command.  The function itself can only be executed
    after the gcloud CLI has been build i.e. after all Args methods have
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

  def Http(self, auth=True, creds=None, **kwargs):
    """Get the http object to be used during service requests.

    Args:
      auth: bool, True if the http object returned should be authorized.
      creds: oauth2client.client.Credentials, If auth is True and creds is not
          None, use those credentials to authorize the httplib2.Http object.
      **kwargs: keyword arguments to forward to httplib2.Http()

    Returns:
      httplib2.Http, http object to be used during service requests.
    """
    return self._http_func(auth=auth, creds=creds, **kwargs)


class Command(_Common):
  """Command is a base class for commands to implement.

  Attributes:
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
    context: {str:object}, A set of key-value pairs that can be used for
        common initialization among commands.
    group: base.Group, The instance of the group class above this command.  You
        can use this to access common methods within a group.
    format: func(obj), A function that prints objects to stdout using the
        user-chosen formatting option.
    http_func: function that returns an http object that can be used during
        service requests.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, cli, context, group, http_func, format_string):
    super(Command, self).__init__(http_func)
    self.cli = cli
    self.context = context
    self.group = group
    self.__format_string = format_string

  def ExecuteCommand(self, args):
    self.cli.Execute(args, call_arg_complete=False)

  @abc.abstractmethod
  def Run(self, args):
    """Run the command.

    Args:
      args: argparse.Namespace, An object that contains the values for the
          arguments specified in the .Args() method.
    Returns:
      A python object that is given back to the python caller, or sent to the
      .Display() method in CLI mode.
    """
    raise NotImplementedError('CommandBase.Run is not overridden')

  def Display(self, args, result):
    """Print the result for a human to read from the terminal.

    Args:
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
      result: object, The object return by the corresponding .Run() invocation.
    """
    pass

  # TODO(markpell): When the formatting revamp goes in, this should be renamed.
  # pylint: disable=invalid-name
  def format(self, obj):
    """Prints out the given object using the format decided by the format flag.

    Args:
      obj: Object, The object to print.
    """
    if obj:
      resource_printer.Print(obj, self.__format_string, out=log.out)


class Group(_Common):
  """Group is a base class for groups to implement.

  Attributes:
    http_func: function that returns an http object that can be used during
        service requests.
  """

  def __init__(self, http_func):
    super(Group, self).__init__(http_func)

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    pass


class Argument(object):
  """A class that allows you to save an argument configuration for reuse."""

  def __init__(self, *args, **kwargs):
    """Creates the argument.

    Args:
      *args: The positional args to parser.add_argument.
      **kwargs: The keyword args to parser.add_argument.
    """
    try:
      self.__detailed_help = kwargs.pop('detailed_help')
    except KeyError:
      self.__detailed_help = None
    self.__args = args
    self.__kwargs = kwargs

  def AddToParser(self, parser):
    """Adds this argument to the given parser.

    Args:
      parser: The argparse parser.

    Returns:
      The result of parser.add_argument().
    """
    arg = parser.add_argument(*self.__args, **self.__kwargs)
    if self.__detailed_help:
      arg.detailed_help = self.__detailed_help
    return arg


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


# TODO(markpell): Remove this once commands are only allowed to show up under
# the correct track (b/19406151).
def Alpha(cmd_class):
  """Decorator for annotating a command or group as ALPHA.

  Args:
    cmd_class: base._Common, A calliope command or group.

  Returns:
    A modified version of the provided class.
  """
  # pylint: disable=protected-access
  cmd_class._legacy_release_track = ReleaseTrack.ALPHA
  return cmd_class


# TODO(markpell): Remove this once commands are only allowed to show up under
# the correct track (b/19406151)
def Beta(cmd_class):
  """Decorator for annotating a command or group as BETA.

  Args:
    cmd_class: base._Common, A calliope command or group.

  Returns:
    A modified version of the provided class.
  """
  # pylint: disable=protected-access
  cmd_class._legacy_release_track = ReleaseTrack.BETA
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
