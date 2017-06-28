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

"""utils for search-help command resources."""

import copy
import re
import StringIO

from googlecloudsdk.command_lib.search_help import lookup
from googlecloudsdk.core import log
from googlecloudsdk.core.document_renderers import render_document

DEFAULT_SNIPPET_LENGTH = 200
DOT = '.'

PRIORITIES = {lookup.NAME: 0,
              lookup.CAPSULE: 1,
              lookup.SECTIONS: 2,
              lookup.POSITIONALS: 3,
              lookup.FLAGS: 4,
              lookup.COMMANDS: 5,
              lookup.PATH: 6}


class TextSlice(object):
  """Small class for working with pieces of text."""

  def __init__(self, start, end):
    self.start = start
    self.end = end

  def Overlaps(self, other):
    if other.start < self.start:
      return other.overlaps(self)
    return self.end >= other.start

  def Merge(self, other):
    if not self.Overlaps(other):
      msg = ('Cannot merge text slices [{}:{}] and [{}:{}]: '
             'Do not overlap.'.format(
                 self.start, self.end, other.start, other.end))
      raise ValueError(msg)
    self.start = min(self.start, other.start)
    self.end = max(self.end, other.end)

  def AsSlice(self):
    return slice(self.start, self.end, 1)


def _GetStartAndEnd(match, cut_points, length_per_snippet):
  """Helper function to get start and end of single snippet that matches text.

  Gets a snippet of length length_per_snippet with the match object
  in the middle.
  Cuts at the first cut point (if available, else cuts at any char)
  within 1/2 the length of the start of the match object.
  Then cuts at the last cut point within
  the desired length (if available, else cuts at any point).
  Then moves start back if there is extra room at the beginning.

  Args:
    match: re.match object.
    cut_points: [int], indices of each cut char, plus start and
        end index of full string. Must be sorted.
        (The characters at cut_points are skipped.)
    length_per_snippet: int, max length of snippet to be returned

  Returns:
    (int, int) 2-tuple with start and end index of the snippet
  """
  max_length = cut_points[-1] if cut_points else 0
  match_start = match.start() if match else 0
  match_end = match.end() if match else 0

  # Get start cut point.
  start = 0
  if match_start > .5 * length_per_snippet:
    # Get first point within 1/2 * length_per_snippet chars of term.
    for c in cut_points:
      if c >= match_start - (.5 * length_per_snippet) and c < match_start:
        start = c + 1
        break  # The cut points are already sorted, so first = min.
    # If no cut points, just start 1/2 the desired length back or at 0.
    start = int(max(match_start - (.5 * length_per_snippet), start))

  # Get end cut point.
  # Must be after term but within desired distance of start.
  end = match_end
  # Look for last cut point in this interval
  for c in cut_points:
    if end < c <= start + length_per_snippet:
      end = c
    elif c > start + length_per_snippet:
      break  # the list was sorted, so last = max.
  # If no cut points, just cut at the exact desired length or at the end,
  # whichever comes first.
  if end == match_end:
    end = max(min(max_length, start + length_per_snippet), end)

  # If cutting at the end, update start so we get the maximum length snippet.
  # Look for the first cut point within length_of_snippet of the end.
  if end == max_length:
    for c in cut_points:
      if end - c <= (length_per_snippet + 1) and c < start:
        start = c + 1
        break
  return TextSlice(start, end)


def _BuildExcerpt(text, snips):
  """Helper function to build excerpt using (start, end) tuples.

  Returns a string that combines substrings of the text (text[start:end]),
  joins them with ellipses

  Args:
    text: the text to excerpt from.
    snips: [(int, int)] list of 2-tuples representing start and end places
        to cut text.

  Returns:
    str, the excerpt.
  """
  snippet = '...'.join([text[snip.AsSlice()] for snip in snips])
  if snips:
    if snips[0].start != 0:
      snippet = '...' + snippet
    if snips[-1].end != len(text):
      snippet += '...'
  # TODO(b/35918584): highlight appearance of terms
  return snippet


def _Snip(text, length_per_snippet, terms):
  """Create snippet of text, containing given terms if present.

  The max length of the snippet is the number of terms times the given length.
  This is to prevent a long list of terms from resulting in nonsensically
  short sub-strings. Each substring is up to length given, joined by '...'

  Args:
    text: str, the part of help text to cut. Should be only ASCII characters.
    length_per_snippet: int, the length of the substrings to create containing
        each term.
    terms: [str], the terms to include.

  Returns:
    str, a summary excerpt including the terms, with all consecutive whitespace
        including newlines reduced to a single ' '.
  """
  text = re.sub(r'\s+', ' ', text)
  if len(text) <= length_per_snippet:
    return text
  cut_points = ([0] + [r.start() for r in re.finditer(r'\s', text)] +
                [len(text)])

  if not terms:
    return _BuildExcerpt(
        text,
        [_GetStartAndEnd(None, cut_points, length_per_snippet)])

  unsorted_matches = [re.search(term, text, re.IGNORECASE) for term in terms]
  matches = sorted(filter(bool, unsorted_matches),
                   key=lambda x: x.start())
  snips = []  # list of TextSlice objects.
  for match in matches:
    # Don't get a new excerpt if the word is already in the excerpted part.
    if not (snips and
            snips[-1].start < match.start() and snips[-1].end > match.end()):
      next_slice = _GetStartAndEnd(match, cut_points, length_per_snippet)
      # Combine if overlaps with previous snippet.
      if snips:
        latest = snips[-1]
        if latest.Overlaps(next_slice):
          latest.Merge(next_slice)
        else:
          snips.append(next_slice)
      else:
        snips.append(next_slice)
  # If no terms were found, just cut from beginning.
  if not snips:
    snips = [_GetStartAndEnd(None, cut_points, length_per_snippet)]
  return _BuildExcerpt(text, snips)


def _FormatHeader(header):
  """Helper function to reformat header string in markdown."""
  if header == lookup.CAPSULE:
    header = 'summary description'
  return '# {}'.format(header.upper())


def _FormatItem(item):
  """Helper function to reformat string as markdown list item: {STRING}::."""
  return '{}::'.format(item)


def _AddFlagToSummary(command, summary, length_per_snippet, location, terms):
  """Adds flag summary, given location such as ['flags']['--myflag']."""
  flags = command.get(location[0], {})
  lines = []
  line = ''
  if _FormatHeader(lookup.FLAGS) not in summary:
    lines.append(_FormatHeader(lookup.FLAGS))

  # Add specific flag if given.
  if len(location) > 1:
    # Add flag name and description of flag if not added yet.
    if _FormatItem(location[1]) not in summary:
      lines.append(_FormatItem(location[1]))
      desc_line = flags.get(location[1], {}).get(lookup.DESCRIPTION, '')
      desc_line = _Snip(desc_line, length_per_snippet, terms)
      if desc_line:
        line = desc_line
      else:
        log.warn('Attempted to look up a location [{}] that was not '
                 'found.'.format(location[1]))

    # Add subsections of flag if given.
    if len(location) > 2:
      if location[2] == lookup.DEFAULT:
        default = flags.get(location[1]).get(lookup.DEFAULT)
        if default:
          lines.append(line)
          line = 'Default: {}.'.format(
              flags.get(location[1]).get(lookup.DEFAULT))
      else:
        log.warn('Attempted to look up a location [{}] that was not '
                 'found.'.format(location[-1]))

  # If no specific flag given, get list of all flags.
  else:
    line = ', '.join(sorted(command.get(location[0], {}).keys()))
    line = _Snip(line, length_per_snippet, terms)

  if line:
    lines.append(line)
    summary += lines


def _AddPositionalToSummary(command, summary, length_per_snippet,
                            location, terms):
  """Adds summary of arg, given location such as ['positionals']['myarg']."""
  positionals = command.get(lookup.POSITIONALS)
  lines = []
  line = ''
  if _FormatHeader(lookup.POSITIONALS) not in summary:
    lines.append(_FormatHeader(lookup.POSITIONALS))

  # Add specific positional if given in location.
  if len(location) > 1:
    lines.append(_FormatItem(location[1]))
    positionals = [p for p in positionals if p[lookup.NAME] == location[1]]
    if positionals:
      positional = positionals[0]
      line = positional.get(lookup.DESCRIPTION, '')
      line = _Snip(line, length_per_snippet, terms)
    else:
      log.warn('Attempted to look up a location [{}] that was not '
               'found.'.format(location[1]))

  # If no specific positional given, just add list of all available.
  else:
    line = ', '.join(sorted([p[lookup.NAME] for p in positionals]))
  if line:
    lines.append(line)
    summary += lines


def _AddGenericSectionToSummary(command, summary, length_per_snippet,
                                location, terms):
  """Helper function for adding sections in the form ['loc1','loc2',...]."""
  section = command
  for loc in location:
    section = section.get(loc, {})
    if isinstance(section, str):
      line = section
    # if dict or list, use commas to join keys or items, respectively.
    elif isinstance(section, list):
      line = ', '.join(sorted(section))
    elif isinstance(section, dict):
      line = ', '.join(sorted(section.keys()))
    else:
      line = str(section)
  if line:
    summary.append(_FormatHeader(location[-1]))
    loc = '.'.join(location)
    summary.append(
        _Snip(line, length_per_snippet, terms))
  else:
    log.warn('Attempted to look up a location [{}] that was not '
             'found.'.format(location[-1]))


def _Priority(x):
  # Ensure the summary is built in the right order.
  return PRIORITIES.get(x[0], len(PRIORITIES))


def GetSummary(command, found_terms, length_per_snippet=DEFAULT_SNIPPET_LENGTH):
  """Gets a summary of certain attributes of a command.

  This will summarize a json representation of a command using
  cloud SDK-style markdown (but with no text wrapping) by taking snippets
  of the given locations in a command.

  If a lookup is given from terms to where they appear, then the snippets will
  include the relevant terms.

  Uses a small amount of simple Cloud SDK markdown.

  1) To get a summary with just the brief help:
  GetSummary(command, {'alligator': 'capsule'},
             length_per_snippet=200)

  # SUMMARY DESCRIPTION
  {200-char excerpt of command['capsule'] with first appearance of 'alligator'}

  2) To get a summary with a section (can be first-level or inside 'sections',
  which is the same as detailed_help):
  GetSummary(command, {'': 'sections.SECTION_NAME'})

  # SECTION_NAME
  {excerpt of 'SECTION_NAME' section of detailed help. If it is a list
   it will be joined by ', '.}

  3) To get a summary with a specific positional arg:
  GetSummary(command, {'crocodile': 'positionals.myarg'})

  # POSITIONALS
  myarg::
  {200-char excerpt of 'myarg' positional help containing 'crocodile'}

  4) To get a summary with specific flags, possibly including choices/defaults:
  GetSummary(command,
            {'a': 'flags.myflag.choices', 'b': 'flags.myotherflag.default'})

  # FLAGS
  myflag::
  {excerpt of help} Choices: {comma-separated list of flag choices}
  myotherflag::
  {excerpt of help} Default: {flag default}

  Args:
    command: dict, a json representation of a command.
    found_terms: dict, mapping of terms to the locations where they are
        found. If no term is relevant, a '' is used.
    length_per_snippet: int, length of desired substrings to get from text.

  Returns:
    str, a markdown summary
  """
  # Always include capsule.
  found_terms.update({'': lookup.CAPSULE})
  summary = []
  locations = [location.split('.')
               for location in sorted(set(found_terms.values()))]

  for location in sorted(locations, key=_Priority):
    terms = {t for t, l in found_terms.iteritems()
             if l == '.'.join(location) and t}
    if location[0] == lookup.FLAGS:
      _AddFlagToSummary(command, summary, length_per_snippet, location, terms)
    elif location[0] == lookup.POSITIONALS:
      _AddPositionalToSummary(command, summary, length_per_snippet, location,
                              terms)
    # Add any other sections of help. path and name are ignored.
    elif lookup.PATH not in location and lookup.NAME not in location:
      _AddGenericSectionToSummary(command, summary, length_per_snippet,
                                  location, terms)
  return '\n'.join(summary)


def ProcessResult(command, found_terms):
  """Helper function to create help text resource for listing results.

  Args:
    command: dict, json representation of command.
    found_terms: {str: str}, lookup from terms to where they were
      found.

  Returns:
    A modified copy of the json command with a summary, and with the dict
        of subcommands replaced with just a list of available subcommands.
  """
  new_command = copy.deepcopy(command)
  if lookup.COMMANDS in new_command.keys():
    new_command[lookup.COMMANDS] = sorted([
        c[lookup.NAME] for c in new_command[lookup.COMMANDS].values()])
  summary = GetSummary(command, found_terms)
  # Render the summary for console printing, but ignoring console width.
  md = StringIO.StringIO(summary)
  rendered_summary = StringIO.StringIO()
  render_document.RenderDocument('text',
                                 md,
                                 out=rendered_summary,
                                 width=len(summary))
  # Remove indents and blank lines so summary can be easily
  # printed in a table.
  new_command[lookup.SUMMARY] = '\n'.join([
      l.lstrip() for l in rendered_summary.getvalue().splitlines()
      if l.lstrip()])
  return new_command


def LocateTerm(command, term):
  """Helper function to get first location of term in a json command.

  Locations are considered in this order: 'name', 'capsule',
  'sections', 'positionals', 'flags', 'commands', 'path'. Returns a dot-
  separated lookup for the location e.g. 'sections.description' or
  empty string if not found.

  Args:
    command: dict, json representation of command.
    term: str, the term to search.

  Returns:
    str, lookup for where to find the term when building summary of command.
  """
  # Look in name/capsule
  regexp = re.compile(re.escape(term), re.IGNORECASE)
  if (regexp.search(command[lookup.NAME])
      or regexp.search(command[lookup.CAPSULE])):
    return lookup.CAPSULE

  # Look in detailed help sections
  for section_name, section_desc in sorted(
      command[lookup.SECTIONS].iteritems()):
    if regexp.search(section_desc):
      return DOT.join([lookup.SECTIONS, section_name])

  # Look in flags
  for flag_name, flag in sorted(command[lookup.FLAGS].iteritems()):
    if (regexp.search(flag[lookup.NAME])
        or regexp.search(flag[lookup.DESCRIPTION])):
      return DOT.join([lookup.FLAGS, flag_name])
    if regexp.search(str(flag[lookup.CHOICES])):
      return DOT.join([lookup.FLAGS, flag[lookup.NAME], lookup.CHOICES])
    if regexp.search(str(flag.get(lookup.DEFAULT, ''))):
      return DOT.join([lookup.FLAGS, flag[lookup.NAME], lookup.DEFAULT])

  # Look in positionals
  for positional in command[lookup.POSITIONALS]:
    if (regexp.search(positional[lookup.NAME])
        or regexp.search(positional[lookup.DESCRIPTION])):
      return DOT.join([lookup.POSITIONALS, positional[lookup.NAME]])

  # Look in subcommands & path
  if regexp.search(str(command[lookup.COMMANDS].keys())):
    return lookup.COMMANDS
  if regexp.search(' '.join(command[lookup.PATH])):
    return lookup.PATH
  return ''
