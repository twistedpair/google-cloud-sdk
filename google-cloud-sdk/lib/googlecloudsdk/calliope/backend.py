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
from googlecloudsdk.calliope import display_info
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parse_errors
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.updater import update_manager
from googlecloudsdk.core.util import pkg_resources


_MUTEX_GROUP_REQUIRED_DESCRIPTION = 'Exactly one of these must be specified:'
_MUTEX_GROUP_OPTIONAL_DESCRIPTION = 'At most one of these may be specified:'


class ArgumentException(Exception):
  """ArgumentException is for problems with the provided arguments."""
  pass


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


class ArgumentParserError(object):
  """Object to store the ArgumentParser error and extra information.

    Args:
      dotted_command_path: str, as much as we could parse from the path to the
          command, separating elements by dots.
      error: class, the class to the error we want to report
      error_extra_info: str, json string for extra information that we want
          recorded with the error.
  """

  def __init__(self, dotted_command_path, error, error_extra_info):
    self.dotted_command_path = dotted_command_path
    self.error = error
    self.error_extra_info = error_extra_info


class ArgumentParser(argparse.ArgumentParser):
  """A custom subclass for arg parsing behavior.

  This overrides the default argparse parser.  It only changes a few things,
  mostly around the printing of usage error messages.
  """

  def __init__(self, *args, **kwargs):
    self._calliope_command = kwargs.pop('calliope_command')
    self._flag_collection = kwargs.pop('flag_collection')
    self._is_group = isinstance(self._calliope_command, CommandGroup)
    self._error_to_report = None
    self._remainder_action = None
    super(ArgumentParser, self).__init__(*args, **kwargs)

  # Assume we will never have a flag called ----calliope-internal...
  CIDP = '__calliope_internal_deepest_parser'

  def GetFlagCollection(self):
    return self._flag_collection

  def AddRemainderArgument(self, *args, **kwargs):
    """Add an argument representing '--' followed by anything.

    This argument is bound to the parser, so the parser can use it's helper
    methods to parse.

    GA track methods are made non-strict for backwards compatibility. If a BETA
    track alternate exists, it is used as the suggested strict alternate. See
    arg_parsers.RemainderAction for more information.

    Args:
      *args: The arguments for the action.
      **kwargs: They keyword arguments for the action.

    Raises:
      ArgumentException: If there already is a Remainder Action bound to this
      parser.

    Returns:
      The created action.
    """
    if self._remainder_action:
      raise ArgumentException('There can only be one pass through argument.')
    kwargs['action'] = arg_parsers.RemainderAction
    track = self._calliope_command.ReleaseTrack()
    # pylint:disable=protected-access
    cli_generator = self._calliope_command._cli_generator
    alternates = cli_generator.ReplicateCommandPathForAllOtherTracks(
        self._calliope_command.GetPath())
    # Assume GA has backwards compatability otherwise assume strict.
    is_strict = track is not base.ReleaseTrack.GA
    strict_alternate = None
    if not is_strict and base.ReleaseTrack.BETA in alternates:
      strict_alternate = ' '.join(alternates[base.ReleaseTrack.BETA])
    self._remainder_action = self.add_argument(
        is_strict=is_strict, strict_alternate=strict_alternate, *args, **kwargs)
    return self._remainder_action

  def parse_known_args(self, args=None, namespace=None):
    """Overrides argparse.ArgumentParser's .parse_known_args method."""
    if args is None:
      args = sys.argv[1:]
    if namespace is None:
      namespace = argparse.Namespace()
    try:
      if self._remainder_action:
        # Remove remainder_action so it is not parsed regularly.
        self._actions.remove(self._remainder_action)
        # Split on first -- if it exists
        namespace, args = self._remainder_action.ParseKnownArgs(
            args, namespace)
      namespace, unknown_args = super(
          ArgumentParser, self).parse_known_args(args, namespace)
    finally:
      # Replace action for help message and ArgumentErrors.
      if self._remainder_action:
        self._actions.append(self._remainder_action)

    # Pass back a reference to the deepest parser used in the parse
    # as part of the returned args.
    if not hasattr(namespace, self.CIDP):
      setattr(namespace, self.CIDP, self)
    return (namespace, unknown_args)

  def parse_args(self, args=None, namespace=None):
    """Overrides argparse.ArgumentParser's .parse_args method."""
    namespace, unknown_args = self.parse_known_args(args, namespace)
    if not unknown_args:
      return namespace

    # Content of these lines differs from argparser's parse_args().
    deepest_parser = getattr(namespace, self.CIDP, self)

    # pylint:disable=protected-access
    if deepest_parser._remainder_action:
      # Assume the user wanted to pass all arguments after last recognized
      # arguments into _remainder_action. Either do this with a warning or
      # fail depending on strictness.
      # pylint:disable=protected-access
      namespace, unknown_args = (
          deepest_parser._remainder_action.ParseRemainingArgs(
              unknown_args, namespace, args))
      # There still may be unknown_args that came before the last known arg.
      if not unknown_args:
        return namespace

    # Add a message for each unknown argument.  For each, try to come up with
    # a suggestion based on text distance.  If one is close enough, print a
    # 'did you mean' message along with that argument.
    messages = []
    suggester = usage_text.TextChoiceSuggester()
    # pylint:disable=protected-access, This is an instance of this class.
    for flag in deepest_parser._calliope_command.GetAllAvailableFlags():
      options = flag.option_strings
      if options:
        # This is a flag, add all its names as choices.
        suggester.AddChoices(options)
        # Add any aliases as choices as well, but suggest the primary name.
        aliases = getattr(flag, 'suggestion_aliases', None)
        if aliases:
          suggester.AddAliases(aliases, options[0])

    suggestions = {}
    for arg in unknown_args:
      # Only do this for flag names.
      if arg.startswith('--'):
        flag = arg.split('=')[0]
        suggestion = suggester.GetSuggestion(flag)
      else:
        suggestion = None
      if suggestion:
        suggestions[arg] = suggestion
        messages.append(arg + " (did you mean '{0}'?)".format(suggestion))
      else:
        messages.append(arg)

    error_extra_info = {
        'total_unrecognized': len(unknown_args),
        'total_suggestions': len(suggestions),
        'suggestions': suggestions,
    }
    deepest_parser._error_to_report = ArgumentParserError(
        '.'.join(deepest_parser._calliope_command.GetPath()),
        parse_errors.UnrecognizedArguments,
        error_extra_info)

    # If there is a single arg, put it on the same line.  If there are multiple
    # add each on it's own line for better clarity.
    separator = u'\n  ' if len(messages) > 1 else u' '
    deepest_parser.error(u'unrecognized arguments:{0}{1}'.format(
        separator, separator.join(messages)))

  def _check_value(self, action, value):
    """Overrides argparse.ArgumentParser's ._check_value(action, value) method.

    Args:
      action: argparse.Action, The action being checked against this value.
      value: The command line argument provided that needs to correspond to this
          action.

    Raises:
      argparse.ArgumentError: If the action and value don't work together.
    """
    is_subparser = isinstance(action, CloudSDKSubParsersAction)

    # When using tab completion, argcomplete monkey patches various parts of
    # argparse and interferes with the normal argument parsing flow.  Here, we
    # need to set self._orig_class because argcomplete compares this
    # directly to argparse._SubParsersAction to see if it should recursively
    # patch this parser.  It should really check to see if it is a subclass
    # but alas, it does not.  If we don't set this, argcomplete will not patch,
    # our subparser and completions below this point wont work.  Normally we
    # would just set this in action.IsValidChoice() but sometimes this
    # sub-element has already been loaded and is already in action.choices.  In
    # either case, we still need argcomplete to patch this subparser so it
    # can compute completions below this point.
    if is_subparser and '_ARGCOMPLETE' in os.environ:
      # pylint:disable=protected-access, Required by argcomplete.
      action._orig_class = argparse._SubParsersAction

    # This is copied from this method in argparse's version of this method.
    if action.choices is None or value in action.choices:
      return

    # We add this to check if we can lazy load the element.
    if is_subparser and action.IsValidChoice(value):
      return

    # Not something we know, raise an error.
    # pylint:disable=protected-access
    cli_generator = self._calliope_command._cli_generator
    missing_components = cli_generator.ComponentsForMissingCommand(
        self._calliope_command.GetPath() + [value])
    if missing_components:
      msg = ('You do not currently have this command group installed.  Using '
             'it requires the installation of components: '
             '[{missing_components}]'.format(
                 missing_components=', '.join(missing_components)))
      update_manager.UpdateManager.EnsureInstalledAndRestart(
          missing_components, msg=msg)

    if is_subparser:
      # We are going to show the usage anyway, which requires loading
      # everything.  Do this here so that choices gets populated.
      self._calliope_command.LoadAllSubElements()

    # Command is not valid, see what we can suggest as a fix...
    message = u"Invalid choice: '{0}'.".format(value)

    # Determine if the requested command is available in another release track.
    existing_alternatives = self._ExistingAlternativeReleaseTracks(value)
    if existing_alternatives:
      message += (u'\nThis command is available in one or more alternate '
                  u'release tracks.  Try:\n  ')
      message += u'\n  '.join(existing_alternatives)

      # Log to analytics the attempt to execute a command.
      # We know the user entered 'value' is a valid command in a different
      # release track. It's safe to include it.
      self._error_to_report = ArgumentParserError(
          '.'.join(self._calliope_command.GetPath() + [value]),
          parse_errors.WrongTrackException,
          {'suggestions': existing_alternatives})

    # See if the spelling was close to something else that exists here.
    else:
      choices = sorted(action.choices)
      suggester = usage_text.TextChoiceSuggester(choices)
      suggester.AddSynonyms()
      suggestion = suggester.GetSuggestion(value)
      if suggestion:
        message += " Did you mean '{0}'?".format(suggestion)
      elif not isinstance(action, CloudSDKSubParsersAction):
        # Command group choices will be displayed in the usage message.
        message += '\n\nValid choices are [{0}].'.format(', '.join(choices))

      # Log to analytics the attempt to execute a command.
      # We don't know if the user entered 'value' is a mistyped command or
      # some resource name that the user entered and we incorrectly thought it's
      # a command. We can't include it since it might be PII.

      error_extra_info = {
          'total_unrecognized': 1,
          'total_suggestions': 1 if suggestion else 0,
          'suggestions': [suggestion] if suggestion else choices,
      }
      self._error_to_report = ArgumentParserError(
          '.'.join(self._calliope_command.GetPath()),
          parse_errors.ParsingCommandException,
          error_extra_info)

    raise argparse.ArgumentError(action, message)

  def _ExistingAlternativeReleaseTracks(self, value):
    """Gets the path of alternatives for the command in other release tracks.

    Args:
      value: str, The value being parsed.

    Returns:
      [str]: The names of alternate commands that the user may have meant.
    """
    existing_alternatives = []
    # Get possible alternatives.
    # pylint:disable=protected-access
    cli_generator = self._calliope_command._cli_generator
    alternates = cli_generator.ReplicateCommandPathForAllOtherTracks(
        self._calliope_command.GetPath() + [value])
    # See if the command is actually enabled in any of those alternative tracks.
    if alternates:
      top_element = self._calliope_command._TopCLIElement()
      # Sort by the release track prefix.
      for _, command_path in sorted(alternates.iteritems(),
                                    key=lambda x: x[0].prefix):
        alternative_cmd = top_element.LoadSubElementByPath(command_path[1:])
        if alternative_cmd and not alternative_cmd.IsHidden():
          existing_alternatives.append(' '.join(command_path))
    return existing_alternatives

  def _ReportErrorMetricsHelper(self, dotted_command_path, error,
                                error_extra_info=None):
    """Log `Commands` and `Error` Google Analytics events for an error.

    Args:
      dotted_command_path: str, The dotted path to as much of the command as we
          can identify before an error. Example: gcloud.projects
      error: class, The class (not the instance) of the Exception for an error.
      error_extra_info: {str: json-serializable}, A json serializable dict of
        extra info that we want to log with the error. This enables us to write
        queries that can understand the keys and values in this dict.
    """
    metrics.Commands(
        dotted_command_path,
        config.CLOUD_SDK_VERSION,
        self._flag_collection,
        error=error,
        error_extra_info=error_extra_info)
    metrics.Error(
        dotted_command_path,
        error,
        self._flag_collection,
        error_extra_info=error_extra_info)

  def ReportErrorMetrics(self, message):
    """Report Command and Error metrics in case of argparse errors."""

    if self._error_to_report:
      self._ReportErrorMetricsHelper(
          self._error_to_report.dotted_command_path,
          self._error_to_report.error,
          self._error_to_report.error_extra_info)
      return

    # No recorded error from upstream, try to detect error from message.

    dotted_command_path = '.'.join(self._calliope_command.GetPath())

    if 'too few arguments' in message:
      self._ReportErrorMetricsHelper(
          dotted_command_path,
          parse_errors.TooFewArgumentsException)
      return

    re_result = re.search('argument (.+?) is required', message)
    if re_result:
      req_argument = re_result.group(1)
      self._ReportErrorMetricsHelper(
          dotted_command_path,
          parse_errors.RequiredArgumentException,
          {'required': req_argument})
      return

    re_result = re.search('one of the arguments (.+?) is required', message)
    if re_result:
      req_argument = re_result.group(1)
      self._ReportErrorMetricsHelper(
          dotted_command_path,
          parse_errors.RequiredArgumentGroupException,
          {'required': req_argument})
      return

    # Catch all for any error we didn't explicitly detect
    self._ReportErrorMetricsHelper(
        dotted_command_path,
        parse_errors.OtherParsingError)

  def error(self, message):
    """Overrides argparse.ArgumentParser's .error(message) method.

    Specifically, it avoids reprinting the program name and the string "error:".

    Args:
      message: str, The error message to print.
    """
    self.ReportErrorMetrics(message)

    # No need to output help/usage text if we are in completion mode. However,
    # we do need to populate group/command level choices. These choices are not
    # loaded when there is a parser error since we do lazy loading.
    if '_ARGCOMPLETE' in os.environ:
      # pylint:disable=protected-access
      if self._calliope_command._sub_parser:
        self._calliope_command.LoadAllSubElements()
    else:
      message = console_attr.EncodeForOutput(message)
      log.error(u'({prog}) {message}'.format(prog=self.prog, message=message))
      # multi-line message means hints already added, no need for usage.
      # pylint:disable=protected-access
      if '\n' not in message:
        argparse._sys.stderr.write(self._calliope_command.GetUsage())

    self.exit(2)

  def _parse_optional(self, arg_string):
    """Overrides argparse.ArgumentParser's ._parse_optional method.

    This allows the parser to have leading flags included in the grabbed
    arguments and stored in the namespace.

    Args:
      arg_string: str, The argument string.

    Returns:
      The normal return value of argparse.ArgumentParser._parse_optional.
    """
    positional_actions = self._get_positional_actions()
    option_tuple = super(ArgumentParser, self)._parse_optional(arg_string)
    # If parse_optional finds an action for this arg_string, use that option.
    # Note: option_tuple = (action, option_string, explicit_arg) or None
    known_option = option_tuple and option_tuple[0]
    if (len(positional_actions) == 1 and
        positional_actions[0].nargs == argparse.REMAINDER and
        not known_option):
      return None
    return option_tuple

  def _get_values(self, action, arg_strings):
    """Overrides argparse.ArgumentParser's ._get_values method.

    This override does not actually change any behavior.  We use this hook to
    grab the flags and arguments that are actually seen at parse time.  The
    resulting namespace has entries for every argument (some with defaults) so
    we can't know which the user actually typed.

    Args:
      action: Action, the action that is being processed.
      arg_strings: [str], The values provided for this action.

    Returns:
      Whatever the parent method returns.
    """
    if action.dest != argparse.SUPPRESS:
      # Don't look at the action unless it is a real argument or flag. The
      # suppressed destination indicates that it is a SubParsers action.
      name = None
      if action.option_strings:
        # This is a flag, save the first declared name of the flag.
        name = action.option_strings[0]
      elif arg_strings:
        # This is a positional and there are arguments to consume.  Optional
        # positionals will always get to this method, so we need to ignore the
        # ones for which a value was not actually provided.  If it is provided,
        # save the metavar name or the destination name.
        name = action.metavar if action.metavar else action.dest
        if action.nargs and action.nargs != '?':
          # This arg takes in multiple values, record how many were provided.
          # (? means 0 or 1, so treat that as an arg that takes a single value.
          name += ':' + str(len(arg_strings))
      if name:
        self._flag_collection.append(name)
    return super(ArgumentParser, self)._get_values(action, arg_strings)

  def _get_option_tuples(self, option_string):
    """Overrides argparse.ArgumentParser's ._get_option_tuples method.

    Cloud SDK no longer supports flag abbreviations, so it always returns []
    for the non-arg-completion case to indicate no abbreviated flag matches.

    Args:
      option_string: The option string to match.

    Returns:
      A list of matching flag tuples.
    """
    if '_ARGCOMPLETE' in os.environ:
      return super(ArgumentParser, self)._get_option_tuples(option_string)
    return []


# pylint:disable=protected-access
class CloudSDKSubParsersAction(argparse._SubParsersAction):
  """A custom subclass for arg parsing behavior.

  While the above ArgumentParser overrides behavior for parsing the flags
  associated with a specific group or command, this class overrides behavior
  for loading those sub parsers.  We use this to intercept the parsing right
  before it needs to start parsing args for sub groups and we then load the
  specific sub group it needs.
  """

  def __init__(self, *args, **kwargs):
    self._calliope_command = kwargs.pop('calliope_command')
    self._flag_collection = kwargs.pop('flag_collection')
    super(CloudSDKSubParsersAction, self).__init__(*args, **kwargs)

  def add_parser(self, name, **kwargs):
    # Pass the same flag collection down to any sub parsers that are created.
    kwargs['flag_collection'] = self._flag_collection
    # Pass the same abbreviated flags down to any sub parsers that are created.
    return super(CloudSDKSubParsersAction, self).add_parser(name, **kwargs)

  def IsValidChoice(self, choice):
    """Determines if the given arg is a valid sub group or command.

    Args:
      choice: str, The name of the sub element to check.

    Returns:
      bool, True if the given item is a valid sub element, False otherwise.
    """
    # When using tab completion, argcomplete monkey patches various parts of
    # argparse and interferes with the normal argument parsing flow.  Usually
    # it is sufficient to check if the given choice is valid here, but delay
    # the loading until __call__ is invoked later during the parsing process.
    # During completion time, argcomplete tries to patch the subparser before
    # __call__ is called, so nothing has been loaded yet.  We need to force
    # load things here so that there will be something loaded for it to patch.
    if '_ARGCOMPLETE' in os.environ:
      self._calliope_command.LoadSubElement(choice)
    return self._calliope_command.IsValidSubElement(choice)

  def __call__(self, parser, namespace, values, option_string=None):
    # This is the name of the arg that is the sub element that needs to be
    # loaded.
    parser_name = values[0]
    # Load that element if it's there.  If it's not valid, nothing will be
    # loaded and normal error handling will take over.
    if self._calliope_command:
      self._calliope_command.LoadSubElement(parser_name)
    super(CloudSDKSubParsersAction, self).__call__(
        parser, namespace, values, option_string=option_string)


class ArgumentGroupAttr(object):
  """Argument group attributes."""

  def __init__(self, description=None, is_mutex=False, is_required=False):
    self.description = description
    self.is_mutex = is_mutex
    self.is_required = is_required


class ArgumentInterceptor(object):
  """ArgumentInterceptor intercepts calls to argparse parsers.

  The argparse module provides no public way to access a complete list of
  all arguments, and we need to know these so we can do validation of arguments
  when this library is used in the python interpreter mode. Argparse itself does
  the validation when it is run from the command line.

  Attributes:
    parser: argparse.Parser, The parser whose methods are being intercepted.
    allow_positional: bool, Whether or not to allow positional arguments.
    defaults: {str:obj}, A dict of {dest: default} for all the arguments added.
    required: [str], A list of the dests for all required arguments.
    dests: [str], A list of the dests for all arguments.
    positional_args: [argparse.Action], A list of the positional arguments.
    flag_args: [argparse.Action], A list of the flag arguments.

  Raises:
    ArgumentException: if a positional argument is made when allow_positional
        is false.
  """

  class ParserData(object):

    def __init__(self, command_name):
      self.command_name = command_name
      self.defaults = {}
      self.required = []
      self.dests = []
      self.group_attr = {}
      self.argument_groups = {}
      self.mutex_groups = {}
      self.required_mutex_groups = set()
      self.positional_args = []
      self.flag_args = []
      self.ancestor_flag_args = []
      self.groups = {}
      self.display_info = display_info.DisplayInfo()

  def __init__(self, parser, is_root, cli_generator, allow_positional,
               data=None, mutex_group_id=None, argument_group_id=None):
    self.parser = parser
    self.is_root = is_root
    self.cli_generator = cli_generator
    self.allow_positional = allow_positional
    # If this is an argument group within a command, use the data from the
    # parser for the entire command.  If it is the command itself, create a new
    # data object and extract the command name from the parser.
    if data:
      self.data = data
    else:
      self.data = ArgumentInterceptor.ParserData(
          command_name=self.parser._calliope_command.GetPath())
    self.mutex_group_id = mutex_group_id
    self.argument_group_id = argument_group_id

  @property
  def defaults(self):
    return self.data.defaults

  @property
  def display_info(self):
    return self.data.display_info

  @property
  def required(self):
    return self.data.required

  @property
  def group_attr(self):
    return self.data.group_attr

  @property
  def dests(self):
    return self.data.dests

  @property
  def argument_groups(self):
    return self.data.argument_groups

  @property
  def mutex_groups(self):
    return self.data.mutex_groups

  @property
  def required_mutex_groups(self):
    return self.data.required_mutex_groups

  @property
  def positional_args(self):
    return self.data.positional_args

  @property
  def flag_args(self):
    return self.data.flag_args

  @property
  def ancestor_flag_args(self):
    return self.data.ancestor_flag_args

  # pylint: disable=g-bad-name
  def add_argument(self, *args, **kwargs):
    """add_argument intercepts calls to the parser to track arguments."""
    # TODO(user): do not allow short-options without long-options.

    # we will choose the first option as the name
    name = args[0]
    dest = kwargs.get('dest')
    if not dest:
      # this is exactly what happens in argparse
      dest = name.lstrip(self.parser.prefix_chars).replace('-', '_')

    default = kwargs.get('default')
    required = kwargs.get('required')

    # A flag that can only be supplied where it is defined and not propagated to
    # subcommands.
    do_not_propagate = kwargs.pop('do_not_propagate', False)
    # A global flag that is added at each level explicitly because each command
    # has a different behavior (like -h).
    is_replicated = kwargs.pop('is_replicated', False)
    # This is used for help printing.  A flag is considered global if it is
    # added at the root of the CLI tree, or if it is explicitly added to every
    # command level.
    is_global = self.is_root or is_replicated
    # The flag category name, None for no category. This is also used for help
    # printing. Flags in the same category are grouped together in a section
    # named "{category} FLAGS".
    category = kwargs.pop('category', None)
    # Any alias this flag has for the purposes of the "did you mean"
    # suggestions.
    suggestion_aliases = kwargs.pop('suggestion_aliases', [])
    # The resource name for the purposes of doing remote completion.
    completion_resource = kwargs.pop('completion_resource', None)
    # An explicit command to run for remote completion instead of the default
    # for this resource type.
    list_command_path = kwargs.pop('list_command_path', None)
    # Callback function that receives the currently entered args at the time of
    # remote completion processing, and returns the command to run.
    list_command_callback_fn = kwargs.pop('list_command_callback_fn', None)
    # hidden=True => help=argparse.SUPPRESS, but retains help and detailed_help
    # in the source.
    if kwargs.pop('hidden', False):
      kwargs['help'] = argparse.SUPPRESS

    positional = not name.startswith('-')
    if positional:
      if not self.allow_positional:
        # TODO(user): More informative error message here about which group
        # the problem is in.
        raise ArgumentException(
            'Illegal positional argument [{0}] for command [{1}]'.format(
                name, self.data.command_name))
      if '-' in name:
        raise ArgumentException(
            "Positional arguments cannot contain a '-'. Illegal argument [{0}] "
            'for command [{1}]'.format(name, self.data.command_name))
      if category:
        raise ArgumentException(
            'Positional argument [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      if suggestion_aliases:
        raise ArgumentException(
            'Positional argument [{0}] cannot have suggestion aliases in '
            'command [{1}]'.format(name, self.data.command_name))

    self.defaults[dest] = default
    if self.mutex_group_id:
      self.mutex_groups[dest] = self.mutex_group_id
      if self.parser.required:
        self.required_mutex_groups.add(self.mutex_group_id)
        self.group_attr[self.mutex_group_id] = ArgumentGroupAttr(
            description=_MUTEX_GROUP_REQUIRED_DESCRIPTION,
            is_mutex=True,
            is_required=True,
        )
      else:
        self.group_attr[self.mutex_group_id] = ArgumentGroupAttr(
            description=_MUTEX_GROUP_OPTIONAL_DESCRIPTION,
            is_mutex=True,
            is_required=False,
        )
    elif self.argument_group_id:
      self.argument_groups[dest] = self.argument_group_id
      if self.parser.description:
        description = self.parser.description
      elif self.parser.title:
        description = self.parser.title.rstrip('.') + ':'
      else:
        description = None
      self.group_attr[self.argument_group_id] = ArgumentGroupAttr(
          description=description,
          is_mutex=False,
          is_required=False,
      )
    if required:
      self.required.append(dest)
    self.dests.append(dest)

    if positional and 'metavar' not in kwargs:
      kwargs['metavar'] = name.upper()
    if kwargs.get('nargs') is argparse.REMAINDER:
      added_argument = self.parser.AddRemainderArgument(*args, **kwargs)
    else:
      added_argument = self.parser.add_argument(*args, **kwargs)
    self._AddRemoteCompleter(added_argument, completion_resource,
                             list_command_path, list_command_callback_fn)

    if positional:
      if category:
        raise ArgumentException(
            'Positional argument [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      self.positional_args.append(added_argument)
    else:
      if category and required:
        raise ArgumentException(
            'Required flag [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      if category == 'REQUIRED':
        raise ArgumentException(
            "Flag [{0}] cannot have category='REQUIRED' in "
            'command [{1}]'.format(name, self.data.command_name))
      added_argument.category = category
      added_argument.do_not_propagate = do_not_propagate
      added_argument.is_replicated = is_replicated
      added_argument.is_global = is_global
      added_argument.required = required
      added_argument.suggestion_aliases = suggestion_aliases
      if isinstance(added_argument.choices, dict):
        # choices is a name: description dict. Set the choices attribute to the
        # keys for argparse and the choices_help attribute to the dict for
        # the markdown generator.
        setattr(added_argument, 'choices_help', added_argument.choices)
        added_argument.choices = sorted(added_argument.choices.keys())
      self.flag_args.append(added_argument)

      inverted_flag = self._AddInvertedBooleanFlagIfNecessary(
          added_argument, name, dest, kwargs)
      if inverted_flag:
        inverted_flag.category = category
        inverted_flag.do_not_propagate = do_not_propagate
        inverted_flag.is_replicated = is_replicated
        inverted_flag.is_global = is_global
        # Don't add suggestion aliases for the inverted flag.  It can only map
        # to one or the other.
        self.flag_args.append(inverted_flag)

    return added_argument

  # pylint: disable=redefined-builtin
  def register(self, registry_name, value, object):
    return self.parser.register(registry_name, value, object)

  def set_defaults(self, **kwargs):
    return self.parser.set_defaults(**kwargs)

  def get_default(self, dest):
    return self.parser.get_default(dest)

  def add_argument_group(self, *args, **kwargs):
    new_parser = self.parser.add_argument_group(*args, **kwargs)
    return ArgumentInterceptor(parser=new_parser,
                               is_root=self.is_root,
                               cli_generator=self.cli_generator,
                               allow_positional=self.allow_positional,
                               data=self.data,
                               argument_group_id=id(new_parser))

  def add_mutually_exclusive_group(self, **kwargs):
    new_parser = self.parser.add_mutually_exclusive_group(**kwargs)
    return ArgumentInterceptor(parser=new_parser,
                               is_root=self.is_root,
                               cli_generator=self.cli_generator,
                               allow_positional=self.allow_positional,
                               data=self.data,
                               mutex_group_id=id(new_parser))

  def AddFlagActionFromAncestors(self, action):
    """Add a flag action to this parser, but segregate it from the others.

    Segregating the action allows automatically generated help text to ignore
    this flag.

    Args:
      action: argparse.Action, The action for the flag being added.

    """
    # pylint:disable=protected-access, simply no other way to do this.
    self.parser._add_action(action)
    # explicitly do this second, in case ._add_action() fails.
    self.data.ancestor_flag_args.append(action)

  def _AddInvertedBooleanFlagIfNecessary(self, added_argument, name, dest,
                                         original_kwargs):
    """Determines whether to create the --no-* flag and adds it to the parser.

    Args:
      added_argument: The argparse argument that was previously created.
      name: str, The name of the flag.
      dest: str, The dest field of the flag.
      original_kwargs: {str: object}, The original set of kwargs passed to the
        ArgumentInterceptor.

    Returns:
      The new argument that was added to the parser or None, if it was not
      necessary to create a new argument.
    """
    action = original_kwargs.get('action')
    # There are a few legitimate explicit --no-foo flags.
    should_invert, prop = self._ShouldInvertBooleanFlag(name, action)
    if not should_invert:
      return

    default = original_kwargs.get('default', False)
    help_str = original_kwargs.get('help')

    # Add hidden --no-foo for the --foo Boolean flag. The inverted flag will
    # have the same dest and mutually exclusive group as the original flag.
    inverted_name = '--no-' + name[2:]
    # Explicit default=None yields the 'Use to disable.' text.
    show_inverted = False
    if prop or (default in (True, None) and help_str != argparse.SUPPRESS):
      if prop:
        if prop.default:
          show_inverted = True
        inverted_help = (' Overrides the default *{0}* property value'
                         ' for this command invocation. Use *{1}* to'
                         ' disable.'.format(prop.name, inverted_name))
      elif default:
        inverted_help = ' Enabled by default, use *{0}* to disable.'.format(
            inverted_name)
        show_inverted = True
      else:
        inverted_help = ' Use *{0}* to disable.'.format(inverted_name)
      # calliope.markdown.MarkdownGenerator._Details() checks and appends
      # arg.inverted_help to the detailed help markdown.  We can't do that
      # here because detailed_help may not have been set yet.
      setattr(added_argument, 'inverted_help', inverted_help)

    kwargs = dict(original_kwargs)
    if action == 'store_true':
      action = 'store_false'
    elif action == 'store_false':
      action = 'store_true'
    kwargs['action'] = action
    if not kwargs.get('dest'):
      kwargs['dest'] = dest
    kwargs['help'] = argparse.SUPPRESS

    inverted_argument = self.parser.add_argument(inverted_name, **kwargs)
    if show_inverted:
      # flag.show_inverted means display inverted_argument in the SYNOPSIS.
      setattr(added_argument, 'show_inverted', inverted_argument)
    return inverted_argument

  def _ShouldInvertBooleanFlag(self, name, action):
    """Checks if flag name with action is a Boolean flag to invert.

    Args:
      name: str, The flag name.
      action: argparse.Action, The argparse action.

    Returns:
      (False, None) if flag is not a Boolean flag or should not be inverted,
      (True, property) if flag is a Boolean flag associated with a property,
      otherwise (True, None) if flag is a pure Boolean flag.
    """
    if not name.startswith('--'):
      return False, None
    if name.startswith('--no-'):
      # --no-no-* is a no no.
      return False, None
    if '--no-' + name[2:] in self.parser._option_string_actions:
      # Don't override explicit --no-* inverted flag.
      return False, None
    if isinstance(self.parser, argparse._MutuallyExclusiveGroup):
      # Flags in mutually exclusive groups are not inverted.
      return False, None
    if action in ('store_true', 'store_false'):
      return True, None
    prop = getattr(action, 'boolean_property', None)
    if prop:
      return True, prop
    # Not a Boolean flag.
    return False, None

  def _AddRemoteCompleter(self, added_argument, completion_resource,
                          list_command_path, list_command_callback_fn):
    """Adds a remote completer to the given argument if necessary.

    Args:
      added_argument: The argparse argument that was previously created.
      completion_resource: str, The name of the resource that this argument
        corresponds to.
      list_command_path: str, The explicit calliope command to run to get the
        completions if you want to override the default for the given resource
        type. list_command_callback_fn takes precedence.
      list_command_callback_fn: function, Callback function to be called to get
        the list command. Takes precedence over list_command_path.
    """
    if not completion_resource:
      return

    if not list_command_path:
      list_command_path = completion_resource
      # alpha, beta, and preview commands need to specify list_command_path
      if (list_command_path.startswith('alpha') or
          list_command_path.startswith('beta') or
          list_command_path.startswith('preview')):
        # if list_command_path not specified don't add the completer
        completion_resource = None
      else:
        list_command_path = self._LowerCaseWithDashes(completion_resource)

    if completion_resource:
      # add a remote completer
      added_argument.completer = (
          remote_completion.RemoteCompletion.GetCompleterForResource(
              completion_resource,
              self.cli_generator.Generate,
              command_line=list_command_path,
              list_command_callback_fn=list_command_callback_fn))
      added_argument.completion_resource = completion_resource

  def _LowerCaseWithDashes(self, name):
    # Uses two passes to handle all-upper initialisms, such as fooBARBaz
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
    return s2


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
      self.short_help = self.detailed_help['brief']
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
      self._parser = ArgumentParser(
          description=self.long_help,
          add_help=False,
          prog=self.dotted_name,
          calliope_command=self,
          flag_collection=[])
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

    self.ai = ArgumentInterceptor(
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
    self._common_type._Flags(self.ai)
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
          raise ArgumentException(
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
      self._sub_parser = self._parser.add_subparsers(
          action=CloudSDKSubParsersAction, calliope_command=self,
          flag_collection=self._parser._flag_collection)
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
