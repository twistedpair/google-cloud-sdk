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

"""The Calliope command help document markdown generator."""

import abc
import argparse
import re
import StringIO
import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import usage_text
from googlecloudsdk.core.console import console_io


_SPLIT = 78  # Split lines longer than this.
_SECTION_INDENT = 8  # Section or list within section indent.
_FIRST_INDENT = 2  # First line indent.
_SUBSEQUENT_INDENT = 6  # Subsequent line indent.


def _GetIndexFromCapsule(capsule):
  """Returns a help doc index line for a capsule line.

  The capsule line is a formal imperative sentence, preceded by optional
  (RELEASE-TRACK) or [TAG] tags, optionally with markdown attributes. The index
  line has no tags, is not capitalized and has no period, period.

  Args:
    capsule: The capsule line to convert to an index line.

  Returns:
    The help doc index line for a capsule line.
  """
  # Strip leading tags: <markdown>(TAG)<markdown> or <markdown>[TAG]<markdown>.
  capsule = re.sub(r'(\*?[[(][A-Z]+[])]\*? +)*', '', capsule)
  # Lower case first word if not an abbreviation.
  match = re.match(r'([A-Z])([^A-Z].*)', capsule)
  if match:
    capsule = match.group(1).lower() + match.group(2)
  # Strip trailing period.
  return capsule.rstrip('.')


def GetFlagHeading(category):
  """Returns the flag section heading name for a flag category.

  Args:
    category: The flags category name.

  Returns:
    The flag section heading name for a flag category.
  """
  return category if 'FLAGS' in category else category + ' FLAGS'


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
  """Command help markdown document generator base class.

  Attributes:
    _buf: Output document stream.
    _capsule: The one line description string.
    _command_name: The dotted command name.
    _command_path: The command path list.
    _doc: The output markdown document string.
    _docstring: The command docstring.
    _file_name: The command path name (used to name documents).
    _final_sections: The list of PrintFinalSections section names.
    _flag_sections: The flag sections generated by _SetFlagSections().
    _is_hidden: The command is hidden.
    _is_topic: True if the command is a help topic.
    _out: Output writer.
    _printed_sections: The set of already printed sections.
    _release_track: The calliope.base.ReleaseTrack.
    _sections: Command SECTION dict indexed by section name.
    _subcommand: The list of subcommand instances or None.
    _subgroup: The list of subgroup instances or None.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self, command_path, release_track, is_hidden):
    """Constructor.

    Args:
      command_path: The command path list.
      release_track: The base.ReleaseTrack of the command.
      is_hidden: The command is hidden if True.
    """
    self._command_path = command_path
    self._command_name = ' '.join(self._command_path)
    self._top = self._command_path[0] if self._command_path else ''
    self._buf = StringIO.StringIO()
    self._out = self._buf.write
    self._capsule = ''
    self._docstring = ''
    self._final_sections = ['EXAMPLES', 'SEE ALSO']
    self._sections = {}
    self._file_name = '_'.join(self._command_path)
    self._flag_sections = None
    self._global_flags = []
    self._is_hidden = is_hidden
    self._is_root = len(self._command_path) == 1
    self._release_track = release_track
    if (len(self._command_path) >= 3 and
        self._command_path[1] == release_track.prefix):
      command_index = 2
    else:
      command_index = 1
    self._is_topic = (len(self._command_path) >= (command_index + 1) and
                      self._command_path[command_index] == 'topic')
    self._printed_sections = set()

  @staticmethod
  @abc.abstractmethod
  def FlagGroupSortKey(flags):
    """Returns a flag group sort key for sorted().

    This orders individual flags before mutually exclusive groups.

    Args:
      flags: A list of flags in the group.

    Returns:
      A sort key for the sorted() builtin where singletons sort before groups.
    """
    pass

  @staticmethod
  @abc.abstractmethod
  def IsHidden(arg):
    """Returns True if arg is suppressed."""
    pass

  @abc.abstractmethod
  def IsValidSubPath(self, sub_command_path):
    """Determines if the given sub command path is valid from this node.

    Args:
      sub_command_path: [str], The pieces of the command path.

    Returns:
      True, if the given path parts exist under this command or group node.
      False, if the sub path does not lead to a valid command or group.
    """
    pass

  @abc.abstractmethod
  def GetPositionalArgs(self):
    """Returns the command positional args."""
    pass

  @abc.abstractmethod
  def GetFlagGroups(self):
    """Returns (group, group_attr, global_flags)."""
    pass

  def _FilterOutHidden(self, args):
    """Returns a copy of args containing only non-hidden arguments."""
    return [a for a in args if not self.IsHidden(a)]

  def _ExpandHelpText(self, text):
    """Expand command {...} references in text.

    Args:
      text: The text chunk to expand.

    Returns:
      The expanded help text.
    """
    return console_io.LazyFormat(
        text or '',
        command=self._command_name,
        man_name=self._file_name,
        top_command=self._top,
        parent_command=' '.join(self._command_path[:-1]),
        index=self._capsule,
        **self._sections
    )

  def _SetFlagSections(self):
    """Sets self._flag_sections in document order and self._global_flags.

    Returns:
      ([section], global_flags)
        section - (heading, is_priority, flags)
          heading - The section heading.
          is_priority - True if this is a priority section. Priority sections
            are grouped first. The first 2 priority sections appear in short
            help.
          flags - The list of flags in the section.
          attrs - A dict of calliope.backend.ArgumentGroupAttr objects indexed
            by group_id.
        global_flags - The list of global flags not included in the section
          .list
    """
    if self._flag_sections is not None:
      return
    groups, group_attr, self._global_flags = self.GetFlagGroups()
    # Partition the non-GLOBAL flag groups dict into categorized sections. A
    # group is REQUIRED if any flag in it is required, categorized if any flag
    # in it is categorized, otherwise its OTHER.  REQUIRED takes precedence
    # over categorized.
    categorized_groups = {}
    attrs = {}
    for group_id, group in groups.iteritems():
      if groups and not group_id:
        continue
      flags = self._FilterOutHidden(group)
      if not flags:
        continue

      attr = group_attr.get(group_id)
      if attr and attr.is_mutex and attr.is_required:
        category = 'REQUIRED'
      else:
        category = 'OTHER'
        for f in flags:
          if f.required:
            category = 'REQUIRED'
            break
          elif f.category:
            category = f.category
            break

      if category not in categorized_groups:
        categorized_groups[category] = {}
      categorized_groups[category][group_id] = flags
      if category not in attrs:
        attrs[category] = {}
      attrs[category][group_id] = attr

    # Collect the priority sections first in order:
    #   REQUIRED, COMMON, OTHER, and categorized.
    self._flag_sections = []
    other_flags_heading = 'FLAGS'
    for category, other in (('REQUIRED', 'OPTIONAL'),
                            (base.COMMONLY_USED_FLAGS, 'OTHER'),
                            ('OTHER', None)):
      if category in categorized_groups:
        if other:
          other_flags_heading = other
          heading = category
        elif len(categorized_groups) > 1:
          heading = 'FLAGS'
        else:
          heading = other_flags_heading
        if heading == base.COMMONLY_USED_FLAGS and self._is_root:
          # The root command COMMON flags are "<self._top> WIDE".
          heading = '{} WIDE'.format(self._top.upper())
        self._flag_sections.append((GetFlagHeading(heading),
                                    other is not None,
                                    categorized_groups[category],
                                    attrs[category]))
        # This prevents the category from being re-added in the loop below.
        del categorized_groups[category]

    # Add the remaining categories in sorted order.
    for category, groups in sorted(categorized_groups.iteritems()):
      self._flag_sections.append((GetFlagHeading(category),
                                  False,
                                  groups,
                                  attrs[category]))

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
    skip = 1
    i = skip
    while i <= len(cmd):
      i += 1
      if not self.IsValidSubPath(cmd[skip:i]):
        i -= 1
        break
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

  def PrintSectionHeader(self, name, sep=True):
    """Prints the section header markdown for name.

    Args:
      name: str, The manpage section name.
      sep: boolean, Add trailing newline.
    """
    self._printed_sections.add(name)
    self._out('\n\n## {name}\n'.format(name=name))
    if sep:
      self._out('\n')

  def PrintNameSection(self, disable_header=False):
    """Prints the command line name section.

    Args:
      disable_header: Disable printing the section header if True.
    """
    if not disable_header:
      self.PrintSectionHeader('NAME')
    self._out('{command} - {index}\n'.format(
        command=self._command_name,
        index=_GetIndexFromCapsule(self._capsule)))

  def PrintSynopsisSection(self, disable_header=False):
    """Prints the command line synopsis section.

    Args:
      disable_header: Disable printing the section header if True.
    """
    if self._is_topic:
      return
    self._SetFlagSections()
    # MARKDOWN_CODE is the default SYNOPSIS font style.
    code = base.MARKDOWN_CODE
    em = base.MARKDOWN_ITALIC
    if not disable_header:
      self.PrintSectionHeader('SYNOPSIS')
    self._out('{code}{command}{code}'.format(code=code,
                                             command=self._command_name))

    # Output the positional args up to the first REMAINDER or '-- *' args. The
    # rest will be picked up after the flag args are output. argparse does not
    # have an explicit '--' arg intercept, so we use the metavar value as a '--'
    # sentinel. Any suppressed args are ingnored by a pre-pass.
    positional_args = self._FilterOutHidden(self.GetPositionalArgs())
    while positional_args:
      arg = positional_args[0]
      if arg.nargs == argparse.REMAINDER or arg.metavar.startswith('-- '):
        break
      positional_args.pop(0)
      self._out(' ' + usage_text.PositionalDisplayString(arg, markdown=True))

    if self._subcommands and self._subgroups:
      self._out(' ' + em + 'GROUP' + em + ' | ' + em + 'COMMAND' + em)
    elif self._subcommands:
      self._out(' ' + em + 'COMMAND' + em)
    elif self._subgroups:
      self._out(' ' + em + 'GROUP' + em)

    # Generate the flag usage string with flags in section order.
    for _, _, groups, attrs in self._flag_sections:
      for group_id, group in sorted(
          groups.iteritems(), key=lambda x: self.FlagGroupSortKey(x[1])):
        flag = group[0]
        if len(group) == 1:
          msg = usage_text.FlagDisplayString(
              flag,
              markdown=True,
              inverted=getattr(flag, 'inverted_synopsis', False))
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

    if self._global_flags:
      self._out(' [' + em + self._top.upper() + '_WIDE_FLAG ...' + em + ']')

    # positional_args will only be non-empty if we had -- ... or REMAINDER left.
    for arg in self._FilterOutHidden(positional_args):
      self._out(' ' + usage_text.PositionalDisplayString(arg, markdown=True))

    self._out('\n')

  def PrintPositionalDefinition(self, arg):
    self._out('\n{0}::\n'.format(
        usage_text.PositionalDisplayString(arg, markdown=True)))
    self._out('\n{arghelp}\n'.format(arghelp=self.GetArgDetails(arg)))

  def PrintFlagDefinition(self, flag, disable_header=False):
    """Prints a flags definition list item.

    Args:
      flag: The flag object to display.
      disable_header: Disable printing the section header if True.
    """
    if not disable_header:
      self._out('\n')
    self._out('{0}::\n'.format(
        usage_text.FlagDisplayString(flag, markdown=True)))
    self._out('\n{arghelp}\n'.format(arghelp=self.GetArgDetails(flag)))

  def PrintFlagSection(self, heading, groups, attrs, disable_header=False):
    """Prints a flag section.

    Args:
      heading: The flag section heading name.
      groups: The flag group ids.
      attrs: The flag group attributes.
      disable_header: Disable printing the section header if True.
    """
    if not disable_header:
      self.PrintSectionHeader(heading, sep=False)
    for group_id, group in sorted(
        groups.iteritems(), key=lambda x: self.FlagGroupSortKey(x[1])):
      if len(group) == 1 or any([getattr(f, 'inverted_synopsis', None)
                                 for f in group]):
        self.PrintFlagDefinition(group[0], disable_header=disable_header)
      else:
        if len(group) > 1:
          attr = attrs.get(group_id)
          if attr and attr.description:
            self._out('\n' + attr.description + '\n')
        for flag in sorted(group, key=lambda f: f.option_strings):
          self.PrintFlagDefinition(flag, disable_header=disable_header)

  def PrintPositionalsAndFlagsSections(self, disable_header=False):
    """Prints the positionals and flags sections.

    Args:
      disable_header: Disable printing the section header if True.
    """
    if self._is_topic:
      return
    self._SetFlagSections()
    visible_positionals = self._FilterOutHidden(self.GetPositionalArgs())
    if visible_positionals:
      if not disable_header:
        self.PrintSectionHeader('POSITIONAL ARGUMENTS', sep=False)
      for arg in visible_positionals:
        self.PrintPositionalDefinition(arg)

    # List the sections in order.
    for heading, _, groups, attrs in self._flag_sections:
      self.PrintFlagSection(heading, groups, attrs,
                            disable_header=disable_header)

    if self._global_flags:
      if not disable_header:
        self.PrintSectionHeader(
            '{} WIDE FLAGS'.format(self._top.upper()), sep=False)
      self._out('\nThese flags are available to all commands: {}.'
                '\nRun *$ {} help* for details.\n'
                .format(', '.join(sorted(self._global_flags)),
                        self._top))

  def PrintSubGroups(self, disable_header=False):
    """Prints the subgroup section if there are subgroups.

    Args:
      disable_header: Disable printing the section header if True.
    """
    if self._subgroups:
      self.PrintCommandSection('GROUP', self._subgroups,
                               disable_header=disable_header)

  def PrintSubCommands(self, disable_header=False):
    """Prints the subcommand section if there are subcommands.

    Args:
      disable_header: Disable printing the section header if True.
    """
    if self._subcommands:
      if self._is_topic:
        self.PrintCommandSection('TOPIC', self._subcommands, is_topic=True,
                                 disable_header=disable_header)
      else:
        self.PrintCommandSection('COMMAND', self._subcommands,
                                 disable_header=disable_header)

  def PrintSectionIfExists(self, name, default=None, disable_header=False):
    """Print a section name if it exists.

    Args:
      name: str, The manpage section name.
      default: str, Default help_stuff if section name is not defined.
      disable_header: Disable printing the section header if True.
    """
    if name in self._printed_sections:
      return
    help_stuff = self._sections.get(name, default)
    if not help_stuff:
      return
    if callable(help_stuff):
      help_message = help_stuff()
    else:
      help_message = help_stuff
    if not disable_header:
      self.PrintSectionHeader(name)
    self._out('{message}\n'.format(
        message=textwrap.dedent(help_message).strip()))

  def PrintExtraSections(self, disable_header=False):
    """Print extra sections not in excluded_sections.

    Extra sections are sections that have not been printed yet.
    PrintSectionIfExists() skips sections that have already been printed.

    Args:
      disable_header: Disable printing the section header if True.
    """
    excluded_sections = set(self._final_sections + ['NOTES'])
    for section in sorted(self._sections):
      if section.isupper() and section not in excluded_sections:
        self.PrintSectionIfExists(section, disable_header=disable_header)

  def PrintFinalSections(self, disable_header=False):
    """Print the final sections in order.

    Args:
      disable_header: Disable printing the section header if True.
    """
    for section in self._final_sections:
      self.PrintSectionIfExists(section, disable_header=disable_header)
    self.PrintNotesSection(disable_header=disable_header)

  def PrintCommandSection(self, name, subcommands, is_topic=False,
                          disable_header=False):
    """Prints a group or command section.

    Args:
      name: str, The section name singular form.
      subcommands: dict, The subcommand dict.
      is_topic: bool, True if this is a TOPIC subsection.
      disable_header: Disable printing the section header if True.
    """
    # Determine if the section has any content.
    content = ''
    for subcommand, help_info in sorted(subcommands.iteritems()):
      if self._is_hidden or not help_info.is_hidden:
        # If this group is already hidden, we can safely include hidden
        # sub-items.  Else, only include them if they are not hidden.
        content += '\n*link:{ref}[{cmd}]*::\n\n{txt}\n'.format(
            ref='/'.join(self._command_path + [subcommand]),
            cmd=subcommand,
            txt=help_info.help_text)
    if content:
      if not disable_header:
        self.PrintSectionHeader(name + 'S')
      if is_topic:
        self._out('The supplementary help topics are:\n')
      else:
        self._out('{cmd} is one of the following:\n'.format(
            cmd=self._UserInput(name)))
      self._out(content)

  def GetNotes(self):
    """Returns the explicit NOTES section contents."""
    return self._sections.get('NOTES')

  def PrintNotesSection(self, disable_header=False):
    """Prints the NOTES section if needed.

    Args:
      disable_header: Disable printing the section header if True.
    """
    notes = self.GetNotes()
    if notes:
      if not disable_header:
        self.PrintSectionHeader('NOTES')
      if notes:
        self._out(notes + '\n\n')

  def GetArgDetails(self, arg):
    """Returns the detailed help message for the given arg."""
    if getattr(arg, 'detailed_help', None):
      raise ValueError(
          '{}: Use add_argument(help=...) instead of detailed_help="""{}""".'
          .format(self._command_name, getattr(arg, 'detailed_help')))
    return usage_text.GetArgDetails(arg)

  def _ExpandFormatReferences(self, doc):
    """Expand {...} references in doc."""
    doc = self._ExpandHelpText(doc)

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
    if not self._command_path:
      return doc
    # This pattern matches "([`*]){top} {arg}*\1" where {top}...{arg} is a
    # known command. The negative lookbehind prefix prevents hyperlinks in
    # SYNOPSIS sections and as the first line in a paragraph.
    pat = re.compile(r'(?<!\n\n)(?<!\*\(ALPHA\)\* )(?<!\*\(BETA\)\* )'
                     r'([`*])(?P<command>{top}( [a-z][-a-z0-9]*)*)\1'.format(
                         top=self._top))
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
    if not self._command_path:
      return doc
    # This pattern matches "$ {top} {arg}*" where each arg is lower case and
    # does not start with example-, my-, or sample-. This follows the style
    # guide rule that user-supplied args to example commands contain upper case
    # chars or start with example-, my-, or sample-. The trailing .? allows for
    # an optional punctuation character before end of line. This handles cases
    # like ``... run $ <top> foo bar.'' at the end of a sentence.
    pat = re.compile(r'\$ (' + self._top +
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
    """Add <top> ...(1) man page link markdown to doc."""
    if not self._command_path:
      return doc
    pat = re.compile(r'(\*?(' + self._top + r'(?:[-_ a-z])*)\*?)\(1\)')
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
    """Change ``.*[[:alnum:]]{2,}.*'' quotes => _UserInput(*) in doc."""

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

  def Edit(self, doc=None):
    """Applies edits to a copy of the generated markdown in doc.

    The sub-edit method call order might be significant. This method allows
    the combined edits to be tested without relying on the order.

    Args:
      doc: The markdown document string to edit, None for the output buffer.

    Returns:
      An edited copy of the generated markdown.
    """
    if doc is None:
      doc = self._buf.getvalue()
    doc = self._ExpandFormatReferences(doc)
    doc = self._AddCommandLineLinkMarkdown(doc)
    doc = self._AddCommandLinkMarkdown(doc)
    doc = self._AddManPageLinkMarkdown(doc)
    doc = self._FixAirQuotesMarkdown(doc)
    return doc

  def Generate(self):
    """Generates markdown for the command, group or topic, into a string."""
    self._out('# {0}(1)\n'.format(self._file_name.upper()))
    self.PrintNameSection()
    self.PrintSynopsisSection()
    self.PrintSectionIfExists('DESCRIPTION')
    self.PrintPositionalsAndFlagsSections()
    self.PrintSubGroups()
    self.PrintSubCommands()
    self.PrintExtraSections()
    self.PrintFinalSections()
    return self.Edit()


class CommandMarkdownGenerator(MarkdownGenerator):
  """Command help markdown document generator.

  Attributes:
    _command: The CommandCommon instance for command.
    _root_command: The root CLI command instance.
    _subcommands: The dict of subcommand help indexed by subcommand name.
    _subgroups: The dict of subgroup help indexed by subcommand name.
  """

  def __init__(self, command):
    """Constructor.

    Args:
      command: A calliope._CommandCommon instance. Help is extracted from this
        calliope command, group or topic.
    """
    self._command = command
    command.LoadAllSubElements()
    # pylint: disable=protected-access
    self._root_command = command._TopCLIElement()
    self._subcommands = command.GetSubCommandHelps()
    self._subgroups = command.GetSubGroupHelps()
    super(CommandMarkdownGenerator, self).__init__(
        command.GetPath(),
        command.ReleaseTrack(),
        command.IsHidden())
    self._capsule = self._command.short_help
    self._docstring = self._command.long_help
    self._ExtractSectionsFromDocstring(self._docstring)
    self._sections['description'] = self._sections.get('DESCRIPTION', '')
    self._sections.update(getattr(self._command, 'detailed_help', {}))
    self._subcommands = command.GetSubCommandHelps()
    self._subgroups = command.GetSubGroupHelps()

  def _SetSectionHelp(self, name, lines):
    """Sets section name help composed of lines.

    Args:
      name: The section name.
      lines: The list of lines in the section.
    """
    # Strip leading empty lines.
    while lines and not lines[0]:
      lines = lines[1:]
    # Strip trailing empty lines.
    while lines and not lines[-1]:
      lines = lines[:-1]
    if lines:
      self._sections[name] = '\n'.join(lines)

  def _ExtractSectionsFromDocstring(self, docstring):
    """Extracts section help from the command docstring."""
    name = 'DESCRIPTION'
    lines = []
    for line in textwrap.dedent(docstring).strip().splitlines():
      # '## \n' is not section markdown.
      if len(line) >= 4 and line.startswith('## '):
        self._SetSectionHelp(name, lines)
        name = line[3:]
        lines = []
      else:
        lines.append(line)
    self._SetSectionHelp(name, lines)

  @staticmethod
  def FlagGroupSortKey(flags):
    """Returns a flag group sort key for sorted()."""
    return [len(flags) > 1] + sorted([flag.option_strings for flag in flags])

  @staticmethod
  def IsHidden(arg):
    """Returns True if arg is hidden."""
    return arg.help == argparse.SUPPRESS

  def IsValidSubPath(self, sub_command_path):
    """Returns True if the given sub command path is valid from this node."""
    return self._root_command.IsValidSubPath(sub_command_path)

  def GetPositionalArgs(self):
    """Returns the command positional args."""
    return self._command.ai.positional_args

  def GetFlagGroups(self):
    """Returns (group, group_attr, global_flags)."""
    # Place all flag groups into a dict. Flags that are in a mutually
    # exclusive group are mapped group_id -> [flags]. All other flags
    # are mapped dest -> [flag].
    global_flags = []
    groups = {}
    for flag in (self._command.ai.flag_args +
                 self._command.ai.ancestor_flag_args):
      if flag.is_global and not self._is_root:
        if (flag.help != argparse.SUPPRESS and
            flag.option_strings and
            flag.option_strings[0].startswith('--')):
          global_flags.append(flag.option_strings[0])
      else:
        group_id = self._command.ai.mutex_groups.get(
            flag.dest,
            self._command.ai.argument_groups.get(flag.dest, flag.dest))
        if group_id not in groups:
          groups[group_id] = []
        groups[group_id].append(flag)
    return groups, self._command.ai.group_attr, global_flags

  def GetNotes(self):
    """Returns the explicit and auto-generated NOTES section contents."""
    return self._command.GetNotesHelpSection(self._sections.get('NOTES'))


def Markdown(command):
  """Generates and returns the help markdown document for command.

  Args:
    command: The CommandCommon command instance.

  Returns:
    The markdown document string.
  """
  return CommandMarkdownGenerator(command).Generate()
