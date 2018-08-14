# -*- coding: utf-8 -*- #
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

"""The gcloud interactive shell completion."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import time

from googlecloudsdk.calliope import parser_completer
from googlecloudsdk.command_lib.interactive import parser
from googlecloudsdk.command_lib.meta import generate_cli_trees
from googlecloudsdk.core import module_util
from prompt_toolkit import completion
import six


def _NameSpaceDict(args):
  """Returns a namespace dict given parsed CLI tree args."""
  namespace = {}
  name = None
  for arg in args:
    if arg.token_type == parser.ArgTokenType.POSITIONAL:
      name = arg.tree.get(parser.LOOKUP_NAME)
      value = arg.value
    elif arg.token_type == parser.ArgTokenType.FLAG:
      name = arg.tree.get(parser.LOOKUP_NAME)
      if name:
        if name.startswith('--'):
          name = name[2:]
        name = name.replace('-', '_')
      continue
    elif not name:
      continue
    elif arg.token_type == parser.ArgTokenType.FLAG_ARG:
      value = arg.value
    else:
      continue
    namespace[name] = value
  return namespace


class CompleterCache(object):
  """A local completer cache item to minimize intra-command latency.

  Attributes:
    _TIMEOUT: Newly updated choices stale after this many seconds.
    completer_class: The completer class.
    coshell: The coshell object.
    choices: The cached choices.
    stale: choices stale after this time.
  """

  _TIMEOUT = 60

  def __init__(self, completer_class):
    self.completer_class = completer_class
    self.choices = None
    self.stale = 0
    self.timeout = CompleterCache._TIMEOUT


class InteractiveCliCompleter(completion.Completer):
  """A prompt_toolkit interactive CLI completer."""

  def __init__(self, interactive_parser, args=None, hidden=False,
               manpage_generator=True, cosh=None):
    self.parsed_args = args
    self.hidden = hidden
    self.coshell = cosh
    self.completer_cache = {}
    self.manpage_generator = manpage_generator
    self.parser = interactive_parser
    self.empty = False
    self.last = ''
    generate_cli_trees.CliTreeGenerator.MemoizeFailures(True)

  def IsSuppressed(self, info):
    if self.hidden:
      return info.get(parser.LOOKUP_NAME, '').startswith('--no-')
    return info.get(parser.LOOKUP_IS_HIDDEN)

  def get_completions(self, doc, event):
    """Yields the completions for doc.

    Args:
      doc: A Document instance containing the interactive command line to
           complete.
      event: The CompleteEvent that triggered this completion.

    Yields:
      Completion instances for doc.
    """
    args = self.parser.ParseCommand(doc.text_before_cursor)
    if not args:
      return
    self.last = doc.text_before_cursor[-1] if doc.text_before_cursor else ''
    self.empty = self.last.isspace()
    self.event = event

    for completer in (
        self.CommandCompleter,
        self.FlagCompleter,
        self.PositionalCompleter,
        self.InteractiveCompleter,
    ):
      choices, offset = completer(args)
      if choices is not None:
        if offset is None:
          # The choices are already completion.Completion objects.
          for choice in choices:
            yield choice
        else:
          for choice in sorted(choices):
            yield completion.Completion(choice, start_position=offset)
        return

  def CommandCompleter(self, args):
    """Returns the command/group completion choices for args or None.

    Args:
      args: The CLI tree parsed command args.

    Returns:
      (choices, offset):
        choices - The list of completion strings or None.
        offset - The completion prefix offset.
    """
    arg = args[-1]

    if arg.value.startswith('-'):
      return None, 0

    if arg.token_type == parser.ArgTokenType.GROUP:
      if not self.empty:
        return [], 0
      node = arg.tree
      prefix = ''

    elif arg.token_type == parser.ArgTokenType.UNKNOWN:
      prefix = arg.value
      if len(args) == 1:
        node = self.parser.root
      elif (self.manpage_generator and not prefix and
            len(args) == 2 and args[0].value):
        node = generate_cli_trees.LoadOrGenerate(args[0].value)
        if not node:
          return None, 0
        self.parser.root[parser.LOOKUP_COMMANDS][args[0].value] = node
      elif args[-2].token_type == parser.ArgTokenType.GROUP:
        node = args[-2].tree
      else:
        return None, 0

    else:
      return None, 0

    return [k for k, v in six.iteritems(node[parser.LOOKUP_COMMANDS])
            if k.startswith(prefix) and not self.IsSuppressed(v)], -len(prefix)

  def ArgCompleter(self, args, arg, value):
    """Returns the flag or positional completion choices for arg or [].

    Args:
      args: The CLI tree parsed command args.
      arg: The flag or positional argument.
      value: The (partial) arg value.

    Returns:
      (choices, offset):
        choices - The list of completion strings or None.
        offset - The completion prefix offset.
    """
    choices = arg.get(parser.LOOKUP_CHOICES)
    if choices:
      # static choices
      return [v for v in choices if v.startswith(value)], -len(value)

    if not value and not self.event.completion_requested:
      return [], 0

    module_path = arg.get(parser.LOOKUP_COMPLETER)
    if not module_path:
      return [], 0

    # arg with a completer
    cache = self.completer_cache.get(module_path)
    if not cache:
      cache = CompleterCache(module_util.ImportModule(module_path))
      self.completer_cache[module_path] = cache
    prefix = value
    if not isinstance(cache.completer_class, type):
      cache.choices = cache.completer_class(prefix=prefix)
    elif cache.stale < time.time():
      old_dict = self.parsed_args.__dict__
      self.parsed_args.__dict__ = {}
      self.parsed_args.__dict__.update(old_dict)
      self.parsed_args.__dict__.update(_NameSpaceDict(args))
      completer = parser_completer.ArgumentCompleter(
          cache.completer_class,
          parsed_args=self.parsed_args)
      cache.choices = completer(prefix='')
      self.parsed_args.__dict__ = old_dict
      cache.stale = time.time() + cache.timeout
    if arg.get(parser.LOOKUP_TYPE) == 'list':
      parts = value.split(',')
      prefix = parts[-1]
    if not cache.choices:
      return [], 0
    return [v for v in cache.choices if v.startswith(prefix)], -len(prefix)

  def FlagCompleter(self, args):
    """Returns the flag completion choices for args or None.

    Args:
      args: The CLI tree parsed command args.

    Returns:
      (choices, offset):
        choices - The list of completion strings or None.
        offset - The completion prefix offset.
    """
    arg = args[-1]

    if arg.token_type == parser.ArgTokenType.FLAG_ARG:
      flag = args[-2].tree
      return self.ArgCompleter(args, flag, arg.value)

    elif arg.token_type == parser.ArgTokenType.FLAG:
      flag = arg.tree
      if flag.get(parser.LOOKUP_TYPE) != 'bool':
        completions, offset = self.ArgCompleter(args, flag, '')
        if not self.empty and self.last != '=':
          completions = [' ' + c for c in completions]
        return completions, offset

    elif arg.value.startswith('-'):
      return [k for k, v in six.iteritems(arg.tree[parser.LOOKUP_FLAGS])
              if k.startswith(arg.value) and
              not self.IsSuppressed(v)], -len(arg.value)

    return None, 0

  def PositionalCompleter(self, args):
    """Returns the positional completion choices for args or None.

    Args:
      args: The CLI tree parsed command args.

    Returns:
      (choices, offset):
        choices - The list of completion strings or None.
        offset - The completion prefix offset.
    """
    arg = args[-1]

    if arg.token_type == parser.ArgTokenType.POSITIONAL:
      return self.ArgCompleter(args, arg.tree, arg.value)

    return None, 0

  def InteractiveCompleter(self, args):
    """Returns the interactive completion choices for args or None.

    Args:
      args: The CLI tree parsed command args.

    Returns:
      (choices, offset):
        choices - The list of completion strings or None.
        offset - The completion prefix offset.
    """
    if not self.event.completion_requested:
      return None, 0
    command = [arg.value for arg in args]
    # If the input command line ended with a space then the split command line
    # must end with an empty string if it doesn't already. This instructs the
    # completer to complete the next arg.
    if self.empty and command[-1]:
      command.append('')
    completions = self.coshell.GetCompletions(command)
    if not completions:
      return None, None

    # Make path completions play nice with dropdowns. Add trailing '/' for dirs
    # in the dropdown but not the completion. User types '/' to select a dir
    # and ' ' to select a path.
    #
    # NOTE: '/' instead of os.path.sep since the coshell is bash even on Windows
    last = command[-1]
    offset = -len(last)
    prefix = last if last.endswith('/') else os.path.dirname(last)
    chop = len(prefix) if prefix else 0

    def _Mark(c):
      """Returns completion c with a trailing '/' if it is a dir."""
      if not c.endswith('/') and os.path.isdir(c):
        return c + '/'
      return c

    def _Display(c):
      """Returns the annotated dropdown display spelling of completion c."""
      c = _Mark(c)[chop:]
      if prefix and c.startswith('/'):
        # Some shell completers insert an '/' that spoils the dropdown.
        c = c[1:]
      return c

    if not os.path.isdir(prefix) and not self.coshell.GetPwd():
      # The prefix is not a dir or we have a bogus coshell pwd. Treat the
      # completions as normal strings.
      return completions, offset
    if len(completions) == 1:
      # No dropdown for singletons so just return the marked completion.
      choice = _Mark(completions[0])
      return [completion.Completion(choice, start_position=offset)], None
    # Return completion objects with annotated choices for the dropdown.
    return [completion.Completion(c, display=_Display(c), start_position=offset)
            for c in completions], None
