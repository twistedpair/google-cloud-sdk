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

"""The calliope CLI/API is a framework for building library interfaces."""

import argparse
import os
import re
import sys
import types
import uuid

import argcomplete
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import backend
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.util import pkg_resources


_COMMAND_SUFFIX = '.py'


class RunHook(object):
  """Encapsulates a function to be run before or after command execution.

  The function should take **kwargs so that more things can be passed to the
  functions in the future.
  """

  def __init__(self, func, include_commands=None, exclude_commands=None):
    """Constructs the hook.

    Args:
      func: function, The function to run.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    self.__func = func
    self.__include_commands = include_commands if include_commands else '.*'
    self.__exclude_commands = exclude_commands

  def Run(self, command_path):
    """Runs this hook if the filters match the given command.

    Args:
      command_path: str, The calliope command path for the command that was run.

    Returns:
      bool, True if the hook was run, False if it did not match.
    """
    if not re.match(self.__include_commands, command_path):
      return False
    if self.__exclude_commands and re.match(self.__exclude_commands,
                                            command_path):
      return False
    self.__func(command_path=command_path)
    return True


class CLILoader(object):
  """A class to encapsulate loading the CLI and bootstrapping the REPL."""

  # Splits a path like foo.bar.baz into 2 groups: foo.bar, and baz.  Group 1 is
  # optional.
  PATH_RE = re.compile(r'(?:([\w\.]+)\.)?([^\.]+)')

  def __init__(self, name, command_root_directory,
               allow_non_existing_modules=False,
               logs_dir=config.Paths().logs_dir, version_func=None,
               known_error_handler=None):
    """Initialize Calliope.

    Args:
      name: str, The name of the top level command, used for nice error
        reporting.
      command_root_directory: str, The path to the directory containing the main
        CLI module.
      allow_non_existing_modules: True to allow extra module directories to not
        exist, False to raise an exception if a module does not exist.
      logs_dir: str, The path to the root directory to store logs in, or None
        for no log files.
      version_func: func, A function to call for a top-level -v and
        --version flag. If None, no flags will be available.
      known_error_handler: f(x)->None, A function to call when an known error is
        handled. It takes a single argument that is the exception.

    Raises:
      backend.LayoutException: If no command root directory is given.
    """
    self.__name = name
    self.__command_root_directory = command_root_directory
    if not self.__command_root_directory:
      raise backend.LayoutException(
          'You must specify a command root directory.')

    self.__allow_non_existing_modules = allow_non_existing_modules

    self.__logs_dir = logs_dir
    self.__version_func = version_func
    self.__known_errror_handler = known_error_handler

    self.__pre_run_hooks = []
    self.__post_run_hooks = []

    self.__modules = []
    self.__missing_components = {}
    self.__release_tracks = {}

  def AddReleaseTrack(self, release_track, path, component=None):
    """Adds a release track to this CLI tool.

    A release track (like alpha, beta...) will appear as a subgroup under the
    main entry point of the tool.  All groups and commands will be replicated
    under each registered release track.  You can implement your commands to
    behave differently based on how they are called.

    Args:
      release_track: base.ReleaseTrack, The release track you are adding.
      path: str, The full path the directory containing the root of this group.
      component: str, The name of the component this release track is in, if
        you want calliope to auto install it for users.

    Raises:
      ValueError: If an invalid track is registered.
    """
    if not release_track.prefix:
      raise ValueError('You may only register alternate release tracks that '
                       'have a different prefix.')
    self.__release_tracks[release_track] = (path, component)

  def AddModule(self, name, path, component=None):
    """Adds a module to this CLI tool.

    If you are making a CLI that has subgroups, use this to add in more
    directories of commands.

    Args:
      name: str, The name of the group to create under the main CLI.  If this is
        to be placed under another group, a dotted name can be used.
      path: str, The full path the directory containing the commands for this
        group.
      component: str, The name of the component this command module is in, if
        you want calliope to auto install it for users.
    """
    self.__modules.append((name, path, component))

  def RegisterPreRunHook(self, func,
                         include_commands=None, exclude_commands=None):
    """Register a function to be run before command execution.

    Args:
      func: function, The function to run.  See RunHook for more details.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    hook = RunHook(func, include_commands, exclude_commands)
    self.__pre_run_hooks.append(hook)

  def RegisterPostRunHook(self, func,
                          include_commands=None, exclude_commands=None):
    """Register a function to be run after command execution.

    Args:
      func: function, The function to run.  See RunHook for more details.
      include_commands: str, A regex for the command paths to run.  If not
        provided, the hook will be run for all commands.
      exclude_commands: str, A regex for the command paths to exclude.  If not
        provided, nothing will be excluded.
    """
    hook = RunHook(func, include_commands, exclude_commands)
    self.__post_run_hooks.append(hook)

  def ComponentsForMissingCommand(self, command_path):
    """Gets the components that need to be installed to run the given command.

    Args:
      command_path: [str], The path of the command being run.

    Returns:
      [str], The component names of the components that should be installed.
    """
    path_string = '.'.join(command_path)
    return [component
            for path, component in self.__missing_components.iteritems()
            if path_string.startswith(self.__name + '.' + path)]

  def ReplicateCommandPathForAllOtherTracks(self, command_path):
    """Finds other release tracks this command could be in.

    The returned values are not necessarily guaranteed to exist because the
    commands could be disabled for that particular release track.  It is up to
    the caller to determine if the commands actually exist before attempting
    use.

    Args:
      command_path: [str], The path of the command being run.

    Returns:
      {ReleaseTrack: [str]}, A mapping of release track to command path of other
      places this command could be found.
    """
    # Only a single element, it's just the root of the tree.
    if len(command_path) < 2:
      return []

    # Determine if the first token is a release track name.
    track = calliope_base.ReleaseTrack.FromPrefix(command_path[1])
    if track and track not in self.__release_tracks:
      # Make sure it's actually a track that we are using in this CLI.
      track = None

    # Remove the track from the path to get back to the GA version of the
    # command, or  keep the existing path if it is not in a track (already GA).
    root = command_path[0]
    sub_path = command_path[2:] if track else command_path[1:]

    if not sub_path:
      # There are no parts to the path other than the track.
      return []

    results = dict()
    # Calculate how this command looks under each alternate release track.
    for t in self.__release_tracks:
      results[t] = [root] + [t.prefix] + sub_path

    if track:
      # If the incoming command had a release track, remove that one from
      # alternate suggestions but add GA.
      del results[track]
      results[calliope_base.ReleaseTrack.GA] = [root] + sub_path

    return results

  def Generate(self):
    """Uses the registered information to generate the CLI tool.

    Returns:
      CLI, The generated CLI tool.
    """
    # The root group of the CLI.
    top_group = self.__LoadTopGroup(
        self.__GetCommandOrGroupInfo(
            module_dir_path=self.__command_root_directory, name=self.__name,
            release_track=calliope_base.ReleaseTrack.GA,
            allow_non_existing_modules=False, exception_if_present=None))
    self.__AddBuiltinGlobalFlags(top_group)

    # Sub groups for each alternate release track.
    loaded_release_tracks = dict([(calliope_base.ReleaseTrack.GA, top_group)])
    track_names = set(track.prefix for track in self.__release_tracks.keys())
    for track, (module_dir, component) in self.__release_tracks.iteritems():
      group_info = self.__GetCommandOrGroupInfo(
          module_dir_path=module_dir, name=track.prefix, release_track=track,
          allow_non_existing_modules=self.__allow_non_existing_modules,
          exception_if_present=None)
      if group_info:
        # Add the release track sub group into the top group.
        top_group.AddSubGroup(group_info)
        track_group = top_group.LoadSubElement(track.prefix, allow_empty=True)
        # Copy all the root elements of the top group into the release group.
        top_group.CopyAllSubElementsTo(track_group, ignore=track_names)
        loaded_release_tracks[track] = track_group
      elif component:
        self.__missing_components[track.prefix] = component

    # Load the normal set of registered sub groups.
    for module_dot_path, module_dir_path, component in self.__modules:
      is_command = module_dir_path.endswith(_COMMAND_SUFFIX)
      if is_command:
        module_dir_path = module_dir_path[:-len(_COMMAND_SUFFIX)]
      match = CLILoader.PATH_RE.match(module_dot_path)
      root, name = match.group(1, 2)
      try:
        # Mount each registered sub group under each release track that exists.
        for track, track_root_group in loaded_release_tracks.iteritems():
          parent_group = self.__FindParentGroup(track_root_group, root)
          exception_if_present = None
          if not parent_group:
            if track != calliope_base.ReleaseTrack.GA:
              # Don't error mounting sub groups if the parent group can't be
              # found unless this is for the GA group.  The GA should always be
              # there, but for alternate release channels, the parent group
              # might not be enabled for that particular release channel, so it
              # is valid to not exist.
              continue
            exception_if_present = backend.LayoutException(
                'Root [{root}] for command group [{group}] does not exist.'
                .format(root=root, group=name))

          cmd_or_grp_name = module_dot_path.split('.')[-1]
          cmd_or_grp_info = self.__GetCommandOrGroupInfo(
              module_dir_path=module_dir_path,
              name=cmd_or_grp_name,
              release_track=(parent_group.ReleaseTrack()
                             if parent_group else None),
              allow_non_existing_modules=self.__allow_non_existing_modules,
              exception_if_present=exception_if_present)

          if cmd_or_grp_info:
            if is_command:
              parent_group.AddSubCommand(cmd_or_grp_info)
            else:
              parent_group.AddSubGroup(cmd_or_grp_info)
          elif component:
            prefix = track.prefix + '.' if track.prefix else ''
            self.__missing_components[prefix + module_dot_path] = component
      except backend.CommandLoadFailure as e:
        log.exception(e)

    cli = self.__MakeCLI(top_group)

    return cli

  def __FindParentGroup(self, top_group, root):
    """Find the group that should be the parent of this command.

    Args:
      top_group: _CommandCommon, The top group in this CLI hierarchy.
      root: str, The dotted path of where this command or group should appear
        in the command tree.

    Returns:
      _CommandCommon, The group that should be parent of this new command tree
        or None if it could not be found.
    """
    if not root:
      return top_group
    root_path = root.split('.')
    group = top_group
    for part in root_path:
      group = group.LoadSubElement(part)
      if not group:
        return None
    return group

  def __GetCommandOrGroupInfo(self, module_dir_path, name, release_track,
                              allow_non_existing_modules=False,
                              exception_if_present=None):
    """Generates the information necessary to be able to load a command group.

    The group might actually be loaded now if it is the root of the SDK, or the
    information might be saved for later if it is to be lazy loaded.

    Args:
      module_dir_path: str, The path to the location of the module.
      name: str, The name that this group will appear as in the CLI.
      release_track: base.ReleaseTrack, The release track (ga, beta, alpha,
        preview) that this command group is in.  This will apply to all commands
        under it.
      allow_non_existing_modules: True to allow this module directory to not
        exist, False to raise an exception if this module does not exist.
      exception_if_present: Exception, An exception to throw if the module
        actually exists, or None.

    Raises:
      LayoutException: If the module directory does not exist and
      allow_non_existing is False.

    Returns:
      A tuple of (module_dir, module_path, name, release_track) or None if the
      module directory does not exist and allow_non_existing is True.  This
      tuple can be passed to self.__LoadTopGroup() or
      backend.CommandGroup.AddSubGroup().  The module_dir is the directory the
      group is found under.  The module_path is the relative path of the root
      of the command group from the module_dir. name is the user facing name
      this group will appear under wherever this command group is mounted.  The
      release_track is the release track (ga, beta, alpha, preview) that this
      command group is in.
    """
    module_root, module = os.path.split(module_dir_path)
    if not pkg_resources.IsImportable(module, module_root):
      if allow_non_existing_modules:
        return None
      raise backend.LayoutException(
          'The given module directory does not exist: {0}'.format(
              module_dir_path))
    elif exception_if_present:
      # pylint: disable=raising-bad-type, This will be an actual exception.
      raise exception_if_present

    return (module_root, [module], name, release_track)

  def __LoadTopGroup(self, group_info):
    """Actually loads the top group of the CLI based on the given group_info.

    Args:
      group_info: A tuple of (module_dir, module_path, name) generated by
        self.__GetGroupInfo()

    Returns:
      The backend.CommandGroup object.
    """
    (module_root, module, name, release_track) = group_info
    return backend.CommandGroup(
        module_root, module, [name], release_track, uuid.uuid4().hex, self,
        None)

  def __AddBuiltinGlobalFlags(self, top_element):
    """Adds in calliope builtin global flags.

    This needs to happen immediately after the top group is loaded and before
    any other groups are loaded.  The flags must be present so when sub groups
    are loaded, the flags propagate down.

    Args:
      top_element: backend._CommandCommon, The root of the command tree.
    """
    calliope_base.FLATTEN_FLAG.AddToParser(top_element.ai)
    calliope_base.FORMAT_FLAG.AddToParser(top_element.ai)

    if self.__version_func is not None:
      top_element.ai.add_argument(
          '-v', '--version',
          do_not_propagate=True,
          category=calliope_base.COMMONLY_USED_FLAGS,
          action=actions.FunctionExitAction(self.__version_func),
          help='Print version information and exit. This flag is only available'
          ' at the global level.')

    top_element.ai.add_argument(
        '--configuration',
        metavar='CONFIGURATION',
        category=calliope_base.COMMONLY_USED_FLAGS,
        help="""\
        The configuration to use for this command invocation. For more
        information on how to use configurations, run:
        `gcloud topic configurations`.  You can also use the [{0}] environment
        variable to set the equivalent of this flag for a terminal
        session.""".format(config.CLOUDSDK_ACTIVE_CONFIG_NAME))

    top_element.ai.add_argument(
        '--verbosity',
        choices=log.OrderedVerbosityNames(),
        default=log.DEFAULT_VERBOSITY_STRING,
        category=calliope_base.COMMONLY_USED_FLAGS,
        help='Override the default verbosity for this command.',
        action=actions.StoreProperty(properties.VALUES.core.verbosity))

    # This should be a pure Boolean flag, but the alternate true/false explicit
    # value form is preserved for backwards compatibility. This flag and
    # is the only Cloud SDK outlier.
    # TODO(b/24095744): Add true/false deprecation message.
    top_element.ai.add_argument(
        '--user-output-enabled',
        metavar=' ',  # Help text will look like the flag does not have a value.
        nargs='?',
        default=None,  # Tri-valued, None => don't override the property.
        const='true',
        choices=('true', 'false'),
        action=actions.StoreBooleanProperty(
            properties.VALUES.core.user_output_enabled),
        help='Print user intended output to the console.')

    top_element.ai.add_argument(
        '--log-http',
        default=None,  # Tri-valued, None => don't override the property.
        action=actions.StoreBooleanProperty(properties.VALUES.core.log_http),
        help='Log all HTTP server requests and responses to stderr.')

    top_element.ai.add_argument(
        '--authority-selector',
        default=None,
        action=actions.StoreProperty(properties.VALUES.auth.authority_selector),
        help=argparse.SUPPRESS)

    top_element.ai.add_argument(
        '--authorization-token-file',
        default=None,
        action=actions.StoreProperty(
            properties.VALUES.auth.authorization_token_file),
        help=argparse.SUPPRESS)

    top_element.ai.add_argument(
        '--credential-file-override',
        action=actions.StoreProperty(
            properties.VALUES.auth.credential_file_override),
        help=argparse.SUPPRESS)

    # Timeout value for HTTP requests.
    top_element.ai.add_argument(
        '--http-timeout',
        default=None,
        action=actions.StoreProperty(properties.VALUES.core.http_timeout),
        help=argparse.SUPPRESS)

  def __MakeCLI(self, top_element):
    """Generate a CLI object from the given data.

    Args:
      top_element: The top element of the command tree
        (that extends backend.CommandCommon).

    Returns:
      CLI, The generated CLI tool.
    """
    # Don't bother setting up logging if we are just doing a completion.
    if '_ARGCOMPLETE' not in os.environ or '_ARGCOMPLETE_TRACE' in os.environ:
      log.AddFileLogging(self.__logs_dir)
      verbosity_string = os.environ.get('_ARGCOMPLETE_TRACE')
      if verbosity_string:
        verbosity = log.VALID_VERBOSITY_STRINGS.get(verbosity_string)
        log.SetVerbosity(verbosity)

    # Pre-load all commands if lazy loading is disabled.
    if properties.VALUES.core.disable_command_lazy_loading.GetBool():
      top_element.LoadAllSubElements(recursive=True)

    cli = CLI(self.__name, top_element, self.__pre_run_hooks,
              self.__post_run_hooks, self.__known_errror_handler)
    return cli


class _CompletionFinder(argcomplete.CompletionFinder):
  """Calliope overrides for argcomplete.CompletionFinder.

  This makes calliope ArgumentInterceptor and actions objects visible to the
  argcomplete monkeypatcher.
  """

  def _patch_argument_parser(self):
    ai = self._parser
    self._parser = ai.parser
    active_parsers = super(_CompletionFinder, self)._patch_argument_parser()
    if ai:
      self._parser = ai
    return active_parsers

  def _get_completions(self, comp_words, cword_prefix, cword_prequote,
                       first_colon_pos):
    active_parsers = self._patch_argument_parser()

    parsed_args = parser_extensions.Namespace()
    self.completing = True

    try:
      self._parser.parse_known_args(comp_words[1:], namespace=parsed_args)
    except BaseException:  # pylint: disable=broad-except
      pass

    self.completing = False

    completions = self.collect_completions(
        active_parsers, parsed_args, cword_prefix, lambda *_: None)
    completions = self.filter_completions(completions)
    return self.quote_completions(completions, cword_prequote, first_colon_pos)


def _ArgComplete(ai, **kwargs):
  """Runs argcomplete.autocomplete on a calliope argument interceptor."""
  if '_ARGCOMPLETE' not in os.environ:
    return
  if '_ARGCOMPLETE_COMP_WORDBREAKS' not in os.environ:
    # The default would \ escape : and . -- bud tugley for GRIs.
    os.environ['_ARGCOMPLETE_COMP_WORDBREAKS'] = '\t"\'@><;|&('
  mute_stderr = None
  namespace = None
  try:
    # Monkeypatch argcomplete argparse Namespace to be the Calliope extended
    # Namespace so the parsed_args passed to the completers is an extended
    # Namespace object.
    namespace = argcomplete.argparse.Namespace
    argcomplete.argparse.Namespace = parser_extensions.Namespace
    # Monkeypatch disable argcomplete.mute_stderr if the caller wants to see
    # error output. This is indispensible for debugging Cloud SDK completers.
    # It's much less verbose than the argcomplete _ARC_DEBUG output.
    if '_ARGCOMPLETE_TRACE' in os.environ:
      mute_stderr = argcomplete.mute_stderr

      def _DisableMuteStderr():
        pass

      argcomplete.mute_stderr = _DisableMuteStderr

    completer = _CompletionFinder()
    # pylint: disable=not-callable
    completer(
        ai,
        always_complete_options=False,
        **kwargs)
  finally:
    if namespace:
      argcomplete.argparse.Namespace = namespace
    if mute_stderr:
      argcomplete.mute_stderr = mute_stderr


class CLI(object):
  """A generated command line tool."""

  def __init__(self, name, top_element, pre_run_hooks, post_run_hooks,
               known_error_handler):
    # pylint: disable=protected-access
    self.__name = name
    self.__parser = top_element._parser
    self.__top_element = top_element
    self.__pre_run_hooks = pre_run_hooks
    self.__post_run_hooks = post_run_hooks
    self.__known_error_handler = known_error_handler

  def _TopElement(self):
    return self.__top_element

  def _ConvertNonAsciiArgsToUnicode(self, args):
    """Converts non-ascii args to unicode.

    The args most likely came from sys.argv, and Python 2.7 passes them in as
    bytestrings instead of unicode.

    Args:
      args: [str], The list of args to convert.

    Raises:
      InvalidCharacterInArgException if a non-ascii arg cannot be converted to
      unicode.

    Returns:
      A new list of args with non-ascii args converted to unicode.
    """
    console_encoding = console_attr.GetConsoleAttr().GetEncoding()
    filesystem_encoding = sys.getfilesystemencoding()
    argv = []
    for arg in args:

      try:
        arg.encode('ascii')
        # Already ascii.
        argv.append(arg)
        continue
      except UnicodeError:
        pass

      try:
        # Convert bytestring to unicode using the console encoding.
        argv.append(unicode(arg, console_encoding))
        continue
      except TypeError:
        # Already unicode.
        argv.append(arg)
        continue
      except UnicodeError:
        pass

      try:
        # Convert bytestring to unicode using the filesystem encoding.
        # A pathname could have been passed in rather than typed, and
        # might not match the user terminal encoding, but still be a valid
        # path. For example: $ foo $(grep -l bar *)
        argv.append(unicode(arg, filesystem_encoding))
        continue
      except UnicodeError:
        pass

      # Can't convert to unicode -- bail out.
      raise exceptions.InvalidCharacterInArgException([self.name] + args, arg)

    return argv

  def _EnforceAsciiArgs(self, argv):
    """Fail if any arg in argv is not ascii.

    Args:
      argv: [str], The list of args to check.

    Raises:
      InvalidCharacterInArgException if there is a non-ascii arg.
    """
    for arg in argv:
      try:
        arg.decode('ascii')
      except UnicodeError:
        raise exceptions.InvalidCharacterInArgException([self.name] + argv, arg)

  @property
  def name(self):
    return self.__name

  @property
  def top_element(self):
    return self.__top_element

  def IsValidCommand(self, cmd):
    """Checks if given command exists.

    Args:
      cmd: [str], The command path not including any arguments.

    Returns:
      True, if the given command exist, False otherwise.
    """
    return self.__top_element.IsValidSubPath(cmd)

  def Execute(self, args=None, call_arg_complete=True):
    """Execute the CLI tool with the given arguments.

    Args:
      args: [str], The arguments from the command line or None to use sys.argv
      call_arg_complete: Call the _ArgComplete function if True

    Returns:
      The result of executing the command determined by the command
      implementation.

    Raises:
      ValueError: for ill-typed arguments.
    """
    if isinstance(args, basestring):
      raise ValueError('Execute expects an iterable of strings, not a string.')

    # The argparse module does not handle unicode args when run in Python 2
    # because it uses str(x) even when type(x) is unicode. This sets itself up
    # for failure because it converts unicode strings back to byte strings which
    # will trigger ASCII codec exceptions. It works in Python 3 because str() is
    # equivalent to unicode() in Python 3. The next Pythonically magic and dirty
    # statement coaxes the Python 3 behavior out of argparse running in
    # Python 2. Doing it here ensures that the workaround is in place for
    # calliope argparse use cases.
    argparse.str = unicode

    if call_arg_complete:
      _ArgComplete(self.__top_element.ai)

    if not args:
      args = sys.argv[1:]

    # help ... is the same as ... --help or ... --document=style=help. We use
    # --document=style=help to signal the metrics.Help() 'help' label in
    # actions.RenderDocumentAction().Action(). It doesn't matter if we append
    # to a command that already has --help or --document=style=... because the
    # first --help/--document from the left takes effect. Note that
    # `help ... --help` produces help for the help command itself.
    if args and args[0] == 'help' and '--help' not in args:
      args = args[1:] + ['--document=style=help']

    # Look for a --configuration flag and update property state based on
    # that before proceeding to the main argparse parse step.
    named_configs.FLAG_OVERRIDE_STACK.PushFromArgs(args)
    properties.VALUES.PushInvocationValues()

    # Set the command name in case an exception happens before the command name
    # is finished parsing.
    command_path_string = self.__name
    specified_arg_names = None

    argv = self._ConvertNonAsciiArgsToUnicode(args)
    old_user_output_enabled = None
    old_verbosity = None
    try:
      args = self.__parser.parse_args(argv)
      command_path_string = '.'.join(args.command_path)
      if not args.calliope_command.IsUnicodeSupported():
        self._EnforceAsciiArgs(argv)
      specified_arg_names = args.GetSpecifiedArgNames()

      # -h|--help|--document are dispatched by parse_args and never get here.

      # Now that we have parsed the args, reload the settings so the flags will
      # take effect.  These will use the values from the properties.
      old_user_output_enabled = log.SetUserOutputEnabled(None)
      old_verbosity = log.SetVerbosity(None)

      # Set the command_name property so it is persisted until the process ends.
      # Only do this for the top level command that can be detected by looking
      # at the stack. It will have one initial level, and another level added by
      # the PushInvocationValues earlier in this method.
      if len(properties.VALUES.GetInvocationStack()) == 2:
        properties.VALUES.metrics.command_name.Set(command_path_string)
      # Set the invocation value for all commands, this is lost when popped
      properties.VALUES.SetInvocationValue(
          properties.VALUES.metrics.command_name, command_path_string, None)

      for hook in self.__pre_run_hooks:
        hook.Run(command_path_string)

      resources = args.calliope_command.Run(cli=self, args=args)

      for hook in self.__post_run_hooks:
        hook.Run(command_path_string)

      # Preserve generator or static list resources.

      if isinstance(resources, types.GeneratorType):

        def _Yield():
          """Activates generator exceptions."""
          try:
            for resource in resources:
              yield resource
          except Exception as exc:  # pylint: disable=broad-except
            self._HandleAllErrors(exc, command_path_string, specified_arg_names)

        return _Yield()

      # Do this last. If there is an error, the error handler will log the
      # command execution along with the error.
      metrics.Commands(
          command_path_string, config.CLOUD_SDK_VERSION, specified_arg_names)
      return resources

    except Exception as exc:  # pylint: disable=broad-except
      self._HandleAllErrors(exc, command_path_string, specified_arg_names)

    finally:
      properties.VALUES.PopInvocationValues()
      named_configs.FLAG_OVERRIDE_STACK.Pop()
      # Reset these values to their previous state now that we popped the flag
      # values.
      if old_user_output_enabled is not None:
        log.SetUserOutputEnabled(old_user_output_enabled)
      if old_verbosity is not None:
        log.SetVerbosity(old_verbosity)

  def _HandleAllErrors(self, exc, command_path_string, specified_arg_names):
    """Handle all errors.

    Args:
      exc: Exception, The exception that was raised.
      command_path_string: str, The '.' separated command path.
      specified_arg_names: [str], The specified arg named scrubbed for metrics.

    Raises:
      exc or a core.exceptions variant that does not produce a stack trace.
    """
    known_exc, print_error = exceptions.ConvertKnownError(exc)
    error_extra_info = {'error_code': getattr(exc, 'exit_code', 1)}
    if isinstance(exc, exceptions.HttpException):
      error_extra_info['http_status_code'] = exc.payload.status_code

    metrics.Commands(
        command_path_string, config.CLOUD_SDK_VERSION, specified_arg_names,
        error=exc.__class__, error_extra_info=error_extra_info)
    metrics.Error(command_path_string, exc.__class__, specified_arg_names,
                  error_extra_info=error_extra_info)

    if known_exc:
      msg = u'({0}) {1}'.format(
          console_attr.EncodeForConsole(command_path_string),
          console_attr.EncodeForConsole(known_exc))
      log.debug(msg, exc_info=sys.exc_info())
      if print_error:
        log.error(msg)
      # Uncaught errors will be handled in gcloud_main.
      if self.__known_error_handler:
        self.__known_error_handler(exc)
      if properties.VALUES.core.print_handled_tracebacks.GetBool():
        raise
      self._Exit(known_exc)
    else:
      # Make sure any uncaught exceptions still make it into the log file.
      log.debug(console_attr.EncodeForConsole(exc), exc_info=sys.exc_info())
      raise

  def _Exit(self, exc):
    """This method exists so we can mock this out during testing to not exit."""
    # exit_code won't be defined in the KNOWN_ERRORs classes
    sys.exit(getattr(exc, 'exit_code', 1))
