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
"""gcloud shell completion."""

from __future__ import unicode_literals

from googlecloudsdk.calliope import parser_completer
from googlecloudsdk.command_lib.shell import lexer
from googlecloudsdk.command_lib.shell import parser
from googlecloudsdk.core import module_util
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion


class ShellCliCompleter(Completer):
  """A prompt_toolkit shell CLI completer."""

  def __init__(self, root, args=None, hidden=False):
    self.root = root
    self.args = args
    self.hidden = hidden
    self.completer_classes = {}

  def IsSuppressed(self, info):
    if self.hidden:
      return info.get(parser.LOOKUP_NAME, '').startswith('--no-')
    return info.get(parser.LOOKUP_IS_HIDDEN)

  def get_completions(self, doc, complete_event):
    """Yields the completions for doc.

    Args:
      doc: A Document instance containing the shell command line to complete.
      complete_event: The CompleteEvent that triggered this completion.

    Yields:
      Completion instances for doc.
    """
    tokens = lexer.GetShellTokens(doc.text_before_cursor)
    if not tokens:
      return
    node = self.root[parser.LOOKUP_COMMANDS]
    info = None
    last = ''
    path = []
    i = 0

    # Autocomplete commands and groups after spaces.
    if doc.text_before_cursor and doc.text_before_cursor[-1].isspace():
      for completion in sorted(self.CompleteCommandGroups(tokens)):
        yield Completion(completion)
      return

    # Complete after the last terminator
    for index, token in enumerate(tokens):
      if token.lex == lexer.ShellTokenType.TERMINATOR:
        i = index + 1

    # Traverse the cli tree.
    while i < len(tokens):
      token = tokens[i]
      if token.lex == lexer.ShellTokenType.FLAG:
        if i == len(tokens) - 1:
          last = token.value
      elif token.value in node:
        info = node[token.value]
        path.append(info)
        node = info.get(parser.LOOKUP_COMMANDS, {})
      else:
        break
      i += 1

    last = tokens[-1].value

    offset = -len(last)

    # Check for flags.
    if last.startswith('-') and info:
      # Collect all flags of current command and parents into node.
      node = info.get(parser.LOOKUP_FLAGS, {})

      value = last.find('=')
      if value > 0:
        if doc.text_before_cursor[-1].isspace():
          return
        name = last[:value]
      else:
        name = last
      if name in node:
        info = node[name]
        if info.get(parser.LOOKUP_TYPE) != 'bool':
          choices = info.get(parser.LOOKUP_CHOICES)
          if choices:
            # A flag with static choices.
            prefix = last
            if value < 0:
              prefix += '='
              offset -= 1
              completer_prefix = ''
            else:
              completer_prefix = last[value + 1:]
            for choice in sorted(choices):
              yield Completion(name + '=' + choice, offset)
          else:
            module_path = info.get(parser.LOOKUP_COMPLETER)
            if module_path:
              # A flag with a completer.
              completer_class = self.completer_classes.get(module_path)
              if not completer_class:
                completer_class = module_util.ImportModule(module_path)
                self.completer_classes[module_path] = completer_class
              completer = parser_completer.ArgumentCompleter(
                  completer_class,
                  parsed_args=self.args)
              prefix = last
              if value < 0:
                prefix += '='
                offset -= 1
                completer_prefix = ''
              else:
                completer_prefix = last[value + 1:]
              for completion in completer(prefix=completer_prefix):
                yield Completion(name + '=' + completion.rstrip(), offset)
        return

    # Check for subcommands.
    for choice, info in sorted(node.iteritems()):
      if not self.IsSuppressed(info) and choice.startswith(last):
        yield Completion(choice, offset)

  def CompleteCommandGroups(self, text):
    """Return possible commands and groups for completions."""
    args = parser.ParseArgs(self.root, text)

    if not args:
      return []

    if args[-1].token_type != parser.ArgTokenType.GROUP:
      return []

    return [k for k, v in args[-1].tree[parser.LOOKUP_COMMANDS].iteritems()
            if not self.IsSuppressed(v)]
