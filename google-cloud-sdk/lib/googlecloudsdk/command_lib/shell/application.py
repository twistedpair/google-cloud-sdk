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

"""The gcloud shell application.

Usage:
  application.main()
"""

from __future__ import unicode_literals

import sys

from googlecloudsdk.command_lib.shell import bindings
from googlecloudsdk.command_lib.shell import completer as shell_completer
from googlecloudsdk.command_lib.shell import coshell
from googlecloudsdk.command_lib.shell import layout
from googlecloudsdk.command_lib.shell import style as shell_style
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from prompt_toolkit import application
from prompt_toolkit import buffer as pt_buffer
from prompt_toolkit import document
from prompt_toolkit import filters
from prompt_toolkit import history as pt_history
from prompt_toolkit import interface
from prompt_toolkit import shortcuts
from prompt_toolkit.token import Token


class Application(object):
  """The CLI application.

  Attributes:
    cli: The prompt cli object.
    coshell: The shell coprocess object.
    key_bindings: The key_bindings object holding the key binding list and
      toggle states.
  """

  BOTTOM_TOOLBAR_SEPARATOR = ' | '
  MENU_RESERVE_SPACE = 5

  def __init__(self, prompt='$ ', cosh=None):
    self.prompt = prompt
    self.coshell = cosh
    self.key_bindings = bindings.KeyBindings(
        edit_mode=self.coshell.edit_mode == 'emacs')

    # Create the CLI.
    self.cli = interface.CommandLineInterface(
        application=self._CreatePromptApplication(),
        eventloop=shortcuts.create_eventloop(),
        output=shortcuts.create_output())
    self.key_bindings.Initialize(self.cli)

  def _CreatePromptApplication(self):
    """Creates a shell prompt Application."""

    # Make sure that complete_while_typing is disabled when
    # enable_history_search is enabled. (First convert to SimpleFilter, to
    # avoid doing bitwise operations on bool objects.)
    complete_while_typing = shortcuts.to_simple_filter(True)
    enable_history_search = shortcuts.to_simple_filter(False)
    multiline = shortcuts.to_simple_filter(False)

    complete_while_typing &= ~enable_history_search

    return application.Application(
        layout=layout.CreatePromptLayout(
            message=self.prompt,
            lexer=None,
            is_password=False,
            reserve_space_for_menu=self.MENU_RESERVE_SPACE,
            multiline=filters.Condition(lambda cli: multiline()),
            get_prompt_tokens=None,
            get_continuation_tokens=None,
            get_bottom_toolbar_tokens=self._GetBottomToolbarTokens,
            display_completions_in_columns=False,
            extra_input_processors=None,
            wrap_lines=True,
            show_help=filters.Condition(
                lambda _: self.key_bindings.help_key.toggle)),
        buffer=pt_buffer.Buffer(
            enable_history_search=enable_history_search,
            complete_while_typing=complete_while_typing,
            is_multiline=multiline,
            history=pt_history.InMemoryHistory(),
            validator=None,
            completer=shell_completer.ShellCliCompleter(),
            auto_suggest=None,
            accept_action=pt_buffer.AcceptAction.RETURN_DOCUMENT,
            initial_document=document.Document(''),),
        style=shell_style.GetDocumentStyle(),
        clipboard=None,
        key_bindings_registry=self.key_bindings.MakeRegistry(),
        get_title=None,
        mouse_support=False,
        erase_when_done=False,
        on_abort=application.AbortAction.RAISE_EXCEPTION,
        on_exit=application.AbortAction.RAISE_EXCEPTION)

  def _GetBottomToolbarTokens(self, _):
    """Returns the bottom toolbar tokens based on the key binding state."""
    named_configs.ActivePropertiesFile().Invalidate()
    project = properties.VALUES.core.project.Get() or '<NO PROJECT SET>'
    account = properties.VALUES.core.account.Get() or '<NO ACCOUNT SET>'
    separator = (Token.Toolbar.Separator, self.BOTTOM_TOOLBAR_SEPARATOR)

    tokens = []
    tokens.append((Token.Toolbar.Account, account))
    tokens.append(separator)
    tokens.append((Token.Toolbar.Project, project))
    for binding in self.key_bindings.bindings:
      tokens.append(separator)
      tokens.append((Token.Toolbar.Help, binding.GetLabel()))
    return tokens

  def Prompt(self):
    """Prompts and returns one command line."""
    result = self.cli.run(reset_current_buffer=False)
    if isinstance(result, document.Document):  # Backwards-compatibility.
      return result.text
    return result

  def Run(self, text):
    """Runs the command(s) in text and waits for them to complete."""
    return self.coshell.Run(text)

  def Loop(self):
    """Loops Prompt-Run until ^D exit, or quit."""
    while True:
      try:
        text = self.Prompt()
        if text is None:
          break
        self.Run(text)
      except EOFError:
        # ctrl-d
        break
      except KeyboardInterrupt:
        # ignore ctrl-c
        pass
      except coshell.CoshellExitException:
        break


def main():
  """The shell application loop."""
  cosh = coshell.Coshell()
  try:
    Application(prompt='gcloud> ', cosh=cosh).Loop()
  finally:
    status = cosh.Close()
  sys.exit(status)
