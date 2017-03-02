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

"""gcloud search-help command resources."""

import copy
import json
import os
import re
import StringIO

from googlecloudsdk.command_lib.search_help import lookup
from googlecloudsdk.command_lib.search_help import search_util
from googlecloudsdk.command_lib.search_help import table
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.document_renderers import render_document

LENGTH = 200
DOT = '.'


def RunSearch(table_path, terms, cli):
  """Runs search-help by opening and reading help table, finding commands.

  Args:
    table_path: str, the path to the help table.
    terms: [str], list of strings that must be found in the command.
    cli: the Calliope CLI object

  Returns:
    a list of json objects representing gcloud commands.
  """
  if not os.path.exists(table_path):
    with progress_tracker.ProgressTracker('Updating command help index...'):
      table.Update(cli)

  with open(table_path, 'r') as table_file:
    parent = json.loads(table_file.read())

  def WalkTree(parent, found_commands):
    result = PossiblyGetResult(parent, terms)
    if result:
      found_commands.append(result)
    for child_command in parent.get(lookup.COMMANDS, {}).values():
      WalkTree(child_command, found_commands)

  found_commands = []
  WalkTree(parent, found_commands)
  return found_commands


def _ProcessResult(command, terms_to_locations):
  """Helper function to create help text resource for listing results.

  Args:
    command: dict, json representation of command.
    terms_to_locations: {str: str}, lookup from terms to where they were found.

  Returns:
    A modified copy of the json command with a summary, and with the dict
        of subcommands replaced with just a list of available subcommands.
  """
  new_command = copy.deepcopy(command)
  if lookup.COMMANDS in new_command.keys():
    new_command[lookup.COMMANDS] = sorted([
        c[lookup.NAME] for c in new_command[lookup.COMMANDS].values()])
  summary = search_util.GetSummary(command, terms_to_locations)
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


def _LocateTerm(command, term):
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


def PossiblyGetResult(command, terms):
  """Helper function to determine whether a command contains all terms.

  Returns a copy of the command or command group with modifications to the
  'commands' field and an added 'summary' field if:
  1) All terms are found in the command
  2) At least one term is in the command name or help text as opposed to the
     ancestry path. For example:
     - Single term 'foo' matches `gcloud foo` because it
       occurs in the name of the command group.
     - Single term 'foo' does not match `gcloud foo bar`
       because it only occurs in the ancestry path.
     - Multiple terms ['gcloud', 'foo'] will match `gcloud foo`
       because one term is in the name, even though the other term is not.
     - Multiple terms ['gcloud', 'foo'] will not match `gcloud foo bar`
       (assuming 'gcloud' and 'foo' don't appear in the help text for
       the command) because both terms occur only in the path.
  3) The command is in GA (alpha commands are not considered stable, and
     help text requirements for beta commands are not as strict).

  Args:
    command: dict, a json representation of a command.
    terms: [str], a list of terms to search.

  Returns:
    a modified copy of the command if the command is a result, otherwise None
  """
  if command[lookup.RELEASE] == lookup.GA:
    locations = [_LocateTerm(command, term) for term in terms]
    terms_to_locations = dict(zip(terms, locations))
    # Return command only if at least one term is outside its ancestry path.
    if all(locations) and set(locations) != {lookup.PATH}:
      terms_to_locations.update({'': lookup.CAPSULE})  # Always include capsule.
      new_command = _ProcessResult(command, terms_to_locations)
      return new_command
