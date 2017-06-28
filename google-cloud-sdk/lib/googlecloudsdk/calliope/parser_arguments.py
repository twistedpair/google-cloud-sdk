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

"""Calliope argparse argument intercepts and extensions.

Refer to the calliope.parser_extensions module for a detailed overview.
"""

import argparse

from googlecloudsdk.calliope import display_info
from googlecloudsdk.calliope import parser_completer
from googlecloudsdk.calliope import parser_errors
from googlecloudsdk.command_lib.util import deprecated_completers
from googlecloudsdk.core.cache import completion_cache
from googlecloudsdk.core.resource import resource_property


_MUTEX_GROUP_REQUIRED_DESCRIPTION = 'Exactly one of these must be specified:'
_MUTEX_GROUP_OPTIONAL_DESCRIPTION = 'At most one of these may be specified:'


class ArgumentGroupAttr(object):
  """Argument group attributes."""

  def __init__(self, description=None, is_mutex=False, is_required=False):
    self.description = description
    self.is_mutex = is_mutex
    self.is_required = is_required


class ArgumentInterceptor(object):
  """ArgumentInterceptor intercepts calls to argparse parsers.

  The argparse module provides no public way to access the arguments that were
  specified on the command line. Argparse itself does the validation when it is
  run from the command line.

  Attributes:
    allow_positional: bool, Whether or not to allow positional arguments.
    defaults: {str:obj}, A dict of {dest: default} for all the arguments added.
    dests: [str], A list of the dests for all arguments.
    flag_args: [argparse.Action], A list of the flag arguments.
    parser: argparse.Parser, The parser whose methods are being intercepted.
    positional_args: [argparse.Action], A list of the positional arguments.
    required: [str], A list of the dests for all required arguments.

  Raises:
    ArgumentException: if a positional argument is made when allow_positional
        is false.
  """

  class ParserData(object):
    """Parser data for the entire command.

    Attributes:
      allow_positional: bool, Allow positional arguments if True.
      ancestor_flag_args: [argparse.Action], The flags for all ancestor groups
        in the cli tree.
      argument_groups: {dest: group-id}, Maps dests to argument group ids.
      cli_generator: cli.CLILoader, The builder used to generate this CLI.
      command_name: str, The dotted command name path.
      defaults: {dest: default}, For all registered arguments.
      dests: [str], A list of the dests for all arguments.
      display_info: [display_info.DisplayInfo], The command display info object.
      flag_args: [ArgumentInterceptor], The flag arguments.
      group_attr: {dest: ArgumentGroupAttr}, Maps dests to ArgumentGroupAttr.
      groups: [ArgumentInterceptor], The arg groups.
      mutex_groups: {dest: mutex_group_id}, Maps dests to mutex group ids.
      positional_args: [ArgumentInterceptor], The positional args.
      positional_completers: {Completer}, The set of completers for positionals.
      required: [str], The dests for all required arguments.
      required_mutex_groups: set(id), Set of mutex group ids that are required.
    """

    def __init__(self, command_name, is_root, cli_generator, allow_positional):
      self.command_name = command_name
      self.is_root = is_root
      self.cli_generator = cli_generator
      self.allow_positional = allow_positional
      self.is_root = is_root

      self.ancestor_flag_args = []
      self.argument_groups = {}
      self.defaults = {}
      self.dests = []
      self.display_info = display_info.DisplayInfo()
      self.flag_args = []
      self.group_attr = {}
      self.groups = {}
      self.mutex_groups = {}
      self.positional_args = []
      self.positional_completers = set()
      self.required = []
      self.required_mutex_groups = set()

  def __init__(self, parser, is_root=False, cli_generator=None,
               allow_positional=True, data=None, mutex_group_id=None,
               argument_group_id=None):
    self.parser = parser
    # If this is an argument group within a command, use the data from the
    # parser for the entire command.  If it is the command itself, create a new
    # data object and extract the command name from the parser.
    if data:
      self.data = data
    else:
      self.data = ArgumentInterceptor.ParserData(
          # pylint: disable=protected-access
          command_name=self.parser._calliope_command.GetPath(),
          is_root=is_root,
          cli_generator=cli_generator,
          allow_positional=allow_positional)
    self.mutex_group_id = mutex_group_id
    self.argument_group_id = argument_group_id

  @property
  def allow_positional(self):
    return self.data.allow_positional

  @property
  def cli_generator(self):
    return self.data.cli_generator

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
  def is_root(self):
    return self.data.is_root

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
  def positional_completers(self):
    return self.data.positional_completers

  @property
  def ancestor_flag_args(self):
    return self.data.ancestor_flag_args

  # pylint: disable=g-bad-name
  def add_argument(self, *args, **kwargs):
    """add_argument intercepts calls to the parser to track arguments."""
    # TODO(b/36050238): do not allow short-options without long-options.

    # we will choose the first option as the name
    name = args[0]
    dest = kwargs.get('dest')
    if not dest:
      # this is exactly what happens in argparse
      dest = name.lstrip(self.parser.prefix_chars).replace('-', '_')

    default = kwargs.get('default')
    required = kwargs.get('required', False)

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
    # The unbound completer object or raw argcomplete completer function).
    completer = kwargs.pop('completer', None)
    # The resource name for the purposes of doing remote completion.
    completion_resource = kwargs.pop('completion_resource', None)
    # An explicit command to run for remote completion instead of the default
    # for this resource type.
    list_command_path = kwargs.pop('list_command_path', None)
    # Callback function that receives the currently entered args at the time of
    # remote completion processing, and returns the command to run.
    list_command_callback_fn = kwargs.pop('list_command_callback_fn', None)
    # hidden=True => help=argparse.SUPPRESS, but retains help in the source.
    if kwargs.pop('hidden', False):
      kwargs['help'] = argparse.SUPPRESS

    positional = not name.startswith('-')
    if positional:
      if not self.allow_positional:
        # TODO(b/36054662): More informative error message here about which
        # group the problem is in.
        raise parser_errors.ArgumentException(
            'Illegal positional argument [{0}] for command [{1}]'.format(
                name, self.data.command_name))
      if '-' in name:
        raise parser_errors.ArgumentException(
            "Positional arguments cannot contain a '-'. Illegal argument [{0}] "
            'for command [{1}]'.format(name, self.data.command_name))
      if category:
        raise parser_errors.ArgumentException(
            'Positional argument [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      if suggestion_aliases:
        raise parser_errors.ArgumentException(
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
    self._AttachCompleter(
        added_argument,
        name,
        completer,
        positional,
        deprecated_collection=completion_resource,
        deprecated_list_command=list_command_path,
        deprecated_list_command_callback=list_command_callback_fn)
    if positional:
      if category:
        raise parser_errors.ArgumentException(
            'Positional argument [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      self.positional_args.append(added_argument)
    else:
      if category and required:
        raise parser_errors.ArgumentException(
            'Required flag [{0}] cannot have a category in '
            'command [{1}]'.format(name, self.data.command_name))
      if category == 'REQUIRED':
        raise parser_errors.ArgumentException(
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

  def parse_known_args(self, args=None, namespace=None):
    """Hooks ArgumentInterceptor into the argcomplete monkeypatch."""
    return self.parser.parse_known_args(args=args, namespace=namespace)

  def add_argument_group(self, *args, **kwargs):
    new_parser = self.parser.add_argument_group(*args, **kwargs)
    return ArgumentInterceptor(parser=new_parser,
                               data=self.data,
                               argument_group_id=id(new_parser))

  def add_mutually_exclusive_group(self, **kwargs):
    new_parser = self.parser.add_mutually_exclusive_group(**kwargs)
    return ArgumentInterceptor(parser=new_parser,
                               data=self.data,
                               mutex_group_id=id(new_parser))

  def AddDynamicPositional(self, name, action, **kwargs):
    """Add a positional argument that adds new args on the fly when called.

    Args:
      name: The name/dest of the positional argument.
      action: The argparse Action to use. It must be a subclass of
        parser_extensions.DynamicPositionalAction.
      **kwargs: Passed verbatim to the argparse.ArgumentParser.add_subparsers
        method.

    Returns:
      argparse.Action, The added action.
    """
    kwargs['dest'] = name
    if 'metavar' not in kwargs:
      kwargs['metavar'] = name.upper()
    kwargs['parent_ai'] = self

    action = self.parser.add_subparsers(action=action, **kwargs)
    action.completer = action.Completions
    self.positional_args.append(action)
    return action

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

    # Add hidden --no-foo for the --foo Boolean flag. The inverted flag will
    # have the same dest and mutually exclusive group as the original flag.
    # Explicit default=None yields the 'Use to disable.' text.
    default = original_kwargs.get('default', False)
    if prop:
      inverted_synopsis = bool(prop.default)
    elif default not in (True, None):
      inverted_synopsis = False
    elif default:
      inverted_synopsis = bool(default)
    else:
      inverted_synopsis = False

    kwargs = dict(original_kwargs)
    if action == 'store_true':
      action = 'store_false'
    elif action == 'store_false':
      action = 'store_true'
    kwargs['action'] = action
    if not kwargs.get('dest'):
      kwargs['dest'] = dest
    kwargs['help'] = argparse.SUPPRESS

    inverted_argument = self.parser.add_argument(
        name.replace('--', '--no-', 1), **kwargs)
    if inverted_synopsis:
      # flag.inverted_synopsis means display the inverted flag in the SYNOPSIS.
      setattr(added_argument, 'inverted_synopsis', True)
    return inverted_argument

  def _ShouldInvertBooleanFlag(self, name, action):
    """Checks if flag name with action is a Boolean flag to invert.

    Args:
      name: str, The flag name.
      action: argparse.Action, The argparse action.

    Returns:
      (False, None) if flag is not a Boolean flag or should not be inverted,
      (True, property) if flag is a Boolean flag associated with a property,
      (False, property) if flag is a non-Boolean flag associated with a property
      otherwise (True, None) if flag is a pure Boolean flag.
    """
    if not name.startswith('--'):
      return False, None
    if name.startswith('--no-'):
      # --no-no-* is a no no.
      return False, None
    if '--no-' + name[2:] in self.parser._option_string_actions:  # pylint: disable=protected-access
      # Don't override explicit --no-* inverted flag.
      return False, None
    if action in ('store_true', 'store_false'):
      return True, None
    prop, kind, _ = getattr(action, 'store_property', (None, None, None))
    if prop:
      return kind == 'bool', prop
    # Not a Boolean flag.
    return False, None

  # TODO(b/38374705): Drop the deprecated code.
  def _AttachCompleter(self, arg, name, completer, positional,
                       deprecated_collection=None,
                       deprecated_list_command=None,
                       deprecated_list_command_callback=None):
    """Attaches a completer to arg if one is specified.

    Args:
      arg: The argument to attach the completer to.
      name: The arg name for messaging.
      completer: The completer Completer class or argcomplete function object.
      positional: True if argument is a positional.
      deprecated_collection: The collection name for the resource to complete.
      deprecated_list_command: The command whose Run() method returns the
        current resource list.
      deprecated_list_command_callback: A callback function that returns the
        list command to run.
    """
    if not completer:
      if not deprecated_collection:
        if deprecated_list_command or deprecated_list_command_callback:
          raise parser_errors.ArgumentException(
              'Command [{}] argument [{}] does not have completion_resource '
              'set but has one or more of the deprecated list_command_path '
              'and list_command_callback_fn attributes.'.format(
                  ' '.join(self.data.command_name), name))
        return

      class DeprecatedCompleter(
          deprecated_completers.DeprecatedListCommandCompleter):

        def __init__(self, **kwargs):
          super(DeprecatedCompleter, self).__init__(
              collection=deprecated_collection,
              list_command=deprecated_list_command,
              list_command_callback=deprecated_list_command_callback,
              **kwargs)

      DeprecatedCompleter.__name__ = (
          resource_property.ConvertToCamelCase(
              deprecated_collection.capitalize().replace('.', '_')) +
          'DeprecatedCompleter')

      completer = DeprecatedCompleter
    elif (deprecated_collection or
          deprecated_list_command or
          deprecated_list_command_callback):
      raise parser_errors.ArgumentException(
          'Command [{}] argument [{}] has a completer set with one or more '
          'of the deprecated completion_resource, list_command_path, and '
          'list_command_callback_fn attributes.'.format(
              ' '.join(self.data.command_name), name))
    if isinstance(completer, type):
      # A completer class that will be instantiated at completion time.
      if positional and issubclass(completer, completion_cache.Completer):
        # The list of positional resource completers is used to determine
        # parameters that must be present in the completions.
        self.data.positional_completers.add(completer)
      arg.completer = parser_completer.ArgumentCompleter(
          completer, argument=arg)
    else:
      arg.completer = completer
