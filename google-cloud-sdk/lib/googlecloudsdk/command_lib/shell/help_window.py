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

"""Code for the gcloud shell help window."""

import StringIO

from googlecloudsdk.calliope import cli_tree_markdown as markdown
from googlecloudsdk.command_lib.shell import parser
from googlecloudsdk.core.document_renderers import render_document
from googlecloudsdk.core.document_renderers import token_renderer
from prompt_toolkit.layout import controls


# The height of the help window in the layout.
HELP_WINDOW_HEIGHT = 10


class HelpWindowControl(controls.UIControl):
  """Implementation of the help window."""

  def __init__(self, default_char=None):
    self._default_char = default_char

  def create_content(self, cli, width, height):
    data = GenerateHelpContent(cli, width)

    return controls.UIContent(
        lambda i: data[i],
        line_count=len(data),
        show_cursor=False,
        default_char=self._default_char)


def GetCurrentToken(tokens, pos):
  """Determine the current token given a cursor position.

  Args:
    tokens: a list of parser.ArgTokens
    pos: an int giving the current cursor position

  Returns:
    The parser.ArgToken at that position or None.
  """
  i = 0
  while i < len(tokens):
    if pos >= tokens[i].start and pos < tokens[i].end:
      return tokens[i]
    if pos < tokens[i].start:
      return tokens[i-1] if i > 0 else None
    i += 1

  return tokens[len(tokens)-1] if tokens else None


def GenerateHelpContent(cli, width):
  """Returns help lines for the current token."""
  if width > 80:
    width = 80
  doc = cli.current_buffer.document
  tok = GetCurrentToken(parser.ParseCommand(cli.root, doc.text),
                        doc.cursor_position)
  if not tok:
    return []

  if tok.token_type == parser.ArgTokenType.COMMAND:
    return GenerateHelpForCommand(cli, tok, width)
  elif tok.token_type == parser.ArgTokenType.GROUP:
    return GenerateHelpForCommand(cli, tok, width)
  elif tok.token_type == parser.ArgTokenType.FLAG:
    return GenerateHelpForFlag(cli, tok, width)
  elif tok.token_type == parser.ArgTokenType.POSITIONAL:
    return GenerateHelpForPositional(cli, tok, width)

  return []


def GenerateHelpForCommand(cli, token, width):
  """Returns help lines for a command token."""
  lines = []

  # Get description
  height = 4
  gen = markdown.CliTreeMarkdownGenerator(token.tree, cli.root)
  gen.PrintSectionIfExists('DESCRIPTION', disable_header=True)
  doc = gen.Edit()
  fin = StringIO.StringIO(doc)
  lines.extend(render_document.MarkdownRenderer(
      token_renderer.TokenRenderer(
          width=width, height=height), fin=fin).Run())

  lines.append([])  # blank line

  # Get synopis
  height = 5
  gen = markdown.CliTreeMarkdownGenerator(token.tree, cli.root)
  gen.PrintSynopsisSection()
  doc = gen.Edit()
  fin = StringIO.StringIO(doc)
  lines.extend(render_document.MarkdownRenderer(
      token_renderer.TokenRenderer(
          width=width, height=height, compact=False), fin=fin).Run())

  return lines


def GenerateHelpForFlag(cli, token, width):
  """Returns help lines for a flag token."""
  gen = markdown.CliTreeMarkdownGenerator(cli.root, cli.root)
  gen.PrintFlagDefinition(token.tree)
  mark = gen.Edit()

  fin = StringIO.StringIO(mark)
  return render_document.MarkdownRenderer(
      token_renderer.TokenRenderer(
          width=width, height=HELP_WINDOW_HEIGHT), fin=fin).Run()


def GenerateHelpForPositional(cli, token, width):
  """Returns help lines for a positional token."""
  gen = markdown.CliTreeMarkdownGenerator(cli.root, cli.root)
  gen.PrintPositionalDefinition(markdown.Positional(token.tree))
  mark = gen.Edit()

  fin = StringIO.StringIO(mark)
  return render_document.MarkdownRenderer(
      token_renderer.TokenRenderer(
          width=width, height=HELP_WINDOW_HEIGHT), fin=fin).Run()
