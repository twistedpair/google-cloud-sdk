# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Help document markdown helpers."""

import argparse
import re
import StringIO
import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.third_party.py27 import py27_collections as collections


class Error(Exception):
  """Exceptions for the markdown module."""


_SPLIT = 78  # Split lines longer than this.
_SECTION_INDENT = 8  # Section or list within section indent.
_FIRST_INDENT = 2  # First line indent.
_SUBSEQUENT_INDENT = 6  # Subsequent line indent.


class ExampleCommandLineSplitter(object):
  """Example command line splitter.

  Attributes:
    max_index: int, The max index to check in line.
    quote_char: str, The current quote char for quotes split across lines.
    quote_index: int, The index of quote_char in line or 0 if in previous line.
  """

  def __init__(self):
    self._max_index = _SPLIT - _SECTION_INDENT - _FIRST_INDENT
    self._quote_char = None
    self._quote_index = 0

  def _SplitInTwo(self, line):
    """Splits line into before and after, len(before) < self._max_index.

    Args:
      line: str, The line to split.

    Returns:
      (before, after)
        The line split into two parts. <before> is a list of strings that forms
        the first line of the split and <after> is a string containing the
        remainder of the line to split. The display width of <before> is
        < self._max_index. <before> contains the separator chars, including a
        newline.
    """
    punct_index = 0
    quoted_space_index = 0
    quoted_space_quote = None
    space_index = 0
    space_flag = False
    i = 0
    while i < self._max_index:
      c = line[i]
      i += 1
      if c == self._quote_char:
        self._quote_char = None
      elif self._quote_char:
        if c == ' ':
          quoted_space_index = i - 1
          quoted_space_quote = self._quote_char
      elif c in ('"', "'"):
        self._quote_char = c
        self._quote_index = i
        quoted_space_index = 0
      elif c == '\\':
        i += 1
      elif i < self._max_index:
        if c == ' ':
          # Split before a flag instead of the next arg; it could be the flag
          # value.
          if line[i] == '-':
            space_flag = True
            space_index = i
          elif space_flag:
            space_flag = False
          else:
            space_index = i
        elif c in (',', ';', '/', '|'):
          punct_index = i
        elif c == '=':
          space_flag = False
    separator = '\\\n'
    indent = _FIRST_INDENT
    if space_index:
      split_index = space_index
      indent = _SUBSEQUENT_INDENT
    elif quoted_space_index:
      split_index = quoted_space_index
      if quoted_space_quote == "'":
        separator = '\n'
    elif punct_index:
      split_index = punct_index
    else:
      split_index = self._max_index
    if split_index <= self._quote_index:
      self._quote_char = None
    else:
      self._quote_index = 0
    self._max_index = _SPLIT - _SECTION_INDENT - indent
    return [line[:split_index], separator, ' ' * indent], line[split_index:]

  def Split(self, line):
    """Splits a long example command line by inserting newlines.

    Args:
      line: str, The command line to split.

    Returns:
      str, The command line with newlines inserted.
    """
    lines = []
    while len(line) > self._max_index:
      before, line = self._SplitInTwo(line)
      lines.extend(before)
    lines.append(line)
    return ''.join(lines)


class MarkdownGenerator(object):
  """Command help markdown document generator.

  Attributes:
    _buf: Output document stream.
    _command: The CommandCommon instance for command.
    _command_name: The command name string.
    _command_path: Command path.
    _description: The long_help description markdown.
    _detailed_help: Command detailed help dict indexed by SECTION name.
    _doc: The output markdown document string.
    _file_name: The command path name (used to name documents).
    _is_top_element: True if command is the top CLI element.
    _is_topic: True if the command is a help topic.
    _out: Output writer.
    _printed_sections: The set of already printed sections.
    _top_element: The top CLI element.
    _track: The Command release track prefix.
    _subcommand: The list of subcommand instances or None.
    _subgroup: The list of subgroup instances or None.
  """

  def __init__(self, command):
    """Constructor.

    Args:
      command: calliope._CommandCommon, Help extracted from this calliope
        command, group or topic.
    """
    command.LoadAllSubElements()
    self._command = command
    self._buf = StringIO.StringIO()
    self._out = self._buf.write
    self._description = ''
    self._detailed_help = getattr(command, 'detailed_help', {})
    self._command_path = command.GetPath()
    self._command_name = ' '.join(self._command_path)
    self._file_name = '_'.join(self._command_path)
    self._track = command.ReleaseTrack().prefix
    command_index = (2 if self._track and len(self._command_path) >= 3 and
                     self._command_path[1] == self._track else 1)
    self._is_topic = (len(self._command_path) >= (command_index + 1) and
                      self._command_path[command_index] == 'topic')
    # pylint: disable=protected-access
    self._top_element = command._TopCLIElement()
    self._is_top_element = command.IsRoot()
    self._printed_sections = set()
    self._subcommands = command.GetSubCommandHelps()
    self._subgroups = command.GetSubGroupHelps()

  def _SplitCommandFromArgs(self, cmd):
    """Splits cmd into command and args lists.

    The command list part is a valid command and the args list part is the
    trailing args.

    Args:
      cmd: [str], A command + args list.

    Returns:
      (command, args): The command and args lists.
    """
    # The bare top level command always works.
    if len(cmd) <= 1:
      return cmd, []
    # Skip the top level command name.
    prefix = 1
    i = prefix + 1
    while i <= len(cmd):
      if not self._top_element.IsValidSubPath(cmd[prefix:i]):
        i -= 1
        break
      i += 1
    return cmd[:i], cmd[i:]

  def _UserInput(self, msg):
    """Returns msg with user input markdown.

    Args:
      msg: str, The user input string.

    Returns:
      The msg string with embedded user input markdown.
    """
    return (base.MARKDOWN_CODE + base.MARKDOWN_ITALIC +
            msg +
            base.MARKDOWN_ITALIC + base.MARKDOWN_CODE)

  def _Section(self, name, sep=True):
    """Prints the section header markdown for name.

    Args:
      name: str, The manpage section name.
      sep: boolean, Add trailing newline.
    """
    self._printed_sections.add(name)
    self._out('\n\n## {name}\n'.format(name=name))
    if sep:
      self._out('\n')

  def _PrintSynopsisSection(self):
    """Prints the command line synopsis section."""
    # MARKDOWN_CODE is the default SYNOPSIS font style.
    code = base.MARKDOWN_CODE
    em = base.MARKDOWN_ITALIC
    self._Section('SYNOPSIS')
    self._out('{code}{command}{code}'.format(code=code,
                                             command=self._command_name))

    # Output the positional args up to the first REMAINDER or '-- *' args. The
    # rest will be picked up after the flag args are output. argparse does not
    # have an explicit '--' arg intercept, so we use the metavar value as a '--'
    # sentinel. Any suppressed args are ingnored by a pre-pass.
    positional_args = usage_text.FilterOutSuppressed(
        self._command.ai.positional_args)
    while positional_args:
      arg = positional_args[0]
      if arg.nargs == argparse.REMAINDER or arg.metavar.startswith('-- '):
        break
      positional_args.pop(0)
      self._out(usage_text.PositionalDisplayString(arg, markdown=True))

    if self._subcommands and self._subgroups:
      self._out(' ' + em + 'GROUP' + em + ' | ' + em + 'COMMAND' + em)
    elif self._subcommands:
      self._out(' ' + em + 'COMMAND' + em)
    elif self._subgroups:
      self._out(' ' + em + 'GROUP' + em)

    # Place all flags into a dict. Flags that are in a mutually
    # exclusive group are mapped group_id -> [flags]. All other flags
    # are mapped dest -> [flag].
    global_flags = False
    groups = collections.defaultdict(list)
    for flag in (self._command.ai.flag_args +
                 self._command.ai.ancestor_flag_args):
      if flag.is_global and not self._is_top_element:
        global_flags = True
      else:
        group_id = self._command.ai.mutex_groups.get(flag.dest, flag.dest)
        groups[group_id].append(flag)

    # Partition the non-GLOBAL flag groups dict into categorized sections. A
    # group is REQUIRED if any flag in it is required, categorized if any flag
    # in it is categorized, otherwise its OTHER.  REQUIRED takes precedence
    # over categorized.
    categorized_groups = {}
    for group_id, flags in groups.iteritems():
      for f in flags:
        if f.required:
          category = 'REQUIRED'
        elif f.category:
          category = f.category
        else:
          continue
        if category not in categorized_groups:
          categorized_groups[category] = {}
        categorized_groups[category][group_id] = flags
        break
    # Delete the categorized groups to get OTHER.
    for v in categorized_groups.values():
      for g in v:
        del groups[g]
    category = 'OTHER'
    if category not in categorized_groups:
      categorized_groups[category] = {}
    for group_id, flags in groups.iteritems():
      categorized_groups[category][group_id] = flags

    # Collect the sections in order: REQUIRED, COMMON, OTHER, and categorized.
    sections = []
    for category in ('REQUIRED', base.COMMONLY_USED_FLAGS, 'OTHER'):
      if category in categorized_groups:
        sections.append(categorized_groups[category])
        del categorized_groups[category]
    for _, v in sorted(categorized_groups.iteritems()):
      sections.append(v)

    # Generate the flag usage string with flags in section order.
    for section in sections:
      for group in sorted(section.values(), key=lambda g: g[0].option_strings):
        if len(group) == 1:
          arg = group[0]
          if usage_text.IsSuppressed(arg):
            continue
          msg = usage_text.FlagDisplayString(arg, markdown=True)
          if not msg:
            continue
          if arg.required:
            self._out(' {msg}'.format(msg=msg))
          else:
            self._out(' [{msg}]'.format(msg=msg))
        else:
          # Check if the inverted boolean name should be displayed.
          inverted = None
          if len(group) == 2:
            for arg in group:
              if getattr(arg, 'show_inverted', False):
                inverted = arg
                break
          if inverted:
            # The inverted arg replaces the boolean group which only contains
            # the arg and inverted arg.
            msg = usage_text.FlagDisplayString(inverted, markdown=True)
          else:
            group = usage_text.FilterOutSuppressed(group)
            group.sort(key=lambda f: f.option_strings)
            msg = ' | '.join(usage_text.FlagDisplayString(arg, markdown=True)
                             for arg in group)
          if not msg:
            continue
          self._out(' [{msg}]'.format(msg=msg))

    if global_flags:
      self._out(' [' + em + 'GLOBAL-FLAG ...' + em + ']')

    # positional_args will only be non-empty if we had -- ... or REMAINDER left.
    for arg in usage_text.FilterOutSuppressed(positional_args):
      self._out(usage_text.PositionalDisplayString(arg, markdown=True))

    self._out('\n')

  def _PrintFlagSection(self, section, flags):
    self._Section(section, sep=False)
    for flag in sorted(flags, key=lambda f: f.option_strings):
      self._out('\n{0}::\n'.format(
          usage_text.FlagDisplayString(flag, markdown=True)))
      self._out('\n{arghelp}\n'.format(arghelp=self._Details(flag)))

  def _PrintPositionalsAndFlagsSections(self):
    """Prints the positionals and flags sections."""
    visible_positionals = usage_text.FilterOutSuppressed(
        self._command.ai.positional_args)
    if visible_positionals:
      self._Section('POSITIONAL ARGUMENTS', sep=False)
      for arg in visible_positionals:
        self._out('\n{0}::\n'.format(
            usage_text.PositionalDisplayString(arg, markdown=True).lstrip()))
        self._out('\n{arghelp}\n'.format(arghelp=self._Details(arg)))

    sections, has_global_flags = usage_text.GetFlagSections(
        self._command, self._command.ai)

    # List the sections in order.
    for section, _, flags in sections:
      self._PrintFlagSection(section, flags)

    if has_global_flags:
      self._Section('GLOBAL FLAGS', sep=False)
      self._out('\nRun *$ gcloud help* for a description of flags available to'
                '\nall commands.\n')

  def _PrintSectionIfExists(self, name, default=None):
    """Print a section of the .help file, from a part of the detailed_help.

    Args:
      name: str, The manpage section name.
      default: str, Default help_stuff if section name is not defined.
    """
    if name in self._printed_sections:
      return
    help_stuff = self._detailed_help.get(name, default)
    if not help_stuff:
      return
    if callable(help_stuff):
      help_message = help_stuff()
    else:
      help_message = help_stuff
    self._Section(name)
    self._out('{message}\n'.format(
        message=textwrap.dedent(help_message).strip()))

  def _PrintAllExtraSections(self, excluded_sections):
    """Print all extra man page sections.

    Args:
      excluded_sections: A list of section names to exclude. These will be
        printed later.

    Extra sections are _detailed_help sections that have not been printed yet.
    _PrintSectionIfExists() skips sections that have already been printed.
    """
    for section in sorted(self._detailed_help):
      if section.isupper() and section not in excluded_sections:
        self._PrintSectionIfExists(section)

  def _PrintCommandSection(self, name, subcommands, is_topic=False):
    """Prints a group or command section.

    Args:
      name: str, The section name singular form.
      subcommands: dict, The subcommand dict.
      is_topic: bool, True if this is a TOPIC subsection.
    """
    # Determine if the section has any content.
    content = ''
    for subcommand, help_info in sorted(subcommands.iteritems()):
      if self._command.IsHidden() or not help_info.is_hidden:
        # If this group is already hidden, we can safely include hidden
        # sub-items.  Else, only include them if they are not hidden.
        content += '\n*link:{ref}[{cmd}]*::\n\n{txt}\n'.format(
            ref='/'.join(self._command_path + [subcommand]),
            cmd=subcommand,
            txt=help_info.help_text)
    if content:
      self._Section(name + 'S')
      if is_topic:
        self._out('The supplementary help topics are:\n')
      else:
        self._out('{cmd} is one of the following:\n'.format(
            cmd=self._UserInput(name)))
      self._out(content)

  def _PrintNotesSection(self):
    """Prints the NOTES section if needed."""
    if (self._command.IsHidden() or
        self._command.ReleaseTrack().help_note):
      self._Section('NOTES')
      if self._command.IsHidden():
        self._out('This command is an internal implementation detail and may'
                  ' change or disappear without notice.\n\n')
      if self._command.ReleaseTrack().help_note:
        self._out(self._command.ReleaseTrack().help_note + '\n\n')

  def _Details(self, arg):
    """Returns the detailed help message for the given arg."""
    help_stuff = getattr(arg, 'detailed_help', (arg.help or '') + '\n')
    help_message = help_stuff() if callable(help_stuff) else help_stuff
    # calliope.backend.ArgumentInterceptor.add_argument() sets arg.inverted_help
    # for Boolean flags with auto-generated --no-FLAG inverted counterparts.
    help_message = textwrap.dedent(help_message)
    inverted_help = getattr(arg, 'inverted_help', None)
    if inverted_help:
      help_message = help_message.rstrip()
      if help_message:
        i = help_message.rfind('\n')
        if i >= 0 and help_message[i + 1] == ' ':
          # Preserve example markdown at end of help_message.
          help_message += '\n\n' + inverted_help.strip() + '\n'
        else:
          if not help_message.endswith('.'):
            help_message += '.'
          help_message += inverted_help + '\n'
    return help_message.replace('\n\n', '\n+\n').strip()

  def _ExpandFormatReferences(self):
    """Expand {...} references."""
    self._doc = usage_text.ExpandHelpText(self._command, self._buf.getvalue())

    # Split long $ ... example lines.
    pat = re.compile(r'^ *(\$ .{%d,})$' % (
        _SPLIT - _FIRST_INDENT - _SECTION_INDENT), re.M)
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      rep += (self._doc[pos:match.start(1)] +
              ExampleCommandLineSplitter().Split(
                  self._doc[match.start(1):match.end(1)]))
      pos = match.end(1)
    if rep:
      self._doc = rep + self._doc[pos:]

  def _AddCommandLineLinkMarkdown(self):
    """Add $ command ... link markdown."""
    top = self._command_path[0]
    # This pattern matches "$ {top} {arg}*" where each arg is lower case and
    # does not start with example-, my-, or sample-. This follows the style
    # guide rule that user-supplied args to example commands contain upper case
    # chars or start with example-, my-, or sample-. The trailing .? allows for
    # an optional punctuation character before end of line. This handles cases
    # like ``... run $ gcloud foo bar.'' at the end of a sentence.
    pat = re.compile(r'\$ (' + top +
                     '((?: (?!(example|my|sample)-)[a-z][-a-z0-9]*)*)).?[ `\n]')
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      cmd, args = self._SplitCommandFromArgs(match.group(1).split(' '))
      ref = '/'.join(cmd)
      lnk = 'link:' + ref + '[' + ' '.join(cmd) + ']'
      if args:
        lnk += ' ' + ' '.join(args)
      rep += self._doc[pos:match.start(1)] + lnk
      pos = match.end(1)
    if rep:
      self._doc = rep + self._doc[pos:]

  def _AddManPageLinkMarkdown(self):
    """Add gcloud ...(1) man page link markdown."""
    top = self._command_path[0]
    pat = re.compile(r'(\*?(' + top + r'(?:[-_ a-z])*)\*?)\(1\)')
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      cmd = match.group(2).replace('_', ' ')
      ref = cmd.replace(' ', '/')
      lnk = '*link:' + ref + '[' + cmd + ']*'
      rep += self._doc[pos:match.start(2)] + lnk
      pos = match.end(1)
    if rep:
      self._doc = rep + self._doc[pos:]

  def _FixAirQuotesMarkdown(self):
    """Change ``.*[[:alnum:]]{2,}.*'' emphasis quotes => UserInput(*).

    Double ``air quotes'' on strings with no identifier chars or groups of
    singleton identifier chars are literal. All other double air quote forms
    are converted to unquoted strings with the _UserInput() font embellishment.

    This is a subjective choice for aesthetically pleasing renderings.
    """
    pat = re.compile(r"[^`](``([^`]*\w{2,}[^`']*)'')")
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      rep += self._doc[pos:match.start(1)] + self._UserInput(match.group(2))
      pos = match.end(1)
    if rep:
      self._doc = rep + self._doc[pos:]

  def _SetDetailedHelpSection(self, name, lines):
    """Sets a _detailed_help name or _description section composed of lines.

    Args:
      name: The section name or None for the DESCRIPTION section.
      lines: The list of lines in the section.
    """
    # Strip leading empty lines.
    while lines and not lines[0]:
      lines = lines[1:]
    # Strip trailing empty lines.
    while lines and not lines[-1]:
      lines = lines[:-1]
    if lines:
      if name:
        self._detailed_help[name] = '\n'.join(lines)
      else:
        self._description = '\n'.join(lines)

  def _ExtractDetailedHelp(self):
    """Extracts _detailed_help sections from the command long_help string."""
    name = None  # DESRIPTION
    lines = []
    for line in textwrap.dedent(self._command.long_help).strip().splitlines():
      # '## \n' is not section markdown.
      if len(line) >= 4 and line.startswith('## '):
        self._SetDetailedHelpSection(name, lines)
        name = line[3:]
        lines = []
      else:
        lines.append(line)
    self._SetDetailedHelpSection(name, lines)

  def Generate(self):
    """Generates markdown for the command, group or topic, into a string."""
    self._out('# {0}(1)\n'.format(self._file_name.upper()))
    self._Section('NAME')
    self._out('{{command}} - {index}\n'.format(index=self._command.index_help))
    if not self._is_topic:
      self._PrintSynopsisSection()
    self._ExtractDetailedHelp()
    self._PrintSectionIfExists(
        'DESCRIPTION',
        default=usage_text.ExpandHelpText(self._command, self._description))
    if not self._is_topic:
      self._PrintPositionalsAndFlagsSections()
    if self._subgroups:
      self._PrintCommandSection('GROUP', self._subgroups)
    if self._subcommands:
      if self._is_topic:
        self._PrintCommandSection('TOPIC', self._subcommands, is_topic=True)
      else:
        self._PrintCommandSection('COMMAND', self._subcommands)
    final_sections = ['EXAMPLES', 'SEE ALSO']
    self._PrintAllExtraSections(excluded_sections=final_sections + ['NOTES'])
    for section in final_sections:
      self._PrintSectionIfExists(section)
    self._PrintNotesSection()
    self._doc = self._buf.getvalue()

    # Apply edits to the generated markdown.
    self._ExpandFormatReferences()
    self._AddCommandLineLinkMarkdown()
    self._AddManPageLinkMarkdown()
    self._FixAirQuotesMarkdown()
    return self._doc


def Markdown(command):
  """Generates and returns the help markdown document for command.

  Args:
    command: The CommandCommon command instance.

  Returns:
    The markdown document string.
  """
  return MarkdownGenerator(command).Generate()
