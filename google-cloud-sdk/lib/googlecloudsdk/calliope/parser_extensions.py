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

"""Calliope argparse intercepts and extensions.

Calliope uses the argparse module for command line argument definition and
parsing. It intercepts some argparse methods to provide enhanced runtime help
document generation, command line usage help, error handling and argument group
conflict analysis.

The parser and intercepts are in these modules:

  parser_extensions (this module)

    Extends and intercepts argparse.ArgumentParser and the parser args
    namespace to support Command.Run() method access to info added in the
    Command.Args() method.

  parser_arguments

    Intercepts the basic argument objects and collects data for command flag
    metrics reporting.

  parser_errors

    Error/exception classes for all Calliope arg parse errors. Errors derived
    from ArgumentError have a payload used for metrics reporting.

The intercepted args namespace object passed to the Command.Run() method adds
methods to access/modify info collected during the parse.
"""

import argparse
import os
import re
import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core import config
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core.console import console_attr
from googlecloudsdk.core.updater import update_manager


class Namespace(argparse.Namespace):
  """A custom subclass for parsed args.

  Attributes:
    _deepest_parser: ArgumentParser, The deepest parser for the command.
    _specified_args: {dest: arg-name}, A map of dest names for known args
      specified on the command line to arg names that have been scrubbed for
      metrics. This dict accumulate across all subparsers.
  """

  def __init__(self):
    self._specified_args = {}
    self._deepest_parser = None
    super(Namespace, self).__init__()

  def GetDisplayInfo(self):
    """Returns the parser display_info."""
    # pylint: disable=protected-access
    return self._deepest_parser._calliope_command.ai.display_info

  def GetSpecifiedArgNames(self):
    """Returns the scrubbed names for args specified on the comman line."""
    return sorted(self._specified_args.values())

  def IsSpecified(self, dest):
    """Returns True if args.dest was specified on the command line.

    Args:
      dest: str, The dest name for the arg to check.

    Raises:
      UnknownDestinationException: If there is no registered arg for dest.

    Returns:
      True if args.dest was specified on the command line.
    """
    if not hasattr(self, dest):
      raise parser_errors.UnknownDestinationException(
          'No registered arg for destination [{}].'.format(dest))
    return dest in self._specified_args


class ArgumentParser(argparse.ArgumentParser):
  """A custom subclass for arg parsing behavior.

  This overrides the default argparse parser.

  Attributes:
    _calliope_command: base._Command, The Calliope command or group for this
      parser.
    _is_group: bool, True if _calliope_command is a group.
    _remainder_action: action, The argument action for a -- ... remainder
      argument, added by AddRemainderArgument.
    _specified_args: {dest: arg-name}, A map of dest names for known args
      specified on the command line to arg names that have been scrubbed for
      metrics. This value is initialized and propagated to the deepest parser
      namespace in parse_known_args() from specified args collected in
      _get_values().
  """

  def __init__(self, *args, **kwargs):
    self._calliope_command = kwargs.pop('calliope_command')
    # Would rather isinstance(self._calliope_command, CommandGroup) here but
    # that would introduce a circular dependency on calliope.backend.
    self._is_group = hasattr(self._calliope_command, 'commands')
    self._remainder_action = None
    self._specified_args = {}
    super(ArgumentParser, self).__init__(*args, **kwargs)

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
      raise parser_errors.ArgumentException(
          'There can only be one pass through argument.')
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

  def GetSpecifiedArgNames(self):
    """Returns the scrubbed names for args specified on the comman line."""
    return sorted(self._specified_args.values())

  def parse_known_args(self, args=None, namespace=None):
    """Overrides argparse.ArgumentParser's .parse_known_args method."""
    if args is None:
      args = sys.argv[1:]
    if namespace is None:
      namespace = Namespace()
    try:
      if self._remainder_action:
        # Remove remainder_action so it is not parsed regularly.
        self._actions.remove(self._remainder_action)
        # Split on first -- if it exists
        namespace, args = self._remainder_action.ParseKnownArgs(args, namespace)
      self._specified_args = {}
      namespace, unknown_args = super(
          ArgumentParser, self).parse_known_args(args, namespace)
      # Update the namespace _specified_args with the specified arg dests and
      # names for this subparser.
      # pylint: disable=protected-access
      namespace._specified_args.update(self._specified_args)
    finally:
      # Replace action for help message and ArgumentErrors.
      if self._remainder_action:
        self._actions.append(self._remainder_action)

    # Pass back a reference to the deepest parser used in the parse as part of
    # the returned args.
    # pylint: disable=protected-access
    if not namespace._deepest_parser:
      namespace._deepest_parser = self
    return (namespace, unknown_args)

  def parse_args(self, args=None, namespace=None):
    """Overrides argparse.ArgumentParser's .parse_args method."""
    namespace, unknown_args = self.parse_known_args(args, namespace)
    if not unknown_args:
      return namespace

    # Content of these lines differs from argparser's parse_args().
    # pylint:disable=protected-access
    deepest_parser = namespace._deepest_parser or self
    deepest_parser._specified_args = namespace._specified_args
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

    # There is at least one parsing error. Add a message for each unknown
    # argument.  For each, try to come up with a suggestion based on text
    # distance.  If one is close enough, print a 'did you mean' message along
    # with that argument.
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
        # Strip the flag value if any from the suggestion.
        flag = arg.split('=')[0]
        suggestion = suggester.GetSuggestion(flag)
      else:
        suggestion = None
      if suggestion:
        suggestions[arg] = suggestion
        messages.append(arg + " (did you mean '{0}'?)".format(suggestion))
      else:
        messages.append(arg)

    # If there is a single arg, put it on the same line.  If there are multiple
    # add each on it's own line for better clarity.
    separator = u'\n  ' if len(messages) > 1 else u' '
    # This try-except models the real parse_args() pathway to self.error().
    try:
      raise parser_errors.UnrecognizedArgumentsError(
          u'unrecognized arguments:{0}{1}'.format(separator,
                                                  separator.join(messages)),
          parser=deepest_parser,
          total_unrecognized=len(unknown_args),
          total_suggestions=len(suggestions),
          suggestions=suggestions,
      )
    except argparse.ArgumentError as e:
      deepest_parser.error(e.message)

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
      raise parser_errors.WrongTrackError(
          message,
          extra_path_arg=value,
          suggestions=existing_alternatives)

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

      raise parser_errors.UnknownCommandError(
          message,
          argument=action.option_strings[0] if action.option_strings else None,
          total_unrecognized=1,
          total_suggestions=1 if suggestion else 0,
          suggestions=[suggestion] if suggestion else choices,
      )

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
    """Logs `Commands` and `Error` Google Analytics events for an error.

    Args:
      dotted_command_path: str, The dotted path to as much of the command as we
          can identify before an error. Example: gcloud.projects
      error: class, The class (not the instance) of the Exception for an error.
      error_extra_info: {str: json-serializable}, A json serializable dict of
        extra info that we want to log with the error. This enables us to write
        queries that can understand the keys and values in this dict.
    """
    specified_args = self.GetSpecifiedArgNames()
    metrics.Commands(
        dotted_command_path,
        config.CLOUD_SDK_VERSION,
        specified_args,
        error=error,
        error_extra_info=error_extra_info)
    metrics.Error(
        dotted_command_path,
        error,
        specified_args,
        error_extra_info=error_extra_info)

  def ReportErrorMetrics(self, error, message):
    """Reports Command and Error metrics in case of argparse errors.

    Args:
      error: Exception, The Exception object.
      message: str, The exception error message.
    """
    dotted_command_path = '.'.join(self._calliope_command.GetPath())

    # Check for parser_errors.ArgumentError with metrics payload.
    if isinstance(error, parser_errors.ArgumentError):
      if error.extra_path_arg:
        dotted_command_path = '.'.join([dotted_command_path,
                                        error.extra_path_arg])
      self._ReportErrorMetricsHelper(dotted_command_path,
                                     error.__class__,
                                     error.error_extra_info)
      return

    # No specific exception with metrics, try to detect error from message.
    if 'too few arguments' in message:
      self._ReportErrorMetricsHelper(dotted_command_path,
                                     parser_errors.TooFewArgumentsError)
      return

    re_result = re.search('argument (.+?) is required', message)
    if re_result:
      req_argument = re_result.group(1)
      self._ReportErrorMetricsHelper(
          dotted_command_path,
          parser_errors.RequiredArgumentError,
          {'required': req_argument})
      return

    re_result = re.search('one of the arguments (.+?) is required', message)
    if re_result:
      req_argument = re_result.group(1)
      self._ReportErrorMetricsHelper(
          dotted_command_path,
          parser_errors.RequiredArgumentGroupError,
          {'required': req_argument})
      return

    # Catchall for any error we didn't explicitly detect.
    self._ReportErrorMetricsHelper(dotted_command_path,
                                   parser_errors.OtherParsingError)

  def error(self, message):
    """Overrides argparse.ArgumentParser's .error(message) method.

    Specifically, it avoids reprinting the program name and the string "error:".

    Args:
      message: str, The error message to print.
    """
    _, error, _ = sys.exc_info()
    parser = self
    if isinstance(error, parser_errors.ArgumentError):
      # This associates the error with the correct parser.
      parser = error.parser or self
    parser.ReportErrorMetrics(error, message)

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
    """Intercepts argparse.ArgumentParser's ._get_values method.

    This intercept does not actually change any behavior.  We use this hook to
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
        self._specified_args[action.dest] = name
    return super(ArgumentParser, self)._get_values(action, arg_strings)

  def _get_option_tuples(self, option_string):
    """Intercepts argparse.ArgumentParser's ._get_option_tuples method.

    Cloud SDK no longer supports flag abbreviations, so it always returns []
    for the non-arg-completion case to indicate no abbreviated flag matches.

    Args:
      option_string: The option string to match.

    Returns:
      A list of matching flag tuples.
    """
    if '_ARGCOMPLETE' in os.environ:
      return super(ArgumentParser, self)._get_option_tuples(option_string)
    return []  # This effectively disables abbreviations.


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
    super(CloudSDKSubParsersAction, self).__init__(*args, **kwargs)

  def add_parser(self, name, **kwargs):
    # Pass the same flag collection down to any sub parsers that are created.
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
