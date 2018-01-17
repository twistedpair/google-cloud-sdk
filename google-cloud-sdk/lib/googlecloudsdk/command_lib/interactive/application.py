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

"""The gcloud interactive application."""

from __future__ import unicode_literals

import os
import sys

from googlecloudsdk.calliope import cli_tree

from googlecloudsdk.command_lib.interactive import bindings
from googlecloudsdk.command_lib.interactive import completer
from googlecloudsdk.command_lib.interactive import coshell
from googlecloudsdk.command_lib.interactive import layout
from googlecloudsdk.command_lib.interactive import parser
from googlecloudsdk.command_lib.interactive import style as interactive_style

from googlecloudsdk.command_lib.meta import generate_cli_trees

from googlecloudsdk.core import config as core_config
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs

from prompt_toolkit import application as pt_application
from prompt_toolkit import auto_suggest
from prompt_toolkit import buffer as pt_buffer
from prompt_toolkit import document
from prompt_toolkit import filters
from prompt_toolkit import history as pt_history
from prompt_toolkit import interface
from prompt_toolkit import shortcuts
from prompt_toolkit import token
from prompt_toolkit.layout import processors as pt_layout


class CLI(interface.CommandLineInterface):
  """Extends the prompt CLI object to include our state.

  Attributes:
    root: The root of the static CLI tree that contains all commands, flags,
      positionals and help doc snippets.
  """

  def __init__(self, config=None, cosh=None, root=None, interactive_parser=None,
               application=None, eventloop=None, output=None):
    super(CLI, self).__init__(
        application=application,
        eventloop=eventloop,
        output=output)
    self.config = config
    self.coshell = cosh
    self.parser = interactive_parser
    self.root = root

  def Run(self, text, alternate_screen=False):
    """Runs the command line in text, optionally in an alternate screen.

    This should use an alternate screen but I haven't found the incantations
    to get that working. Currently alternate_screen=True clears the default
    screen so full screen commands, like editors and man or help, have a clean
    slate. Otherwise they may overwrite previous output and end up with a
    garbled mess. The downside is that on return the default screen is
    clobbered. Not too bad right now because this is only used as a fallback
    when the real web browser is inaccessible (for example when running in ssh).

    Args:
      text: The command line string to run.
      alternate_screen: Send output to an alternate screen and restore the
        original screen when done.
    """
    if alternate_screen:
      self.renderer.erase()
    self.coshell.Run(text)


class Context(pt_layout.Processor):
  """Input processor that adds context."""

  @staticmethod
  def apply_transformation(cli, doc, lineno, source_to_display, tokens):
    if not cli.context_was_set and not doc.text:
      cli.context_was_set = True
      cli.current_buffer.set_document(document.Document(cli.config.context))
    return pt_layout.Transformation(
        tokens, display_to_source=lambda i: len(cli.config.context))


def _GetJustifiedTokens(labels, width=80, justify=True):
  """Returns labels as left- and right-justified tokens."""
  if justify:
    used_width = 0
    label_count = 0
    for label in labels:
      if label is None:
        continue
      label_count += 1
      used_width += len(label)

    if not label_count:
      return []
    elif label_count > 1:
      separator_width = (width - used_width) / (label_count - 1)
      if separator_width < 1:
        separator_width = 1
    else:
      separator_width = 1

    separator_remainder = (
        width - used_width - separator_width * (label_count - 1))
    if separator_remainder > 0:
      # Uneven separators widths. Fudge the separatos by this amount for the
      # first separator_remainder separators to favor right justfication. A
      # true nit, but people could be staring at this all day.
      separator_width += 1

  else:
    separator_remainder = 0
    separator_width = 2

  tokens = []
  for label in labels:
    if label is None:
      continue
    tokens.append((token.Token.Toolbar.Help, label))
    tokens.append((token.Token.Toolbar.Separator, ' ' * separator_width))
    separator_remainder -= 1
    if separator_remainder == 0:
      # Only do this once for this loop.
      separator_width -= 1
  return tokens[:-1]


class Application(object):
  """The CLI application.

  Attributes:
    args: The parsed command line arguments.
    config: The interactive shell config object.
    coshell: The shell coprocess object.
    key_bindings: The key_bindings object holding the key binding list and
      toggle states.
  """

  def __init__(self, cosh=None, args=None, config=None):
    self.args = args
    self.coshell = cosh
    self.config = config
    self.key_bindings = bindings.KeyBindings(
        edit_mode=self.coshell.edit_mode == 'emacs')

    # Load the default CLI trees. On startup we ignore out of date trees. The
    # alternative is to regenerate them before the first prompt. This could be
    # a noticeable delay for users that accrue a lot of trees. Although ignored
    # at startup, the regen will happen on demand as the individual commands
    # are typed.
    self.root = generate_cli_trees.LoadAll(
        ignore_out_of_date=True, warn_on_exceptions=True)

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

    # Create the parser and completer.
    interactive_parser = parser.Parser(
        self.root,
        context=config.context,
        hidden=config.hidden)
    interactive_completer = completer.InteractiveCliCompleter(
        interactive_parser=interactive_parser,
        args=args,
        cosh=self.coshell,
        hidden=config.hidden,
        manpage_generator=config.manpage_generator)

    # Make sure that complete_while_typing is disabled when
    # enable_history_search is enabled. (First convert to SimpleFilter, to
    # avoid doing bitwise operations on bool objects.)
    complete_while_typing = shortcuts.to_simple_filter(True)
    enable_history_search = shortcuts.to_simple_filter(False)
    complete_while_typing &= ~enable_history_search
    history_file = os.path.join(core_config.Paths().global_config_dir,
                                'shell_history')
    multiline = shortcuts.to_simple_filter(False)

    # Create the default buffer.

    self.default_buffer = pt_buffer.Buffer(
        enable_history_search=enable_history_search,
        complete_while_typing=complete_while_typing,
        is_multiline=multiline,
        history=pt_history.FileHistory(history_file),
        validator=None,
        completer=interactive_completer,
        auto_suggest=(auto_suggest.AutoSuggestFromHistory()
                      if config.suggest else None),
        accept_action=pt_buffer.AcceptAction.RETURN_DOCUMENT,
    )

    # Create the CLI.
    self.cli = CLI(
        config=config,
        cosh=cosh,
        root=self.root,
        interactive_parser=interactive_parser,
        application=self._CreatePromptApplication(config=config,
                                                  multiline=multiline),
        eventloop=shortcuts.create_eventloop(),
        output=shortcuts.create_output(),
    )
    self.key_bindings.Initialize(self.cli)

  def _CreatePromptApplication(self, config, multiline):
    """Creates a shell prompt Application."""

    return pt_application.Application(
        layout=layout.CreatePromptLayout(
            config=config,
            extra_input_processors=[Context()],
            get_bottom_status_tokens=self._GetBottomStatusTokens,
            get_bottom_toolbar_tokens=self._GetBottomToolbarTokens,
            get_continuation_tokens=None,
            get_prompt_tokens=None,
            is_password=False,
            lexer=None,
            multiline=filters.Condition(lambda cli: multiline()),
            show_help=filters.Condition(
                lambda _: self.key_bindings.help_key.toggle),
            wrap_lines=True,
        ),
        buffer=self.default_buffer,
        clipboard=None,
        erase_when_done=False,
        get_title=None,
        key_bindings_registry=self.key_bindings.MakeRegistry(),
        mouse_support=False,
        reverse_vi_search_direction=True,
        style=interactive_style.GetDocumentStyle(),
    )

  def _GetProjectAndAccount(self):
    """Returns the current (project, account) tuple."""
    if not self.args.IsSpecified('project'):
      named_configs.ActivePropertiesFile().Invalidate()
    project = properties.VALUES.core.project.Get() or '<NO PROJECT SET>'
    account = properties.VALUES.core.account.Get() or '<NO ACCOUNT SET>'
    return (project, account)

  def _GetBottomStatusTokens(self, cli):
    """Returns the bottom status tokens based on the key binding state."""
    project, account = self._GetProjectAndAccount()
    return _GetJustifiedTokens(
        ['Project:' + project, 'Account:' + account],
        justify=cli.config.justify_bottom_lines,
        width=cli.output.get_size().columns)

  def _GetBottomToolbarTokens(self, cli):
    """Returns the bottom toolbar tokens based on the key binding state."""
    tokens = [binding.GetLabel() for binding in self.key_bindings.bindings]
    if not cli.config.bottom_status_line:
      project, account = self._GetProjectAndAccount()
      tokens.append(project)
      tokens.append(account)
    return _GetJustifiedTokens(
        tokens,
        justify=cli.config.justify_bottom_lines,
        width=cli.output.get_size().columns)

  def Prompt(self):
    """Prompts and returns one command line."""
    self.cli.context_was_set = not self.cli.config.context
    doc = self.cli.run()
    return doc.text if doc else None

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
        self.Run(text)  # paradoxically ignored - coshell maintains $?
      except EOFError:
        # ctrl-d
        break
      except KeyboardInterrupt:
        # ignore ctrl-c
        pass
      except coshell.CoshellExitException:
        break


def main(args=None, config=None):
  """The interactive application loop."""
  cosh = coshell.Coshell()
  try:
    Application(
        args=args,
        cosh=cosh,
        config=config,
    ).Loop()
  finally:
    status = cosh.Close()
  sys.exit(status)
