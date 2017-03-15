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

"""gcloud shell layout.

  This is the prompt toolkit layout for the shell prompt. It determines the
  positioning and layout of the prompt, toolbars, autocomplete, etc.
"""

from googlecloudsdk.command_lib.shell import help_window
from prompt_toolkit import enums
from prompt_toolkit import filters
from prompt_toolkit import layout
from prompt_toolkit import shortcuts
from prompt_toolkit.layout import containers
from prompt_toolkit.layout import controls
from prompt_toolkit.layout import margins
from prompt_toolkit.layout import menus
from prompt_toolkit.layout import processors
from prompt_toolkit.layout import toolbars as pt_toolbars
from prompt_toolkit.layout.dimension import LayoutDimension
from prompt_toolkit.layout.prompt import DefaultPrompt
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.token import Token


@filters.Condition
def UserTypingFilter(cli):
  """Determine if the input field is empty."""
  if cli.current_buffer.document.text:
    return True
  else:
    return False


def CreatePromptLayout(message='',
                       lexer=None,
                       is_password=False,
                       reserve_space_for_menu=6,
                       get_prompt_tokens=None,
                       get_continuation_tokens=None,
                       get_bottom_toolbar_tokens=None,
                       display_completions_in_columns=False,
                       extra_input_processors=None,
                       multiline=False,
                       wrap_lines=True,
                       show_help=True):
  """Create a container instance for the prompt."""
  assert isinstance(message, unicode), 'Please provide a unicode string.'
  assert get_bottom_toolbar_tokens is None or callable(
      get_bottom_toolbar_tokens)
  assert get_prompt_tokens is None or callable(get_prompt_tokens)
  assert not (message and get_prompt_tokens)

  display_completions_in_columns = filters.to_cli_filter(
      display_completions_in_columns)
  multiline = filters.to_cli_filter(multiline)

  if get_prompt_tokens is None:
    get_prompt_tokens = lambda _: [(Token.Prompt, message)]

  has_before_tokens, get_prompt_tokens_1, get_prompt_tokens_2 = (
      shortcuts._split_multiline_prompt(get_prompt_tokens))  # pylint: disable=protected-access
  # TODO(b/35347840): reimplement _split_multiline_prompt to remove
  #                   protected-access.

  # Create processors list.
  input_processors = [
      processors.ConditionalProcessor(
          # By default, only highlight search when the search
          # input has the focus. (Note that this doesn't mean
          # there is no search: the Vi 'n' binding for instance
          # still allows to jump to the next match in
          # navigation mode.)
          processors.HighlightSearchProcessor(preview_search=True),
          filters.HasFocus(enums.SEARCH_BUFFER)),
      processors.HighlightSelectionProcessor(),
      processors.ConditionalProcessor(processors.AppendAutoSuggestion(),
                                      filters.HasFocus(enums.DEFAULT_BUFFER)
                                      & ~filters.IsDone()),
      processors.ConditionalProcessor(processors.PasswordProcessor(),
                                      is_password),
  ]

  if extra_input_processors:
    input_processors.extend(extra_input_processors)

  # Show the prompt before the input (using the DefaultPrompt processor.
  # This also replaces it with reverse-i-search and 'arg' when required.
  # (Only for single line mode.)
  # (DefaultPrompt should always be at the end of the processors.)
  input_processors.append(
      processors.ConditionalProcessor(
          DefaultPrompt(get_prompt_tokens_2), ~multiline))

  # Create toolbars
  toolbars = []
  toolbars.append(
      containers.ConditionalContainer(
          layout.HSplit([
              layout.Window(
                  controls.FillControl(char=Char('-', Token.HSep)),
                  height=LayoutDimension.exact(1)),
              layout.Window(
                  help_window.HelpWindowControl(
                      default_char=Char(' ', Token.Toolbar)),
                  height=LayoutDimension(
                      preferred=help_window.HELP_WINDOW_HEIGHT,
                      max=help_window.HELP_WINDOW_HEIGHT)),
          ]),
          filter=(show_help & UserTypingFilter & ~filters.IsDone() &
                  filters.RendererHeightIsKnown())))
  if get_bottom_toolbar_tokens:
    toolbars.append(
        containers.ConditionalContainer(
            layout.HSplit([
                layout.Window(
                    controls.FillControl(char=Char('-', Token.HSep)),
                    height=LayoutDimension.exact(1)),
                layout.Window(
                    controls.TokenListControl(
                        get_bottom_toolbar_tokens,
                        default_char=Char(' ', Token.Toolbar)),
                    height=LayoutDimension.exact(1)),
            ]),
            filter=~filters.IsDone() & filters.RendererHeightIsKnown()))

  def GetHeight(cli):
    """Determine the height for the input buffer."""
    # If there is an autocompletion menu to be shown, make sure that our
    # layout has at least a minimal height in order to display it.
    if reserve_space_for_menu and not cli.is_done:
      buff = cli.current_buffer

      # Reserve the space, either when there are completions, or when
      # `complete_while_typing` is true and we expect completions very
      # soon.
      if UserTypingFilter(cli) or buff.complete_state is not None:
        return LayoutDimension(min=reserve_space_for_menu)

    return LayoutDimension()

  # Create and return Container instance.
  return layout.HSplit([
      # The main input, with completion menus floating on top of it.
      containers.FloatContainer(
          layout.HSplit([
              containers.ConditionalContainer(
                  layout.Window(
                      controls.TokenListControl(get_prompt_tokens_1),
                      dont_extend_height=True),
                  filters.Condition(has_before_tokens)),
              layout.Window(
                  controls.BufferControl(
                      input_processors=input_processors,
                      lexer=lexer,
                      # Enable preview_search, we want to have immediate
                      # feedback in reverse-i-search mode.
                      preview_search=True),
                  get_height=GetHeight,
                  left_margins=[
                      # In multiline mode, use the window margin to display
                      # the prompt and continuation tokens.
                      margins.ConditionalMargin(
                          margins.PromptMargin(get_prompt_tokens_2,
                                               get_continuation_tokens),
                          filter=multiline)
                  ],
                  wrap_lines=wrap_lines,),
          ]),
          [
              # Completion menus.
              layout.Float(
                  xcursor=True,
                  ycursor=True,
                  content=menus.CompletionsMenu(
                      max_height=16,
                      scroll_offset=1,
                      extra_filter=filters.HasFocus(enums.DEFAULT_BUFFER) &
                      ~display_completions_in_columns)),
              layout.Float(
                  xcursor=True,
                  ycursor=True,
                  content=menus.MultiColumnCompletionsMenu(
                      extra_filter=filters.HasFocus(enums.DEFAULT_BUFFER) &
                      display_completions_in_columns,
                      show_meta=True)),
          ]),
      pt_toolbars.ValidationToolbar(),
      pt_toolbars.SystemToolbar(),

      # In multiline mode, we use two toolbars for 'arg' and 'search'.
      containers.ConditionalContainer(pt_toolbars.ArgToolbar(), multiline),
      containers.ConditionalContainer(pt_toolbars.SearchToolbar(), multiline),
  ] + toolbars)
