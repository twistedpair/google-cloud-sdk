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

import os
import sys

from googlecloudsdk.calliope import cli_tree
from googlecloudsdk.command_lib.shell import bindings
from googlecloudsdk.command_lib.shell import completer
from googlecloudsdk.command_lib.shell import coshell
from googlecloudsdk.command_lib.shell import layout
from googlecloudsdk.command_lib.shell import parser
from googlecloudsdk.command_lib.shell import style as shell_style
from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from prompt_toolkit import application as pt_application
from prompt_toolkit import buffer as pt_buffer
from prompt_toolkit import document
from prompt_toolkit import filters
from prompt_toolkit import history as pt_history
from prompt_toolkit import interface
from prompt_toolkit import shortcuts
from prompt_toolkit.token import Token


class CLI(interface.CommandLineInterface):
  """Extends the prompt CLI object to include our state.

  Attributes:
    root: The root of the static CLI tree that contains all commands, flags,
      positionals and help doc snippets.
  """

  def __init__(self, root=None, application=None, eventloop=None, output=None,
               restrict=None):
    super(CLI, self).__init__(
        application=application,
        eventloop=eventloop,
        output=output)
    self.root = root
    self.restrict = restrict


class Application(object):
  """The CLI application.

  Attributes:
    cli: The prompt cli object.
    coshell: The shell coprocess object.
    key_bindings: The key_bindings object holding the key binding list and
      toggle states.
    prompt: The command line prompt.
    hidden: Complete hidden commands and flags if True.
    restrict: Restrict commands to subcommands of this top level command.
  """

  BOTTOM_TOOLBAR_SEPARATOR = '  '
  MENU_RESERVE_SPACE = 5

  def __init__(self, cli=None, args=None, cosh=None, prompt='$ ', hidden=False,
               restrict=None):
    self.args = args
    self.coshell = cosh
    self.prompt = prompt
    self.hidden = hidden
    self.key_bindings = bindings.KeyBindings(
        edit_mode=self.coshell.edit_mode == 'emacs')

    # Load the default CLI tree.
    if restrict:
      # Restrict the CLI tree to subcommands of this top level command.
      self.root = cli_tree.Load(cli=cli)
    else:
      self.root = cli_tree.LoadAll(cli=cli)
      # Add the exit command completer node to the CLI tree.
      self.root[parser.LOOKUP_COMMANDS]['exit'] = cli_tree.Node(
          command='exit',
          description='Exit the interactive shell.',
          positionals=[
              {
                  'default': '0',
                  'description': 'The exit status.',
                  'name': 'status',
                  'nargs': '?',
                  'required': False,
                  'value': 'STATUS',
              },
          ],
      )

    # Create the CLI.
    self.cli = CLI(
        root=self.root,
        application=self._CreatePromptApplication(args),
        eventloop=shortcuts.create_eventloop(),
        output=shortcuts.create_output(),
        restrict=restrict)
    self.key_bindings.Initialize(self.cli)

  def _CreatePromptApplication(self, args):
    """Creates a shell prompt Application."""

    # Make sure that complete_while_typing is disabled when
    # enable_history_search is enabled. (First convert to SimpleFilter, to
    # avoid doing bitwise operations on bool objects.)
    complete_while_typing = shortcuts.to_simple_filter(True)
    enable_history_search = shortcuts.to_simple_filter(False)
    multiline = shortcuts.to_simple_filter(False)
    complete_while_typing &= ~enable_history_search

    history_file = os.path.join(config.Paths().global_config_dir,
                                'shell_history')

    return pt_application.Application(
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
            history=pt_history.FileHistory(history_file),
            validator=None,
            completer=completer.ShellCliCompleter(self.root,
                                                  args=args,
                                                  hidden=self.hidden),
            auto_suggest=None,
            accept_action=pt_buffer.AcceptAction.RETURN_DOCUMENT,
            initial_document=document.Document(''),),
        style=shell_style.GetDocumentStyle(),
        clipboard=None,
        key_bindings_registry=self.key_bindings.MakeRegistry(),
        get_title=None,
        mouse_support=False,
        erase_when_done=False,
        on_abort=pt_application.AbortAction.RAISE_EXCEPTION,
        on_exit=pt_application.AbortAction.RAISE_EXCEPTION)

  def _GetBottomToolbarTokens(self, _):
    """Returns the bottom toolbar tokens based on the key binding state."""
    named_configs.ActivePropertiesFile().Invalidate()
    project = properties.VALUES.core.project.Get() or '<NO PROJECT SET>'
    account = properties.VALUES.core.account.Get() or '<NO ACCOUNT SET>'
    separator = (Token.Toolbar.Separator, self.BOTTOM_TOOLBAR_SEPARATOR)

    tokens = []
    for binding in self.key_bindings.bindings:
      label = binding.GetLabel()
      if label is not None:
        tokens.append((Token.Toolbar.Help, label))
        tokens.append(separator)
    tokens.extend([
        (Token.Toolbar.Project, project),
        separator,
        (Token.Toolbar.Account, account),
    ])

    return tokens

  def Prompt(self):
    """Prompts and returns one command line."""
    result = self.cli.run(reset_current_buffer=False)
    if isinstance(result, document.Document):  # Backwards-compatibility.
      return result.text
    return result

  def Run(self, text):
    """Runs the command(s) in text and waits for them to complete."""
    status = self.coshell.Run(text)
    if status > 128:
      # command interrupted - print an empty line to clear partial output
      print
    return status  # currently ignored but returned for completeness

  def Loop(self):
    """Loops Prompt-Run until ^D exit, or quit."""
    while True:
      try:
        text = self.Prompt()
        if text is None:
          break
        if self.cli.restrict:
          text = text.strip()
          if not text.startswith(self.restrict):
            text = self.cli.restrict + ' ' + text
        self.Run(text)  # paradoxically ignored - coshell maintains $?
      except EOFError:
        # ctrl-d
        break
      except KeyboardInterrupt:
        # ignore ctrl-c
        pass
      except coshell.CoshellExitException:
        break


def main(cli=None, args=None, hidden=False, prompt='$ ', restrict=None):
  """The shell application loop."""
  cosh = coshell.Coshell()
  try:
    Application(
        cli=cli,
        args=args,
        cosh=cosh,
        hidden=hidden,
        prompt=prompt,
        restrict=restrict).Loop()
  finally:
    status = cosh.Close()
  sys.exit(status)
