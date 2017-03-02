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

from googlecloudsdk.command_lib.shell import gcloud_parser
from googlecloudsdk.command_lib.shell import shell_lexer as lexer
from googlecloudsdk.command_lib.shell.gcloud_tree import gcloud_tree
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion


class ShellCliCompleter(Completer):
  """A prompt_toolkit shell CLI completer."""

  def __init__(self):
    self.root = {'gcloud': gcloud_tree}
    self.index = 0

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
    if tokens[0].value != 'gcloud':
      gcloud_token = lexer.ShellToken(
          'gcloud', lex=lexer.ShellTokenType.ARG, start=0, end=0)
      tokens = ([gcloud_token] + tokens)
    node = self.root
    info = None
    last = ''
    path = []
    i = 0

    # Autocomplete commands and groups after spaces.
    if doc.text_before_cursor and doc.text_before_cursor[-1].isspace():
      for completion in CompleteCommandGroups(tokens):
        yield Completion(completion)
      return

    # If there is a terminator, do not complete.
    for token in tokens:
      if token.lex == lexer.ShellTokenType.TERMINATOR:
        return

    # Traverse the cli tree.
    while i < len(tokens):
      token = tokens[i]
      if token.lex == lexer.ShellTokenType.FLAG:
        if i == len(tokens) - 1:
          last = token.value
      elif token.value in node:
        info = node[token.value]
        path.append(info)
        node = info.get('commands', {})
      else:
        break
      i += 1

    last = tokens[-1].value

    offset = -len(last)

    # Check for flags.
    if last.startswith('-') and info:
      # Collect all flags of current command and parents into node.
      node = info.get('flags', {}).copy()
      for info in path:
        node.update(info.get('flags', {}))

      value = last.find('=')
      if value > 0:
        if doc.text_before_cursor[-1].isspace():
          return
        name = last[:value]
      else:
        name = last
      if name in node:
        info = node[name]
        if info.get('type', None) != 'bool':
          choices = info.get('choices', None)
          if choices:
            # A flag with static choices.
            prefix = last
            if value < 0:
              prefix += '='
              offset -= 1
            for choice in choices:
              yield Completion(name + '=' + choice, offset)
        return

    # Check for subcommands.
    for choice in sorted(node):
      if choice.startswith(last):
        yield Completion(choice, offset)


def CompleteCommandGroups(ts):
  """Return possible commands and groups for completions."""
  args = gcloud_parser.ParseArgs(ts)

  if not args:
    return []

  if args[-1].token_type != gcloud_parser.ArgTokenType.GROUP:
    return []

  return args[-1].tree['commands'].keys()
