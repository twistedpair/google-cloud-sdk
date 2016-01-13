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

from googlecloudsdk.calliope import usage_text
from googlecloudsdk.third_party.py27 import py27_collections as collections


def FilterOutSuppressed(args):
  """Returns a copy of args containing only non-suppressed arguments."""
  return [a for a in args if a.help != argparse.SUPPRESS]


class Error(Exception):
  """Exceptions for the markdown module."""


class MarkdownGenerator(object):
  """Command help markdown document generator.

  Attributes:
    _buf: Output document stream.
    _command: The CommandCommon instance for command.
    _command_name: The command name string.
    _command_path: Command path.
    _detailed_help: Command detailed help string.
    _doc: The output markdown document string.
    _file_name: The command path name (used to name documents).
    _is_top_element: True if command is the top CLI element.
    _is_topic: True if the command is a help topic.
    _out: Output writer.
    _top_element: The top CLI element.
    _track: The Command release track prefix.
    _subcommand: The list of subcommand instances or None.
    _subgroup: The list of subgroup instances or None.
  """

  SPLIT = 78  # Split lines longer than this.
  SECTION_INDENT = 10  # Section or list within section indent.
  FIRST_INDENT = 2  # First line indent.
  SUBSEQUENT_INDENT = 6  # Subsequent line indent.

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
    self._detailed_help = getattr(command, 'detailed_help', {})
    self._command_path = command.GetPath()
    self._command_name = ' '.join(self._command_path)
    self._file_name = '_'.join(self._command_path)
    self._track = command.ReleaseTrack(for_help=True).prefix
    command_index = (2 if self._track and len(self._command_path) >= 3 and
                     self._command_path[1] == self._track else 1)
    self._is_topic = (len(self._command_path) >= (command_index + 1) and
                      self._command_path[command_index] == 'topic')
    # pylint: disable=protected-access
    self._top_element = command._TopCLIElement()
    self._is_top_element = command.IsRoot()
    self._subcommands = command.GetSubCommandHelps()
    self._subgroups = command.GetSubGroupHelps()

  def _IsSuppressed(self, arg):
    """Checks if arg help is suppressed.

    Args:
      arg: The argparse arg to check.

    Returns:
      True if arg help is suppressed.
    """
    return arg.help == argparse.SUPPRESS

  def _UserInput(self, msg):
    """Returns msg with user input markdown.

    Args:
      msg: str, The user input string.

    Returns:
      The msg string with embedded user input markdown.
    """
    return (usage_text.MARKDOWN_CODE + usage_text.MARKDOWN_ITALIC +
            msg +
            usage_text.MARKDOWN_ITALIC + usage_text.MARKDOWN_CODE)

  def _Section(self, name, sep=True):
    """Prints the section header markdown for name.

    Args:
      name: str, The manpage section name.
      sep: boolean, Add trailing newline.
    """
    self._out('\n\n== {name} ==\n'.format(name=name))
    if sep:
      self._out('\n')

  def _PrintSynopsisSection(self):
    """Prints the command line synopsis section."""
    # MARKDOWN_CODE is the default SYNOPSIS font style.
    code = usage_text.MARKDOWN_CODE
    em = usage_text.MARKDOWN_ITALIC
    self._Section('SYNOPSIS')
    self._out('{code}{command}{code}'.format(code=code,
                                             command=self._command_name))

    # Output the positional args up to the first REMAINDER or '-- *' args. The
    # rest will be picked up after the flag args are output. argparse does not
    # have an explicit '--' arg intercept, so we use the metavar value as a '--'
    # sentinel.
    # Any SUPPRESSed args are ingnored by a pre-pass.
    positional_args = FilterOutSuppressed(self._command.ai.positional_args[:])
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

    # Split the groups dict into required, common, and then the rest of the
    # flags.  A group is required if any flag in it is required and common if
    # any flag in it is common.  Required takes precedence over common.
    required_groups = {}
    common_groups = {}
    for group_id, flags in groups.iteritems():
      for f in flags:
        if f.required:
          required_groups[group_id] = flags
          break
        elif f.is_common:
          common_groups[group_id] = flags
          break
    for g in required_groups:
      del groups[g]
    for g in common_groups:
      del groups[g]

    # Generate the flag usage string with required flags first, then common
    # flags, then the rest of the flags.
    for section in [required_groups, common_groups, groups]:
      for group in sorted(section.values(), key=lambda g: g[0].option_strings):
        if len(group) == 1:
          arg = group[0]
          if self._IsSuppressed(arg):
            continue
          msg = usage_text.FlagDisplayString(arg, markdown=True)
          if not msg:
            continue
          if arg.required:
            self._out(' {msg}'.format(msg=msg))
          else:
            self._out(' [{msg}]'.format(msg=msg))
        else:
          group.sort(key=lambda f: f.option_strings)
          group = [flag for flag in group if not self._IsSuppressed(flag)]
          msg = ' | '.join(usage_text.FlagDisplayString(arg, markdown=True)
                           for arg in group)
          if not msg:
            continue
          self._out(' [{msg}]'.format(msg=msg))

    if global_flags:
      self._out(' [' + em + 'GLOBAL-FLAG ...' + em + ']')

    # positional_args will only be non-empty if we had -- ... or REMAINDER left.
    for arg in FilterOutSuppressed(positional_args):
      self._out(usage_text.PositionalDisplayString(arg, markdown=True))

  def _PrintFlagSection(self, flags, section):
    if not flags:
      return
    self._Section(section, sep=False)
    for flag in sorted(flags, key=lambda f: f.option_strings):
      self._out('\n{0}::\n'.format(
          usage_text.FlagDisplayString(flag, markdown=True)))
      self._out('\n{arghelp}\n'.format(arghelp=self._Details(flag)))

  def _PrintPositionalsAndFlagsSections(self):
    """Prints the positionals and flags sections."""
    visible_positionals = FilterOutSuppressed(self._command.ai.positional_args)
    if visible_positionals:
      self._Section('POSITIONAL ARGUMENTS', sep=False)
      for arg in visible_positionals:
        self._out('\n{0}::\n'.format(
            usage_text.PositionalDisplayString(arg, markdown=True).lstrip()))
        self._out('\n{arghelp}\n'.format(arghelp=self._Details(arg)))

    # Partition the flags into REQUIRED FLAGS, COMMON FLAGS, OPTIONAL_FLAGS and
    # GLOBAL FLAGS subsections.
    required_flags = []
    common_flags = []
    other_flags = []
    has_global_flags = False
    for arg in (self._command.ai.flag_args +
                self._command.ai.ancestor_flag_args):
      if not self._IsSuppressed(arg):
        if arg.is_global and not self._is_top_element:
          has_global_flags = True
        elif arg.required:
          required_flags.append(arg)
        elif arg.is_common:
          common_flags.append(arg)
        else:
          other_flags.append(arg)

    other_flags_heading = 'FLAGS'
    if required_flags:
      other_flags_heading = 'OPTIONAL FLAGS'
    if common_flags:
      other_flags_heading = 'OTHER FLAGS'

    for flags, section in ((required_flags, 'REQUIRED FLAGS'),
                           (common_flags, 'COMMONLY USED FLAGS'),
                           (other_flags, other_flags_heading)):
      self._PrintFlagSection(flags, section)

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
    help_stuff = self._detailed_help.get(name, default)
    if not help_stuff:
      return
    # Trim off the additional section marker.
    if name.startswith('+'):
      name = name[1:]
    if callable(help_stuff):
      help_message = help_stuff()
    else:
      help_message = help_stuff
    self._Section(name)
    self._out('{message}\n'.format(
        message=textwrap.dedent(help_message).strip()))

  def _PrintAllExtraSections(self):
    """Print all extra man page sections.  These sections start with a '+'."""
    for section in sorted(self._detailed_help):
      if section.startswith('+'):
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
        self._command.ReleaseTrack(for_help=True).help_note):
      self._Section('NOTES')
      if self._command.IsHidden():
        self._out('This command is an internal implementation detail and may'
                  ' change or disappear without notice.\n\n')
      if self._command.ReleaseTrack(for_help=True).help_note:
        self._out(self._command.ReleaseTrack(for_help=True).help_note + '\n\n')

  def _Details(self, arg):
    """Returns the detailed help message for the given arg."""
    help_stuff = getattr(arg, 'detailed_help', (arg.help or '') + '\n')
    help_message = help_stuff() if callable(help_stuff) else help_stuff
    # calliope.backend.ArgumentInterceptor.add_argument() sets arg.inverted_help
    # for Boolean flags with auto-generated --no-FLAG inverted counterparts.
    inverted_help = getattr(arg, 'inverted_help', None)
    if inverted_help:
      # Drop trailing space, newlines and periods. A period will be added below.
      help_message = re.sub('[ .\n]+$', '', help_message)
      if help_message:
        help_message += '.' + inverted_help + '\n'
    return textwrap.dedent(help_message).replace('\n\n', '\n+\n').strip()

  def _Split(self, line):
    """Splits long example command lines.

    Args:
      line: str, The line to split.

    Returns:
      str, The split line.
    """
    ret = ''
    m = self.SPLIT - self.FIRST_INDENT - self.SECTION_INDENT
    n = len(line)
    while n > m:
      indent = self.SUBSEQUENT_INDENT
      j = m
      noflag = 0
      while True:
        if line[j] == ' ':
          # Break at a flag if possible.
          j += 1
          if line[j] == '-':
            break
          # Look back one more operand to see if it's a flag.
          if noflag:
            j = noflag
            break
          noflag = j
          j -= 2
        else:
          # Line is too long -- force an operand split with no indentation.
          j -= 1
          if not j:
            j = m
            indent = 0
            break
      ret += line[:j] + '\\\n' + ' ' * indent
      line = line[j:]
      n = len(line)
      m = self.SPLIT - self.SUBSEQUENT_INDENT - self.SECTION_INDENT
    return ret + line

  def _ExpandFormatReferences(self):
    """Expand {...} references."""
    self._doc = usage_text.ExpandHelpText(self._command, self._buf.getvalue())

    # Split long $ ... example lines.
    pat = re.compile(r'^ *(\$ .{%d,})$' % (
        self.SPLIT - self.FIRST_INDENT - self.SECTION_INDENT), re.M)
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      rep += (self._doc[pos:match.start(1)] +
              self._Split(self._doc[match.start(1):match.end(1)]))
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
      cmd = match.group(1)
      i = cmd.find('set ')
      if i >= 0:
        # This terminates the command at the first positional ending with set.
        # This handles gcloud set and unset subcommands where 'set' and 'unset'
        # are the last command args, the remainder user-specified.
        i += 3
        rem = cmd[i:]
        cmd = cmd[0:i]
      else:
        rem = ''
      ref = '/'.join(cmd.split(' '))
      lnk = 'link:' + ref + '[' + cmd + ']' + rem
      rep += self._doc[pos:match.start(1)] + lnk
      pos = match.end(1)
    if rep:
      self._doc = rep + self._doc[pos:]

  def _AddManPageLinkMarkdown(self):
    """Add gcloud ...(1) man page link markdown."""
    top = self._command_path[0]
    pat = re.compile(r'(\*?(' + top + r'((?:[-_ a-z])*))\*?)\(1\)')
    pos = 0
    rep = ''
    while True:
      match = pat.search(self._doc, pos)
      if not match:
        break
      cmd = match.group(2).replace('_', ' ')
      ref = match.group(3).replace('_', ' ')
      if ref:
        ref = ref[1:]
      ref = '/'.join(ref.split(' '))
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
    pat = re.compile(r"(``([^`]*\w{2,}[^`']*)'')")
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

  def Generate(self):
    """Generates markdown for the command, group or topic, into a string."""
    self._out('= {0}(1) =\n'.format(self._file_name.upper()))
    self._Section('NAME')
    self._out('{{command}} - {index}\n'.format(index=self._command.index_help))
    if not self._is_topic:
      self._PrintSynopsisSection()
    self._PrintSectionIfExists(
        'DESCRIPTION', default=usage_text.ExpandHelpText(
            self._command, self._command.long_help))
    if not self._is_topic:
      self._PrintPositionalsAndFlagsSections()
    if self._subgroups:
      self._PrintCommandSection('GROUP', self._subgroups)
    if self._subcommands:
      if self._is_topic:
        self._PrintCommandSection('TOPIC', self._subcommands, is_topic=True)
      else:
        self._PrintCommandSection('COMMAND', self._subcommands)
    self._PrintSectionIfExists('EXAMPLES')
    self._PrintSectionIfExists('SEE ALSO')
    self._PrintAllExtraSections()
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
