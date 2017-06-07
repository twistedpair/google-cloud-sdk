# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Generate usage text for displaying to the user.
"""

import argparse
import difflib
import re
import StringIO
import sys
import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base

LINE_WIDTH = 80
HELP_INDENT = 25


def IsSuppressed(arg):
  """Returns True if arg is suppressed."""
  return arg.help == argparse.SUPPRESS


def FilterOutSuppressed(args):
  """Returns a copy of args containing only non-suppressed arguments."""
  return [a for a in args if not IsSuppressed(a)]


class HelpInfo(object):
  """A class to hold some the information we need to generate help text."""

  def __init__(self, help_text, is_hidden, release_track):
    """Create a HelpInfo object.

    Args:
      help_text: str, The text of the help message.
      is_hidden: bool, True if this command or group has been marked as hidden.
      release_track: calliope.base.ReleaseTrack, The maturity level of this
        command.
    """
    self.help_text = help_text or ''
    self.is_hidden = is_hidden
    self.release_track = release_track


class TextChoiceSuggester(object):
  """Utility to suggest mistyped commands.

  """
  _SYNONYM_SETS = [
      set(['create', 'add']),
      set(['delete', 'remove']),
      set(['describe', 'get']),
      set(['patch', 'update']),
  ]

  def __init__(self, choices=None):
    # A mapping of 'thing typed' to the suggestion that should be offered.
    # Often, these will be the same, but this allows for offering more currated
    # suggestions for more commonly misused things.
    self._choices = {}
    if choices:
      self.AddChoices(choices)

  def AddChoices(self, choices):
    """Add a set of valid things that can be suggested.

    Args:
      choices: [str], The valid choices.
    """
    for choice in choices:
      if choice not in self._choices:
        # Keep the first choice mapping that was added so later aliases don't
        # clobber real choices.
        self._choices[choice] = choice

  def AddAliases(self, aliases, suggestion):
    """Add an alias that is not actually a valid choice, but will suggest one.

    This should be called after AddChoices() so that aliases will not clobber
    any actual choices.

    Args:
      aliases: [str], The aliases for the valid choice.  This is something
        someone will commonly type when they actually mean something else.
      suggestion: str, The valid choice to suggest.
    """
    for alias in aliases:
      if alias not in self._choices:
        self._choices[alias] = suggestion

  def AddSynonyms(self):
    """Activate the set of synonyms for this suggester."""
    for s_set in TextChoiceSuggester._SYNONYM_SETS:
      valid_choices = set(self._choices.keys()) & s_set
      for choice in valid_choices:
        # Add all synonyms in the set as aliases for each real choice that is
        # valid.  This will never clobber the original choice that is there.
        # If none of the synonyms are valid choices, this will not add any
        # aliases for this synonym set.
        self.AddAliases(s_set, choice)

  def GetSuggestion(self, arg):
    """Find the item that is closest to what was attempted.

    Args:
      arg: str, The argument provided.

    Returns:
      str, The closest match.
    """
    if not self._choices:
      return None

    match = difflib.get_close_matches(arg.lower(), self._choices, 1)
    return self._choices[match[0]] if match else None


def WrapMessageInNargs(msg, nargs):
  """Create the display help string for a positional arg.

  Args:
    msg: [str] The possibly repeated text.
    nargs: The repetition operator.

  Returns:
    str, The string representation for printing.
  """
  if nargs == '+':
    return '{msg} [{msg} ...]'.format(msg=msg)
  elif nargs == '*':
    return '[{msg} ...]'.format(msg=msg)
  elif nargs == argparse.REMAINDER:
    return '[-- {msg} ...]'.format(msg=msg)
  elif nargs == '?':
    return '[{msg}]'.format(msg=msg)
  else:
    return msg


def FlagGroupSortKey(flags):
  """Returns a flag group sort key for sorted().

  This orders individual flags before mutually exclusive groups.

  Args:
    flags: A list of flags in the group.

  Returns:
    A sort key for the sorted() builtin where singletons sort before groups.
  """
  return [len(flags) > 1] + sorted([flag.option_strings for flag in flags])


def GetFlagMetavar(name, metavar, flag):
  separator = '=' if name.startswith('--') else ' '
  if isinstance(flag.type, arg_parsers.ArgList):
    msg = flag.type.GetUsageMsg(bool(flag.metavar), metavar)
    return separator + msg
  if metavar == ' ':
    return ''
  return separator + metavar


def _GetInvertedFlagName(flag):
  """Returns the inverted flag name for flag."""
  return flag.option_strings[0].replace('--', '--no-', 1)


def GetArgDetails(arg):
  """Returns the help message with autogenerated details for arg."""
  help_message = arg.help() if callable(arg.help) else arg.help
  help_message = textwrap.dedent(help_message) if help_message else ''
  if IsSuppressed(arg):
    return help_message
  positional = False
  if (not arg.option_strings or
      not arg.option_strings[0].startswith('-') or
      arg.metavar == ' '):
    choices = None
    positional = True
  elif arg.choices:
    choices = arg.choices
  else:
    try:
      choices = arg.type.choices
    except AttributeError:
      choices = None
  extra_help = []
  if choices:
    metavar = arg.metavar or arg.dest.upper()
    choices = getattr(arg, 'choices_help', choices)
    if len(choices) > 1:
      one_of = 'one of'
    else:
      # TBD I guess?
      one_of = '(currently only one value is supported)'
    if isinstance(choices, dict):
      extra_help.append(
          '_{metavar}_ must be {one_of}:\n\n{choices}\n\n'.format(
              metavar=metavar,
              one_of=one_of,
              choices='\n'.join(
                  ['*{name}*::: {desc}'.format(name=name, desc=desc)
                   for name, desc in sorted(choices.iteritems())])))
    else:
      extra_help.append('_{metavar}_ must be {one_of}: {choices}.'.format(
          metavar=metavar,
          one_of=one_of,
          choices=', '.join(['*{0}*'.format(x) for x in choices])))
  elif hasattr(arg, 'store_property'):
    prop, _, _ = arg.store_property
    # Don't add help if there's already explicit help.
    if str(prop) not in help_message:
      extra_help.append('Overrides the default *{0}* property value'
                        ' for this command invocation.'.format(prop))
      # '?' in Boolean flag check to cover legacy choices={'true', 'false'}
      # flags. They are the only flags with nargs='?'. This would have been
      # much easier if argparse had a first class Boolean flag attribute.
      if prop.default and arg.nargs in (0, '?'):
        extra_help.append('Use *{}* to disable.'.format(
            _GetInvertedFlagName(arg)))
  elif arg.nargs or positional:
    # Not a Boolean flag.
    pass
  elif arg.default is True:
    extra_help.append(
        'Enabled by default, use *{0}* to disable.'.format(
            _GetInvertedFlagName(arg)))

  if extra_help:
    help_message = help_message.rstrip()
    if help_message:
      extra_help_message = ' '.join(extra_help)
      newline_index = help_message.rfind('\n')
      if newline_index >= 0 and help_message[newline_index + 1] == ' ':
        # Preserve example markdown at end of help_message.
        help_message += '\n\n' + extra_help_message + '\n'
      else:
        if not help_message.endswith('.'):
          help_message += '.'
        if help_message.rfind('\n\n') > 0:
          # help_message has multiple paragraphs. Put extra_help in a new
          # paragraph.
          help_message += '\n\n'
        else:
          help_message += ' '
        help_message += extra_help_message
  return help_message.replace('\n\n', '\n+\n').strip()


def _ApplyMarkdownItalic(msg):
  return re.sub(r'(\b[a-zA-Z][-a-zA-Z_0-9]*)',
                base.MARKDOWN_ITALIC + r'\1' + base.MARKDOWN_ITALIC, msg)


def PositionalDisplayString(arg, markdown=False):
  """Create the display help string for a positional arg.

  Args:
    arg: argparse.Argument, The argument object to be displayed.
    markdown: bool, If true add markdowns.

  Returns:
    str, The string representation for printing.
  """
  msg = arg.metavar or arg.dest.upper()
  if markdown:
    msg = _ApplyMarkdownItalic(msg)
  return WrapMessageInNargs(msg, arg.nargs)


def FlagDisplayString(arg, brief=False, markdown=False, inverted=False):
  """Create the display help string for a flag arg.

  Args:
    arg: argparse.Argument, The argument object to be displayed.
    brief: bool, If true, only display one version of a flag that has
        multiple versions, and do not display the default value.
    markdown: bool, If true add markdowns.
    inverted: bool, If true display the --no-* inverted name.

  Returns:
    str, The string representation for printing.
  """
  if inverted:
    names = [x.replace('--', '--no-', 1) for x in sorted(arg.option_strings)]
  else:
    names = sorted(arg.option_strings)
  metavar = arg.metavar or arg.dest.upper()
  if brief:
    long_name = names[0]
    if arg.nargs == 0:
      return long_name
    return '{flag}{metavar}'.format(
        flag=long_name,
        metavar=GetFlagMetavar(long_name, metavar, arg))
  if arg.nargs == 0:
    if markdown:
      display_string = ', '.join(
          [base.MARKDOWN_BOLD + x + base.MARKDOWN_BOLD for x in names])
    else:
      display_string = ', '.join(names)
  else:
    display_list = []
    for name in names:
      flag_metavar = GetFlagMetavar(name, metavar, arg)
      if markdown:
        flag_metavar = _ApplyMarkdownItalic(flag_metavar)
      display_list.append(
          '{bb}{flag}{be}{flag_metavar}'.format(
              bb=base.MARKDOWN_BOLD if markdown else '',
              flag=name,
              be=base.MARKDOWN_BOLD if markdown else '',
              flag_metavar=flag_metavar))
    display_string = ', '.join(display_list)
    if not arg.required and arg.default:
      if isinstance(arg.default, list):
        default = ','.join(arg.default)
      elif isinstance(arg.default, dict):
        default = ','.join(['{0}={1}'.format(k, v)
                            for k, v in sorted(arg.default.iteritems())])
      else:
        default = arg.default
      display_string += '; default="{0}"'.format(default)
  return display_string


def WrapWithPrefix(prefix, message, indent, length, spacing,
                   writer=sys.stdout):
  """Helper function that does two-column writing.

  If the first column is too long, the second column begins on the next line.

  Args:
    prefix: str, Text for the first column.
    message: str, Text for the second column.
    indent: int, Width of the first column.
    length: int, Width of both columns, added together.
    spacing: str, Space to put on the front of prefix.
    writer: file-like, Receiver of the written output.
  """
  def W(s):
    writer.write(s)
  def Wln(s):
    W(s + '\n')

  # Reformat the message to be of rows of the correct width, which is what's
  # left-over from length when you subtract indent. The first line also needs
  # to begin with the indent, but that will be taken care of conditionally.
  message = ('\n%%%ds' % indent % ' ').join(
      textwrap.TextWrapper(break_on_hyphens=False, width=length - indent).wrap(
          message.replace(' | ', '&| '))).replace('&|', ' |')
  if len(prefix) > indent - len(spacing) - 2:
    # If the prefix is too long to fit in the indent width, start the message
    # on a new line after writing the prefix by itself.
    Wln('%s%s' % (spacing, prefix))
    # The message needs to have the first line indented properly.
    W('%%%ds' % indent % ' ')
    Wln(message)
  else:
    # If the prefix fits comfortably within the indent (2 spaces left-over),
    # print it out and start the message after adding enough whitespace to make
    # up the rest of the indent.
    W('%s%s' % (spacing, prefix))
    Wln('%%%ds %%s'
        % (indent - len(prefix) - len(spacing) - 1)
        % (' ', message))


def TextIfExists(title, messages):
  """Generates the text for the given section.

  This printing is done by collecting a list of rows. If the row is just a
  string, that means print it without decoration. If the row is a tuple, use
  WrapWithPrefix to print that tuple in aligned columns.

  Args:
    title: str, The name of this section.
    messages: str or [(str, str)], The item or items to print in this section.

  Returns:
    str, The generated text.
  """
  if not messages:
    return None
  textbuf = StringIO.StringIO()
  textbuf.write('%s\n' % title)
  if isinstance(messages, str):
    textbuf.write('  ' + messages + '\n')
  else:
    for (arg, helptxt) in messages:
      WrapWithPrefix(arg, helptxt, HELP_INDENT, LINE_WIDTH,
                     spacing='  ', writer=textbuf)
  return textbuf.getvalue()


def GetUsage(command, argument_interceptor):
  """Return the command Usage string.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.
    argument_interceptor: calliope._ArgumentInterceptor, the object that tracks
        all of the flags for this command or group.

  Returns:
    str, The command usage string.
  """
  command.LoadAllSubElements()
  topic = len(command.GetPath()) >= 2 and command.GetPath()[1] == 'topic'

  buf = StringIO.StringIO()

  buf.write('Usage: ')

  command_path = ' '.join(command.GetPath())
  command_id = 'topic' if topic else 'command'
  usage_parts = [command_path]
  optional_flags = []

  if not topic:
    # Do positional args first, since flag args taking lists can mess them
    # up otherwise.
    # Explicitly not sorting here - order matters.
    # Make a copy, and we'll pop items off. Once we get to a REMAINDER, that
    # goes after the flags so we'll stop and finish later.
    positional_args = FilterOutSuppressed(
        argument_interceptor.positional_args[:])
    while positional_args:
      arg = positional_args[0]
      if arg.nargs == argparse.REMAINDER:
        break
      positional_args.pop(0)
      usage_parts.append(PositionalDisplayString(arg))

    flag_messages = []
    for arg in argument_interceptor.flag_args:
      if IsSuppressed(arg):
        continue
      if not arg.required:
        if arg.option_strings:
          optional_flags.append(sorted(arg.option_strings)[0])
        continue
      # and add it to the usage
      msg = FlagDisplayString(arg, brief=True)
      flag_messages.append(msg)
    usage_parts.extend(sorted(flag_messages))

    if optional_flags:
      # If there are any optional flags, add a simple message to the usage.
      usage_parts.append('[optional flags]')

    # positional_args will only be non-empty if we had some REMAINDER left.
    for arg in positional_args:
      usage_parts.append(PositionalDisplayString(arg))

  group_helps = command.GetSubGroupHelps()
  command_helps = command.GetSubCommandHelps()

  groups = sorted([name for (name, help_info) in group_helps.iteritems()
                   if command.IsHidden() or not help_info.is_hidden])
  commands = sorted([name for (name, help_info) in command_helps.iteritems()
                     if command.IsHidden() or not help_info.is_hidden])

  all_subtypes = []
  if groups:
    all_subtypes.append('group')
  if commands:
    all_subtypes.append(command_id)
  if groups or commands:
    usage_parts.append('<%s>' % ' | '.join(all_subtypes))
    optional_flags = None

  buf.write(' '.join(usage_parts) + '\n')

  if groups:
    WrapWithPrefix('group may be', ' | '.join(groups),
                   HELP_INDENT, LINE_WIDTH, spacing='  ', writer=buf)
  if commands:
    WrapWithPrefix('%s may be' % command_id, ' | '.join(commands),
                   HELP_INDENT, LINE_WIDTH, spacing='  ', writer=buf)
  if optional_flags:
    WrapWithPrefix('optional flags may be', ' | '.join(sorted(optional_flags)),
                   HELP_INDENT, LINE_WIDTH, spacing='  ', writer=buf)

  buf.write("""
For detailed information on this command and its flags, run:
  {command_path} --help
""".format(command_path=' '.join(command.GetPath())))

  return buf.getvalue()


def ExtractHelpStrings(docstring):
  """Extracts short help and long help from a docstring.

  If the docstring contains a blank line (i.e., a line consisting of zero or
  more spaces), everything before the first blank line is taken as the short
  help string and everything after it is taken as the long help string. The
  short help is flowing text with no line breaks, while the long help may
  consist of multiple lines, each line beginning with an amount of whitespace
  determined by dedenting the docstring.

  If the docstring does not contain a blank line, the sequence of words in the
  docstring is used as both the short help and the long help.

  Corner cases: If the first line of the docstring is empty, everything
  following it forms the long help, and the sequence of words of in the long
  help (without line breaks) is used as the short help. If the short help
  consists of zero or more spaces, None is used instead. If the long help
  consists of zero or more spaces, the short help (which might or might not be
  None) is used instead.

  Args:
    docstring: The docstring from which short and long help are to be taken

  Returns:
    a tuple consisting of a short help string and a long help string

  """
  if docstring:
    unstripped_doc_lines = docstring.splitlines()
    stripped_doc_lines = [s.strip() for s in unstripped_doc_lines]
    try:
      empty_line_index = stripped_doc_lines.index('')
      short_help = ' '.join(stripped_doc_lines[:empty_line_index])
      raw_long_help = '\n'.join(unstripped_doc_lines[empty_line_index + 1:])
      long_help = textwrap.dedent(raw_long_help).strip()
    except ValueError:  # no empty line in stripped_doc_lines
      short_help = ' '.join(stripped_doc_lines).strip()
      long_help = ''
    if not short_help:  # docstring started with a blank line
      short_help = ' '.join(stripped_doc_lines[empty_line_index + 1:]).strip()
      # words of long help as flowing text
    return (short_help, long_help or short_help)
  else:
    return ('', '')
