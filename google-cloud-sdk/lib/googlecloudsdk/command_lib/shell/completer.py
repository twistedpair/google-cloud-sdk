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
"""gcloud shell completion."""

from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.shell import gcloud_parser as parser
from googlecloudsdk.command_lib.shell.gcloud_tree import gcloud_tree
from googlecloudsdk.core import properties
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion


_LOCATION_FLAGS = ['--global', '--location', '--region', '--zone']


class ShellCliCompleter(Completer):
  """A prompt_toolkit shell CLI completer."""

  def __init__(self):
    self.root = {'gcloud': gcloud_tree}
    self.index = 0
    self.experimental_autocomplete_enabled = ExperimentalAutocompleteEnabled()

  def get_completions(self, doc, complete_event):
    """Yields the completions for doc.

    Args:
      doc: A Document instance containing the shell command line to complete.
      complete_event: The CompleteEvent that triggered this completion.

    Yields:
      Completion instances for doc.
    """
    commands = parser.ParseLine(doc.text_before_cursor)
    if not commands:
      return

    tokens = commands[-1]
    if not tokens:
      return
    if tokens[0].value != 'gcloud':
      gcloud_token = parser.ArgToken('gcloud', parser.ArgTokenType.GROUP,
                                     gcloud_tree, 0, 0)
      tokens = ([gcloud_token] + tokens)
    node = self.root
    info = None
    last_token = tokens[-1]
    path = []

    # Autocomplete commands and groups after spaces.
    if (last_token.token_type == parser.ArgTokenType.GROUP and
        doc.cursor_position > last_token.end):
      for completion in CompleteCommandGroups(tokens):
        yield Completion(completion)
      return

    # Traverse the CLI tree.
    for token in tokens:
      if token.value in node:
        info = node[token.value]
        path.append(info)
        node = info.get('commands', {})
      else:
        break

    last_token_name = last_token.value
    offset = -len(last_token_name)

    # Check for flags.
    if ((last_token_name.startswith('-') and info) or
        (last_token.token_type == parser.ArgTokenType.FLAG_ARG)):
      # Collect all non-hidden flags of current command and parents into node.
      node = FilterHiddenFlags(info.get('flags', {}))
      for info in path:
        node.update(FilterHiddenFlags(info.get('flags', {})))

      if doc.text_before_cursor[-1].isspace():
        return

      if last_token.token_type == parser.ArgTokenType.FLAG_ARG:
        flag_token = tokens[-2]
        if flag_token.value in node:
          choice_offset = doc.cursor_position - last_token.end
          info = node[flag_token.value]
          if info.get('type', None) != 'bool':
            choices = info.get('choices', None)
            if choices:
              # A flag with static choices.
              offset -= choice_offset
              for choice in choices:
                if choice.lower().startswith(last_token_name.lower()):
                  yield Completion(choice, offset)
          return

    def _MetaTextForChoice(choice):
      if (self.experimental_autocomplete_enabled and
          FlagIsRequired(node[choice])):
        return 'required'

    ranked_completions = []
    if self.experimental_autocomplete_enabled:
      ranked_completions = RankedCompletions(node, doc)
    else:
      ranked_completions = sorted(node)

    for choice in ranked_completions:
      if choice.startswith(last_token_name):
        yield Completion(
            choice,
            offset,
            display_meta=_MetaTextForChoice(choice))


def ExperimentalAutocompleteEnabled():
  return bool(properties.VALUES.experimental.shell_autocomplete.GetBool())


def FilterHiddenFlags(flags_dict):
  """Removes flags hidden in the gcloud command tree from the suggestions list.

  Since the negative versions of boolean flags also appear as hidden in the
  gcloud tree, they have to be manually added every time a boolean, non-hidden
  flag should be shown.

  Args:
    flags_dict: a dictionary of flags as they appear in the gcloud_tree.

  Returns:
    A new dictionary with all hidden flags (except for '--no-' boolean flags)
    removed.
  """
  res = {}
  for flag, flag_properties in flags_dict.iteritems():
    if not FlagIsHidden(flag_properties):
      res[flag] = flag_properties
      if flag_properties.get('type', None) == 'bool':
        # add negative version of boolean flag
        no_flag = '--no-' + (flag.split('--')[1])
        no_flag_properties = flags_dict.get(no_flag, None)
        if no_flag_properties:
          res[no_flag] = no_flag_properties
  return res


def FlagIsHidden(flag_dict):
  """Returns whether a flag is hidden or not.

  Args:
    flag_dict: a specific flag's dictionary as found in the gcloud_tree

  Returns:
    True if the flag's hidden, False otherwise or if flag_dict doesn't contain
    the 'hidden' key.
  """
  return flag_dict.get('hidden', False)


def FlagIsRequired(flag_dict):
  """Returns whether a flag is required or not.

  Args:
    flag_dict: a specific flag's dictionary as found in the gcloud_tree

  Returns:
    True if the flag's required, False otherwise. If the passed dictionary does
    not correspond to a flag (does not contain the 'required' key), False is
    also returned
  """
  return flag_dict.get('required', False)


def IsFlag(string):
  """Returns whether the passed string is a flag.

  Args:
    string: the string to check.

  Returns:
    True if it's a flag, False otherwise.
  """
  return string.startswith('-')


def RankedCompletions(suggestions, doc):
  """Ranks a dictionary of completions based on different priorities.

  Args:
    suggestions: A dictionary of all the autocomplete suggestions as they appear
    in the gcloud_tree.
    doc: A Document instance containing the shell command line to complete,
    and for which to rank the completions.

  Returns:
    A sorted array with the keys of the input dictionary, ranked accordingly.
  """

  def _FlagAlreadyUsed(flag):
    """Returns whether a flag has already been used.

    Args:
      flag: the flag to check.

    Returns:
      True if the flag passed has been used, False otherwise.
    """
    # TODO(b/36809101): remove regular expression checks on doc's
    # text_before_cursor and save state instead
    return flag in re.split('[= ]', doc.text_before_cursor)

  def _ShouldPrioritizeUnusedRequiredFlag(flag):
    """Returns whether the passed flag is an unused required flag.

    Args:
      flag: the flag to check.

    Returns:
      True if the flag passed is an unused required flag, False otherwise.
    """
    return FlagIsRequired(suggestions[flag]) and not _FlagAlreadyUsed(flag)

  def _FlagFromGroupAlreadyUsed(flag_group):
    """Return whether any of the flags belonging to the group has been used.

    Args:
      flag_group: an iterable containing strings with the names of the flags for
      which to check whether any of them have already been used.

    Returns:
      True if any flag in the group has already been used, False otherwise.
    """
    return any(_FlagAlreadyUsed(flag) for flag in flag_group)

  def _ShouldPrioritizeUnusedLocationFlag(flag):
    """Returns whether the passed flag is an unused location flag.

    Unused in this particular context means not only that the actual flag being
    tested has been used, but also that no other location flag has been used
    before (that is, location flags are mutually exclusive for the purpose of
    prioritization).

    Args:
      flag: the flag to check.

    Returns:
      True if the flag passed is an unused location flag, False otherwise.
    """
    return (flag in _LOCATION_FLAGS and
            not _FlagFromGroupAlreadyUsed(_LOCATION_FLAGS))

  def _ShouldPrioritizeFlag(string):
    """Returns whether the passed string is a flag and should be prioritized.

    Args:
      string: the string to check.

    Returns:
      True if the string passed is a flag that should be prioritized, False
      otherwise.
    """
    return IsFlag(string) and (_ShouldPrioritizeUnusedRequiredFlag(string) or
                               _ShouldPrioritizeUnusedLocationFlag(string))

  def _PrioritizedUnusedRequiredFlags(keys):
    """Ranks completions based on whether they're unused required flags.

    Args:
      keys: A list of all the autocomplete suggestions as they appear in the
      gcloud_tree.

    Returns:
      A sorted array with the keys of the input dictionary with unused, required
      flags appearing first.
    """
    return sorted(keys, key=_ShouldPrioritizeFlag, reverse=True)

  return _PrioritizedUnusedRequiredFlags(sorted(suggestions))


def CompleteCommandGroups(args):
  """Return possible commands and groups for completions."""
  if not args:
    return []

  if args[-1].token_type != parser.ArgTokenType.GROUP:
    return []

  return args[-1].tree['commands'].keys()
