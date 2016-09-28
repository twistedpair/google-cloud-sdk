# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Util for gcloud_shell operations."""

from googlecloudsdk.command_lib.static_completion import lookup
from googlecloudsdk.core import config
from googlecloudsdk.core import properties
from googlecloudsdk.core.configurations import named_configs
from prompt_toolkit import Application
from prompt_toolkit import auto_suggest
from prompt_toolkit import buffer as ptkbuffer
from prompt_toolkit import completion
from prompt_toolkit import history
from prompt_toolkit import interface
from prompt_toolkit import shortcuts
from prompt_toolkit import styles
from prompt_toolkit.key_binding import manager
from pygments.lexers import shell
from pygments.token import Token


BLUE = '#00bbcc'
GRAY = '#666666'
DARK_GRAY = '#333333'
BLACK = '#000000'


def Color(foreground=None, background=None):
  components = []
  if foreground:
    components.append(foreground)
  if background:
    components.append('bg:' + background)
  return ' '.join(components)


def GetDocumentStyle():
  """Return the color styles for the layout."""
  prompt_styles = styles.default_style_extensions
  prompt_styles.update({
      Token.Menu.Completions.Completion.Current: Color(BLUE, GRAY),
      Token.Menu.Completions.Completion: Color(BLUE, DARK_GRAY),
      Token.Toolbar: Color(BLUE, DARK_GRAY),
      Token.Toolbar.Account: Color(),
      Token.Toolbar.Separator: Color(),
      Token.Toolbar.Project: Color(),
      Token.Prompt: Color()
  })
  return styles.PygmentsStyle.from_defaults(style_dict=prompt_styles)


def GetBottomToolbarTokens(unused_cli):
  # Prevents caching of properties, so we will update the toolbar in response to
  # changes in property status
  named_configs.ActivePropertiesFile().Invalidate()
  project = properties.VALUES.core.project.Get() or '<NO PROJECT SET>'
  account = properties.VALUES.core.account.Get() or '<NO ACCOUNT SET>'
  return [(Token.Toolbar.Account, account),
          (Token.Toolbar.Separator, ' - '),
          (Token.Toolbar.Project, project)]


def _KeyBindings():
  """Returns KeyBindingManager that allows key binding in the Application."""

  # Need to set to True to allow any exit bindings like ctrl-d.
  return manager.KeyBindingManager(enable_abort_and_exit_bindings=True,
                                   enable_auto_suggest_bindings=True)


class ShellCliCompleter(completion.Completer):
  """A prompt_toolkit shell CLI completer."""

  def __init__(self, gcloud_py_dir):
    self.table = lookup.LoadTable(gcloud_py_dir)

  def get_completions(self, doc, complete_event):
    """Get the completions for doc.

    Args:
      doc: A Document instance containing the shell command line to complete.
      complete_event: The CompleteEvent that triggered this completion.
    Yields:
      List of completions for a given input
    """
    input_line = doc.current_line_before_cursor

    # Make sure command contains gcloud
    if input_line.find('gcloud') == -1:
      return

    input_line = GetLastGcloudCmd(input_line)

    possible_completions = []
    try:
      possible_completions = lookup.FindCompletions(self.table, input_line)
    except (lookup.CannotHandleCompletionError, ValueError):
      return

    for item in possible_completions:
      last = input_line.split(' ')[-1]
      token = 0 - len(last)
      yield completion.Completion(item, token)


def CreateCli(gcloud_py_dir):
  """Creates the CLI application.

  Args:
    gcloud_py_dir: str, path to completion lookup table

  Returns:
    cli, a cli instance
  """
  completer = ShellCliCompleter(gcloud_py_dir)
  in_memory_history = history.InMemoryHistory()
  auto_suggest_from_history = auto_suggest.AutoSuggestFromHistory()
  key_manager = _KeyBindings()

  layout = shortcuts.create_prompt_layout(
      lexer=shell.BashLexer,
      get_bottom_toolbar_tokens=GetBottomToolbarTokens,
      message=u'Cloud SDK {0}> '.format(config.CLOUD_SDK_VERSION))

  cli_buffer = ptkbuffer.Buffer(
      history=in_memory_history,
      auto_suggest=auto_suggest_from_history,
      complete_while_typing=True,
      completer=completer,
      accept_action=interface.AcceptAction.RETURN_DOCUMENT)

  application = Application(
      style=GetDocumentStyle(),
      buffer=cli_buffer,
      layout=layout,
      key_bindings_registry=key_manager.registry,
      mouse_support=True)

  cli = interface.CommandLineInterface(
      application=application,
      eventloop=shortcuts.create_eventloop())

  return cli


def GetLastGcloudCmd(cmd):
  """Get the last substring beginning with gcloud.

  Args:
    cmd: str, the full command string user entered

  Returns:
    cmd: str, the last substring beginning with gcloud
  """
  split_point = cmd.rfind('gcloud')
  return cmd[split_point: ]


