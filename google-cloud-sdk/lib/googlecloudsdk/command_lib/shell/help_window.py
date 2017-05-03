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
from googlecloudsdk.command_lib.shell import gcloud_parser
from googlecloudsdk.command_lib.shell.gcloud_tree import gcloud_tree
from googlecloudsdk.core.document_renderers import render_document
from googlecloudsdk.core.document_renderers import token_renderer
from prompt_toolkit.layout import controls
from prompt_toolkit.token import Token


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


def GetCurrentInvocation(invocations, pos):
  """Determine the current invocation given a cursor position.

  Args:
    invocations: a list of GcloudInvocations
    pos: an int giving the current cursor position

  Returns:
    The corresponding GcloudInvocation at position pos, or None.
  """
  for invocation in invocations:
    tokens = invocation.tokens
    if tokens:
      start = tokens[0].start
      end = tokens[-1].end
      if ((start <= pos <= end) or
          (invocations.index(invocation) == len(invocations)-1)):
        return tokens
  return None


def GetCurrentToken(tokens, pos):
  """Determine the current token given a cursor position.

  Args:
    tokens: a list of gcloud_parser.ArgTokens
    pos: an int giving the current cursor position

  Returns:
    The gcloud_parser.ArgToken at that position or None.
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
  """Generates and renders the corresponding help content in the gcloud shell.

  Args:
    cli: the CLI in which to render the help contents.
    width: the width of the help prompt.

  Returns:
    A list with one list per line, each containing (token, string) tuples for
    words in the help text. These tuples represent (Markdown format,
    actual text) pairs.
  """
  if width > 80:
    width = 80
  doc = cli.current_buffer.document

  tokens = GetCurrentInvocation(gcloud_parser.ParseLine(doc.text),
                                doc.cursor_position)
  if not tokens:
    return []

  tok = GetCurrentToken(tokens, doc.cursor_position)
  if not tok:
    return []

  if tok.token_type == gcloud_parser.ArgTokenType.COMMAND:
    return GenerateHelpForCommand(tok, width)
  elif tok.token_type == gcloud_parser.ArgTokenType.GROUP:
    return GenerateHelpForCommand(tok, width)
  elif tok.token_type == gcloud_parser.ArgTokenType.FLAG:
    return GenerateHelpForFlag(tok, width)
  elif tok.token_type == gcloud_parser.ArgTokenType.FLAG_ARG:
    return GenerateHelpForFlag(tok, width)
  elif tok.token_type == gcloud_parser.ArgTokenType.POSITIONAL:
    return GenerateHelpForPositional(tok, width)

  return []


def RenderMarkdown(fin, width, height=HELP_WINDOW_HEIGHT, compact=True):
  """Renders the markdown for the help prompt in the gcloud shell.

  Args:
    fin: the input stream containing the markdown.
    width: the width for which to create the renderer.
    height: optional value representing the height for which to create the
    renderer. Defaults to HELP_WINDOW_HEIGHT.
    compact: optional value representing whether the renderer representation
    should be compact. Defaults to True.

  Returns:
    A MarkdownRenderer Finish() value.
  """
  return render_document.MarkdownRenderer(
      token_renderer.TokenRenderer(width=width, height=height, compact=compact),
      fin=fin).Run()


def GetDescriptionForCommand(token):
  """Gets the description for the command specified in token.

  Args:
    token: the ArgTokenType.COMMAND token for which to get the description.

  Returns:
    A StringIO with the description of the token.
  """
  gen = markdown.CliTreeMarkdownGenerator(token.tree, gcloud_tree)
  gen.PrintSectionIfExists('DESCRIPTION', disable_header=True)
  doc = gen.Edit()
  return StringIO.StringIO(doc)


def GetSynopsisForCommand(token):
  """Gets the synopsis for the command specified in token.

  Args:
    token: the ArgTokenType.COMMAND token for which to get the synopsis.

  Returns:
    A StringIO with the synopsis of the token.
  """
  gen = markdown.CliTreeMarkdownGenerator(token.tree, gcloud_tree)
  gen.PrintSynopsisSection()
  doc = gen.Edit()
  return StringIO.StringIO(doc)


def GetFullReferencePromptTokens():
  """A line of Prompt Toolkit tokens about opening full reference pages."""
  return [[(Token.Purple, 'ctrl-w'),
           (Token, ' to open full reference page within browser')]]


def GenerateHelpForCommand(token, width):
  """Generates the help to show in the CLI for the command token passed.

  Args:
    token: the command token to show help for.
    width: the width of the CLI.

  Returns:
    A list with one list per line, each containing (token, string) tuples for
    words in the help text. These tuples represent (Markdown format,
    actual text) pairs.
  """
  blank_line = [[]]
  return (
      RenderMarkdown(GetDescriptionForCommand(token), width=width, height=2) +
      blank_line +
      RenderMarkdown(
          GetSynopsisForCommand(token), width=width, height=5, compact=False) +
      blank_line +
      GetFullReferencePromptTokens())


def GetDefinitionForFlag(token):
  """Gets the definition for the flag specified in token.

  Args:
    token: the ArgTokenType.FLAG/FLAG_ARG token for which to get the definition.

  Returns:
    A StringIO with the definition of the token.
  """
  gen = markdown.CliTreeMarkdownGenerator(gcloud_tree, gcloud_tree)
  gen.PrintFlagDefinition(token.tree)
  mark = gen.Edit()
  return StringIO.StringIO(mark)


def GenerateHelpForFlag(token, width):
  """Generates the help to show in the CLI for the flag token passed.

  Args:
    token: the command token to show help for.
    width: the width of the CLI.

  Returns:
    A list with one list per line, each containing (token, string) tuples for
    words in the help text. These tuples represent (Markdown format,
    actual text) pairs.
  """
  return RenderMarkdown(GetDefinitionForFlag(token), width=width)


def GetDefinitionForPositional(token):
  """Gets the definition for the positional specified in token.

  Args:
    token: the ArgTokenType.POSITIONAL token for which to get the definition.

  Returns:
    A StringIO with the definition of the token.
  """
  gen = markdown.CliTreeMarkdownGenerator(gcloud_tree, gcloud_tree)
  gen.PrintPositionalDefinition(markdown.Positional(token.tree))
  mark = gen.Edit()
  return StringIO.StringIO(mark)


def GenerateHelpForPositional(token, width):
  """Generates the help to show in the CLI for the positional token passed.

  Args:
    token: the command token to show help for.
    width: the width of the CLI.

  Returns:
    A list with one list per line, each containing (token, string) tuples for
    words in the help text. These tuples represent (Markdown format,
    actual text) pairs.
  """
  return RenderMarkdown(GetDefinitionForPositional(token), width=width)
