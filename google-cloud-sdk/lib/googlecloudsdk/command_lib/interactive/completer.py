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

from __future__ import unicode_literals

import time

from googlecloudsdk.calliope import parser_completer
from googlecloudsdk.command_lib.interactive import parser
from googlecloudsdk.command_lib.meta import generate_cli_trees
from googlecloudsdk.core import module_util
from prompt_toolkit import completion
from prompt_toolkit import document
from prompt_toolkit.contrib import completers


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
    self.path_completer = completers.PathCompleter(expanduser=True)
    self.empty = False
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
    self.empty = doc.text_before_cursor and doc.text_before_cursor[-1].isspace()
    self.event = event

    for completer in (
        self.CommandCompleter,
        self.FlagCompleter,
        self.PositionalCompleter,
        self.InteractiveCompleter,
    ):
      choices, offset = completer(args)
      if choices is not None:
        for choice in sorted(choices):
          display = choice
          if choice.endswith('/'):
            choice = choice[:-1]
          yield completion.Completion(
              choice, display=display, start_position=offset)
        return

    if event.completion_requested:
      # default to path completions
      choices = self.path_completer.get_completions(
          document.Document('' if self.empty else args[-1].value), event)
      if choices:
        for choice in choices:
          yield choice
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

    return [k for k, v in node[parser.LOOKUP_COMMANDS].iteritems()
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
        return self.ArgCompleter(args, flag, '')

    elif arg.value.startswith('-'):
      return [k for k, v in arg.tree[parser.LOOKUP_FLAGS].iteritems()
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
    return self.coshell.GetCompletions(command) or None, -len(command[-1])
