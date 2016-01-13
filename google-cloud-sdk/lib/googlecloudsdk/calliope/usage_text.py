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
import re
import StringIO
import sys
import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core.console import console_io

LINE_WIDTH = 80
HELP_INDENT = 25

MARKDOWN_BOLD = '*'
MARKDOWN_ITALIC = '_'
MARKDOWN_CODE = '`'


def FilterOutSuppressed(args):
  """Returns a copy of args containing only non-suppressed arguments."""
  return [a for a in args if a.help != argparse.SUPPRESS]


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


class CommandChoiceSuggester(object):
  """Utility to suggest mistyped commands.

  """
  TEST_QUOTA = 5000
  MAX_DISTANCE = 5
  _SYNONYM_SETS = [
      set(['create', 'add']),
      set(['delete', 'remove']),
      set(['describe', 'get']),
      set(['patch', 'update']),
  ]

  def __init__(self, choices=None):
    self.cache = {}
    self.inf = float('inf')
    self._quota = self.TEST_QUOTA
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
    for s_set in CommandChoiceSuggester._SYNONYM_SETS:
      valid_choices = set(self._choices.keys()) & s_set
      for choice in valid_choices:
        # Add all synonyms in the set as aliases for each real choice that is
        # valid.  This will never clobber the original choice that is there.
        # If none of the synonyms are valid choices, this will not add any
        # aliases for this synonym set.
        self.AddAliases(s_set, choice)

  def _Deletions(self, s):
    return [s[:i] + s[i + 1:] for i in range(len(s))]

  def _GetDistance(self, longer, shorter):
    """Get the edit distance between two words.

    They must be in the correct order, since deletions and mutations only happen
    from 'longer'.

    Args:
      longer: str, The longer of the two words.
      shorter: str, The shorter of the two words.

    Returns:
      int, The number of substitutions or deletions on longer required to get
      to shorter.
    """

    if longer == shorter:
      return 0

    try:
      return self.cache[(longer, shorter)]
    except KeyError:
      pass

    self.cache[(longer, shorter)] = self.inf
    best_distance = self.inf

    if len(longer) > len(shorter):
      if self._quota < 0:
        return self.inf
      self._quota -= 1
      for m in self._Deletions(longer):
        best_distance = min(best_distance, self._GetDistance(m, shorter) + 1)

    if len(longer) == len(shorter):
      # just count how many letters differ
      best_distance = 0
      for i in range(len(longer)):
        if longer[i] != shorter[i]:
          best_distance += 1

    self.cache[(longer, shorter)] = best_distance
    return best_distance

  def GetSuggestion(self, arg):
    """Find the item that is closest to what was attempted.

    Args:
      arg: str, The argument provided.

    Returns:
      str, The closest match.
    """

    min_distance = self.inf
    bestchoice = None
    for choice in self._choices:
      self._quota = self.TEST_QUOTA
      first, second = arg, choice
      if len(first) < len(second):
        first, second = second, first
      if len(first) - len(second) > self.MAX_DISTANCE:
        # Don't bother if they're too different.
        continue
      d = self._GetDistance(first.lower(), second.lower())
      if d < min_distance:
        min_distance = d
        bestchoice = choice

    if not bestchoice:
      return None
    # MAX_DISTANCE doesn't work very well for shorter strings (two strings of
    # length n can have edit distance of at most n); any length-4 string will
    # match any length-3 or length-4 string with MAX_DISTANCE 5, which is
    # confusing. This trick prevents that.
    if min_distance > min(self.MAX_DISTANCE, len(bestchoice) - 1, len(arg) - 1):
      return None

    # Return the suggestion for the best choice.
    return self._choices[bestchoice]


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
  elif nargs == '*' or nargs == argparse.REMAINDER:
    return '[{msg} ...]'.format(msg=msg)
  elif nargs == '?':
    return '[{msg}]'.format(msg=msg)
  else:
    return msg


def GetFlagMetavar(metavar, flag):
  if isinstance(flag.type, arg_parsers.ArgList):
    msg = '[{metavar},...]'.format(metavar=metavar)
    if flag.type.min_length:
      msg = ','.join([metavar]*flag.type.min_length+[msg])
    return ' ' + msg
  if metavar == ' ':
    return ''
  return ' ' + metavar


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
    msg = re.sub(r'(\b[a-zA-Z][-a-zA-Z_0-9]*)',
                 MARKDOWN_ITALIC + r'\1' + MARKDOWN_ITALIC, msg)
  return ' ' + WrapMessageInNargs(msg, arg.nargs)


def FlagDisplayString(arg, brief=False, markdown=False):
  """Create the display help string for a flag arg.

  Args:
    arg: argparse.Argument, The argument object to be displayed.
    brief: bool, If true, only display one version of a flag that has
        multiple versions, and do not display the default value.
    markdown: bool, If true add markdowns.

  Returns:
    str, The string representation for printing.
  """
  metavar = arg.metavar or arg.dest.upper()
  if brief:
    long_string = sorted(arg.option_strings)[0]
    if arg.nargs == 0:
      return long_string
    return '{flag}{metavar}'.format(
        flag=long_string,
        metavar=GetFlagMetavar(metavar, arg))
  if arg.nargs == 0:
    if markdown:
      display_string = ', '.join([MARKDOWN_BOLD + x + MARKDOWN_BOLD
                                  for x in arg.option_strings])
    else:
      display_string = ', '.join(arg.option_strings)
  else:
    if markdown:
      metavar = re.sub('(\\b[a-zA-Z][-a-zA-Z_0-9]*)',
                       MARKDOWN_ITALIC + '\\1' + MARKDOWN_ITALIC, metavar)
    display_string = ', '.join(
        ['{bb}{flag}{be}{metavar}'.format(
            bb=MARKDOWN_BOLD if markdown else '',
            flag=option_string,
            be=MARKDOWN_BOLD if markdown else '',
            metavar=GetFlagMetavar(metavar, arg))
         for option_string in arg.option_strings])
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
      textwrap.wrap(message, length - indent))
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


def GenerateUsage(command, argument_interceptor, topic=False):
  """Generate a usage string for a calliope command, group or help topic.

  Args:
    command: calliope._CommandCommon, The command, group or help topic object
      that we're generating usage for.
    argument_interceptor: calliope._ArgumentInterceptor, the object that tracks
        all of the flags for this command or group.
    topic: True if this is a supplementary help topic command.

  Returns:
    str, The usage string.
  """
  command.LoadAllSubElements()

  buf = StringIO.StringIO()

  command_path = ' '.join(command.GetPath())
  command_id = 'topic' if topic else 'command'
  usage_parts = []

  optional_messages = False

  flag_messages = []

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

    for arg in argument_interceptor.flag_args:
      if arg.help == argparse.SUPPRESS:
        continue
      if not arg.required:
        optional_messages = True
        continue
      # and add it to the usage
      msg = FlagDisplayString(arg, brief=True)
      flag_messages.append(msg)
    usage_parts.extend(sorted(flag_messages))

    if optional_messages:
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

  usage_msg = ' '.join(usage_parts)

  non_option = '{command} '.format(command=command_path)

  buf.write(non_option + usage_msg + '\n')

  if groups:
    WrapWithPrefix('group may be', ' | '.join(
        groups), HELP_INDENT, LINE_WIDTH, spacing='  ', writer=buf)
  if commands:
    WrapWithPrefix('%s may be' % command_id, ' | '.join(
        commands), HELP_INDENT, LINE_WIDTH, spacing='  ', writer=buf)
  return buf.getvalue()


def ExpandHelpText(command, text):
  """Expand command {...} references in text.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.
    text: str, The text chunk to expand.

  Returns:
    str, The expanded help text.
  """
  if text == command.long_help:
    long_help = ''
  else:
    long_help = ExpandHelpText(command, command.long_help)
  path = command.GetPath()
  return console_io.LazyFormat(
      text or '',
      command=' '.join(path),
      man_name='_'.join(path),
      top_command=path[0],
      parent_command=' '.join(path[:-1]),
      index=command.short_help,
      description=long_help)


def ShortHelpText(command, argument_interceptor):
  """Get a command's short help text.

  Args:
    command: calliope._CommandCommon, The command object that we're helping.
    argument_interceptor: calliope._ArgumentInterceptor, the object that tracks
        all of the flags for this command or group.

  Returns:
    str, The short help text.
  """
  command.LoadAllSubElements()

  topic = len(command.GetPath()) >= 2 and command.GetPath()[1] == 'topic'

  buf = StringIO.StringIO()

  required_messages = []
  common_messages = []
  optional_messages = []
  has_global_flags = False

  # Sorting for consistency and readability.
  for arg in (argument_interceptor.flag_args +
              argument_interceptor.ancestor_flag_args):
    if arg.help == argparse.SUPPRESS:
      continue
    message = (FlagDisplayString(arg), arg.help or '')
    if arg.is_global and not command.IsRoot():
      has_global_flags = True
    elif arg.required:
      required_messages.append(message)
    elif arg.is_common:
      common_messages.append(message)
    else:
      optional_messages.append(message)

  positional_messages = []

  # Explicitly not sorting here - order matters.
  display_positionals = FilterOutSuppressed(
      argument_interceptor.positional_args)
  for arg in display_positionals:
    positional_messages.append(
        (PositionalDisplayString(arg), arg.help or ''))

  group_helps = command.GetSubGroupHelps()
  command_helps = command.GetSubCommandHelps()

  group_messages = [(name, help_info.help_text) for (name, help_info)
                    in group_helps.iteritems()
                    if command.IsHidden() or not help_info.is_hidden]
  command_messages = [(name, help_info.help_text) for (name, help_info)
                      in command_helps.iteritems()
                      if command.IsHidden() or not help_info.is_hidden]

  buf.write('Usage: ' + GenerateUsage(command, argument_interceptor, topic) +
            '\n')

  # Second, print out the long help.

  buf.write('\n'.join(textwrap.wrap(ExpandHelpText(command, command.long_help),
                                    LINE_WIDTH)))
  buf.write('\n\n')

  # Third, print out the short help for everything that can come on
  # the command line, grouped into required flags, optional flags,
  # sub groups, sub commands, and positional arguments.

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
    if type(messages) == str:
      textbuf.write('  ' + messages + '\n')
    else:
      for (arg, helptxt) in messages:
        WrapWithPrefix(arg, helptxt, HELP_INDENT, LINE_WIDTH,
                       spacing='  ', writer=textbuf)
    return textbuf.getvalue()

  if topic:
    all_messages = [
        TextIfExists('topics:', sorted(command_messages)),
    ]
  else:
    all_messages = [
        TextIfExists('positional arguments:', positional_messages),
        TextIfExists('required flags:', sorted(required_messages)),
    ]

    # If this command has flags tagged as common, only show those flags, and
    # print a message to use the long help to see all the flags (if there are
    # others).
    if common_messages:
      all_messages.append(
          TextIfExists('commonly used flags:', sorted(common_messages)))
      command_path = ' '.join(command.GetPath())
      if optional_messages:
        all_messages.append(
            TextIfExists(
                'other flags:',
                'Run: `{0} --help`\n  for the full list of available flags for '
                'this command.'.format(command_path)))
    # If nothing tagged as common, just display all the optional flags as we
    # normally do.
    else:
      optional_flags_tag = 'optional flags:' if required_messages else 'flags:'
      all_messages.append(
          TextIfExists(optional_flags_tag, sorted(optional_messages)))

    if has_global_flags:
      root_command_name = command.GetPath()[0]
      all_messages.append(
          TextIfExists(
              'global flags:',
              'Run `{0} -h` for a description of flags available to all '
              'commands.'.format(root_command_name)))

    all_messages.extend([
        TextIfExists('command groups:', sorted(group_messages)),
        TextIfExists('commands:', sorted(command_messages)),
    ])
  buf.write('\n'.join([msg for msg in all_messages if msg]))

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
