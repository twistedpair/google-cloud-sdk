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

  def _PrintSynopsisSection(self, sections, has_global_flags):
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

    # Generate the flag usage string with flags in section order.
    for _, _, groups, attrs in sections:
      for group_id, group in sorted(
          groups.iteritems(), key=lambda x: usage_text.FlagGroupSortKey(x[1])):
        flag = group[0]
        if len(group) == 1:
          show_inverted = getattr(flag, 'show_inverted', None)
          if show_inverted:
            flag = show_inverted
          msg = usage_text.FlagDisplayString(flag, markdown=True)
          if not msg:
            continue
          if flag.required:
            self._out(' {msg}'.format(msg=msg))
          else:
            self._out(' [{msg}]'.format(msg=msg))
        else:
          group.sort(key=lambda f: f.option_strings)
          attr = attrs.get(group_id)
          if not attr or not attr.is_mutex:
            for flag in group:
              self._out(' [{0}]'.format(
                  usage_text.FlagDisplayString(flag, markdown=True)))
          else:
            msg = ' | '.join(usage_text.FlagDisplayString(flag, markdown=True)
                             for flag in group)
            if not msg:
              continue
            if attr.is_required:
              self._out(' ({msg})'.format(msg=msg))
            else:
              self._out(' [{msg}]'.format(msg=msg))

    if has_global_flags:
      self._out(' [' + em + 'GLOBAL-FLAG ...' + em + ']')

    # positional_args will only be non-empty if we had -- ... or REMAINDER left.
    for arg in usage_text.FilterOutSuppressed(positional_args):
      self._out(usage_text.PositionalDisplayString(arg, markdown=True))

    self._out('\n')

  def _PrintFlagDefinition(self, flag):
    """Prints a flags definition list item."""
    self._out('\n{0}::\n'.format(
        usage_text.FlagDisplayString(flag, markdown=True)))
    self._out('\n{arghelp}\n'.format(arghelp=self._Details(flag)))

  def _PrintFlagSection(self, heading, groups, attrs):
    """Prints a flag section."""
    self._Section(heading, sep=False)
    for group_id, group in sorted(
        groups.iteritems(), key=lambda x: usage_text.FlagGroupSortKey(x[1])):
      if len(group) == 1 or any([getattr(f, 'show_inverted', None)
                                 for f in group]):
        self._PrintFlagDefinition(group[0])
      else:
        if len(group) > 1:
          attr = attrs.get(group_id)
          if attr and attr.description:
            self._out('\n' + attr.description + '\n')
        for flag in sorted(group, key=lambda f: f.option_strings):
          self._PrintFlagDefinition(flag)

  def _PrintPositionalsAndFlagsSections(self, sections, has_global_flags):
    """Prints the positionals and flags sections."""
    visible_positionals = usage_text.FilterOutSuppressed(
        self._command.ai.positional_args)
    if visible_positionals:
      self._Section('POSITIONAL ARGUMENTS', sep=False)
      for arg in visible_positionals:
        self._out('\n{0}::\n'.format(
            usage_text.PositionalDisplayString(arg, markdown=True).lstrip()))
        self._out('\n{arghelp}\n'.format(arghelp=self._Details(arg)))

    # List the sections in order.
    for heading, _, groups, attrs in sections:
      self._PrintFlagSection(heading, groups, attrs)

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
    help_message = textwrap.dedent(help_message)
    if (not arg.option_strings or
        not arg.option_strings[0].startswith('-') or
        arg.metavar == ' '):
      choices = None
    elif arg.choices:
      choices = arg.choices
    else:
      try:
        choices = arg.type.choices
      except AttributeError:
        choices = None
    if choices:
      metavar = arg.metavar or arg.dest.upper()
      choices = getattr(arg, 'choices_help', choices)
      if len(choices) > 1:
        one_of = 'one of'
      else:
        # TBD I guess?
        one_of = '(currenly only one value is supported)'
      if isinstance(choices, dict):
        extra_help = ' _{metavar}_ must be {one_of}:\n\n{choices}\n\n'.format(
            metavar=metavar,
            one_of=one_of,
            choices='\n'.join(
                ['*{name}*::: {desc}'.format(name=name, desc=desc)
                 for name, desc in sorted(choices.iteritems())]))
      else:
        extra_help = ' _{metavar}_ must be {one_of}: {choices}.'.format(
            metavar=metavar,
            one_of=one_of,
            choices=', '.join(['*{0}*'.format(x) for x in choices]))
    else:
      # calliope.backend.ArgumentInterceptor.add_argument() sets
      # arg.inverted_help for Boolean flags with auto-generated --no-FLAG
      # inverted counterparts.
      extra_help = getattr(arg, 'inverted_help', None)
    if extra_help:
      help_message = help_message.rstrip()
      if help_message:
        newline_index = help_message.rfind('\n')
        if newline_index >= 0 and help_message[newline_index + 1] == ' ':
          # Preserve example markdown at end of help_message.
          help_message += '\n\n' + extra_help.strip() + '\n'
        else:
          if not help_message.endswith('.'):
            help_message += '.'
          if help_message.rfind('\n\n') > 0:
            # help_message has multiple paragraphs. Put extra_help in a new
            # paragraph.
            help_message += '\n\n\n'
          help_message += extra_help + '\n'
    return help_message.replace('\n\n', '\n+\n').strip()

  def _ExpandFormatReferences(self, doc):
    """Expand {...} references in doc."""
    doc = usage_text.ExpandHelpText(self._command, doc)

    # Split long $ ... example lines.
    pat = re.compile(r'^ *(\$ .{%d,})$' % (
        _SPLIT - _FIRST_INDENT - _SECTION_INDENT), re.M)
    pos = 0
    rep = ''
    while True:
      match = pat.search(doc, pos)
      if not match:
        break
      rep += (doc[pos:match.start(1)] + ExampleCommandLineSplitter().Split(
          doc[match.start(1):match.end(1)]))
      pos = match.end(1)
    if rep:
      doc = rep + doc[pos:]
    return doc

  def _AddCommandLinkMarkdown(self, doc):
    r"""Add ([`*])command ...\1 link markdown to doc."""
    top = self._command_path[0]
    # This pattern matches "([`*]){top} {arg}*\1" where {top}...{arg} is a
    # known command. The negative lookbehind prefix prevents hyperlinks in
    # SYNOPSIS sections and as the first line in a paragraph.
    pat = re.compile(r'(?<!\n\n)(?<!\*\(ALPHA\)\* )(?<!\*\(BETA\)\* )'
                     r'([`*])(?P<command>{top}( [a-z][-a-z0-9]*)*)\1'.format(
                         top=top))
    pos = 0
    rep = ''
    while True:
      match = pat.search(doc, pos)
      if not match:
        break
      cmd, args = self._SplitCommandFromArgs(match.group('command').split(' '))
      if args:
        # Skip invalid commands.
        rep += doc[pos:match.end(0)]
      else:
        ref = '/'.join(cmd)
        lnk = 'link:' + ref + '[' + ' '.join(cmd) + ']'
        rep += (doc[pos:match.start('command')] + lnk +
                doc[match.end('command'):match.end(0)])
      pos = match.end(0)
    if rep:
      doc = rep + doc[pos:]
    return doc

  def _AddCommandLineLinkMarkdown(self, doc):
    """Add $ command ... link markdown to doc."""
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
      match = pat.search(doc, pos)
      if not match:
        break
      cmd, args = self._SplitCommandFromArgs(match.group(1).split(' '))
      ref = '/'.join(cmd)
      lnk = 'link:' + ref + '[' + ' '.join(cmd) + ']'
      if args:
        lnk += ' ' + ' '.join(args)
      rep += doc[pos:match.start(1)] + lnk
      pos = match.end(1)
    if rep:
      doc = rep + doc[pos:]
    return doc

  def _AddManPageLinkMarkdown(self, doc):
    """Add gcloud ...(1) man page link markdown to doc."""
    top = self._command_path[0]
    pat = re.compile(r'(\*?(' + top + r'(?:[-_ a-z])*)\*?)\(1\)')
    pos = 0
    rep = ''
    while True:
      match = pat.search(doc, pos)
      if not match:
        break
      cmd = match.group(2).replace('_', ' ')
      ref = cmd.replace(' ', '/')
      lnk = '*link:' + ref + '[' + cmd + ']*'
      rep += doc[pos:match.start(2)] + lnk
      pos = match.end(1)
    if rep:
      doc = rep + doc[pos:]
    return doc

  def _FixAirQuotesMarkdown(self, doc):
    """Change ``.*[[:alnum:]]{2,}.*'' quotes => UserInput(*) in doc."""

    # Double ``air quotes'' on strings with no identifier chars or groups of
    # singleton identifier chars are literal. All other double air quote forms
    # are converted to unquoted strings with the _UserInput() font
    # embellishment. This is a subjective choice for aesthetically pleasing
    # renderings.
    pat = re.compile(r"[^`](``([^`]*\w{2,}[^`']*)'')")
    pos = 0
    rep = ''
    while True:
      match = pat.search(doc, pos)
      if not match:
        break
      rep += doc[pos:match.start(1)] + self._UserInput(match.group(2))
      pos = match.end(1)
    if rep:
      doc = rep + doc[pos:]
    return doc

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

  def _Edit(self, doc):
    """Applies edits to a copy of the generated markdown in doc.

    The sub-edit method call order might be significant. This method allows
    the combined edits to be tested without relying on the order.

    Args:
      doc: The markdown document to edit.

    Returns:
      An edited copy of the generated markdown.
    """
    doc = self._ExpandFormatReferences(doc)
    doc = self._AddCommandLineLinkMarkdown(doc)
    doc = self._AddCommandLinkMarkdown(doc)
    doc = self._AddManPageLinkMarkdown(doc)
    doc = self._FixAirQuotesMarkdown(doc)
    return doc

  def Generate(self):
    """Generates markdown for the command, group or topic, into a string."""
    self._out('# {0}(1)\n'.format(self._file_name.upper()))
    self._Section('NAME')
    self._out('{{command}} - {index}\n'.format(index=self._command.index_help))
    if not self._is_topic:
      sections, has_global_flags = usage_text.GetFlagSections(
          self._command, self._command.ai)
      self._PrintSynopsisSection(sections, has_global_flags)
    self._ExtractDetailedHelp()
    self._PrintSectionIfExists(
        'DESCRIPTION',
        default=usage_text.ExpandHelpText(self._command, self._description))
    if not self._is_topic:
      self._PrintPositionalsAndFlagsSections(sections, has_global_flags)
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
    return self._Edit(self._buf.getvalue())


def Markdown(command):
  """Generates and returns the help markdown document for command.

  Args:
    command: The CommandCommon command instance.

  Returns:
    The markdown document string.
  """
  return MarkdownGenerator(command).Generate()
