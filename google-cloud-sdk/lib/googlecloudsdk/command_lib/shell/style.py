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

"""gcloud shell styles."""

from prompt_toolkit import styles
from prompt_toolkit.token import Token


BLUE = '#00DED1'
GREEN = '#008000'
GRAY = '#666666'
DARK_GRAY = '#333333'
BLACK = '#000000'
PURPLE = '#FF00FF'

BOLD = 'bold'
ITALIC = 'underline'  # there is no italic


def Color(foreground=None, background=None, bold=False):
  components = []
  if foreground:
    components.append(foreground)
  if background:
    components.append('bg:' + background)
  if bold:
    components.append('bold')
  return ' '.join(components)


def GetDocumentStyle():
  """Return the color styles for the layout."""
  prompt_styles = styles.default_style_extensions
  prompt_styles.update({
      Token.Menu.Completions.Completion.Current: Color(BLUE, GRAY),
      Token.Menu.Completions.Completion: Color(BLUE, DARK_GRAY),
      Token.Toolbar: BOLD,
      Token.Toolbar.Account: BOLD,
      Token.Toolbar.Separator: BOLD,
      Token.Toolbar.Project: BOLD,
      Token.Toolbar.Help: BOLD,
      Token.Prompt: BOLD,
      Token.HSep: Color(GREEN),
      Token.Markdown.Section: BOLD,
      Token.Markdown.Definition: BOLD,
      Token.Markdown.Value: ITALIC,
      Token.Markdown.Truncated: Color(background=DARK_GRAY),
      Token.Purple: BOLD,
  })
  return styles.PygmentsStyle.from_defaults(style_dict=prompt_styles)
