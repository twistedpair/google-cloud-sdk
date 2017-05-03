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

from googlecloudsdk.command_lib.shell import gcloud_parser as parser
from googlecloudsdk.command_lib.shell.gcloud_tree import gcloud_tree
from googlecloudsdk.core import properties
from prompt_toolkit.completion import Completer
from prompt_toolkit.completion import Completion


_LOCATION_FLAGS = ['--global', '--location', '--region', '--zone']


class ShellCliCompleter(Completer):
  """A prompt_toolkit shell CLI completer."""

  def __init__(self):
    self.experimental_autocomplete_enabled = ExperimentalAutocompleteEnabled()

  def get_completions(self, doc, complete_event):
    """Yields the completions for doc.

    Args:
      doc: A Document instance containing the shell command line to complete.
      complete_event: The CompleteEvent that triggered this completion.

    Yields:
      Completion instances for doc.
    """
    # Check there's at least one invocation
    invocations = parser.ParseLine(doc.text_before_cursor)
    if not invocations:
      return
    invocation = invocations[-1]

    # Check there's at least one token in the invocation
    tokens = invocation.tokens
    if not tokens:
      return

    # Only allow gcloud-related commands
    if tokens[0].value != 'gcloud':
      gcloud_token = parser.ArgToken('gcloud', parser.ArgTokenType.GROUP,
                                     gcloud_tree, 0, 0)
      tokens = ([gcloud_token] + tokens)
      invocation = parser.GcloudInvocation(tokens)

    last_token = tokens[-1]
    last_token_name = last_token.value
    offset = -len(last_token_name)
    suggestions = last_token.tree.get('commands', {})

    # Autocomplete commands and groups after spaces
    if IsGroup(last_token):
      if CursorAheadOfToken(doc.cursor_position, last_token):
        offset = last_token.end - doc.cursor_position + 1
        for completion in invocation.GetPossibleCommandGroups():
          yield Completion(completion, offset)
        return
    elif IsFlag(last_token_name):
      suggestions = FilterHiddenFlags(invocation.GetPossibleFlags())
      if CursorAheadOfToken(doc.cursor_position, last_token):
        offset = 0
        # Check if the flag has a set of choices to choose from
        choices = suggestions.get(last_token.value, {}).get('choices', [])
        for choice in choices:
          yield Completion(choice, offset)
        return
    elif IsFlagArg(last_token):
      suggestions = FilterHiddenFlags(invocation.GetPossibleFlags())
      flag_token = tokens[-2]
      if not CursorAheadOfToken(doc.cursor_position, last_token):
        # Check if the flag has a set of choices to choose from
        choices = suggestions.get(flag_token.value, {}).get('choices', [])
        for choice in choices:
          if choice.lower().startswith(last_token_name.lower()):
            yield Completion(choice, offset)
      return

    def _GetRankedCompletions():
      if self.experimental_autocomplete_enabled:
        return RankedCompletions(suggestions, invocation)
      else:
        return sorted(suggestions)

    def _DisplayTextForChoice(choice):
      """Returns the appropriate display text for the given choice.

      If the choice is a non-bool flag and experimental autocomplete is enabled,
      an equal sign followed by the flag's metavariables will be shown.
      Otherwise, only the choice name will be shown.

      Args:
        choice: the choice for which to create the display text.

      Returns:
        The appropriate display text for the given choice.
      """
      display_text = choice
      if self.experimental_autocomplete_enabled:
        if IsFlag(choice):
          flag_type = suggestions[choice].get('type', None)
          if flag_type != 'bool':
            display_text += '='
            flag_arg_value = suggestions[choice].get('value', '')
            if flag_type == 'list' or flag_type == 'dict':
              display_text += '[' + flag_arg_value + ',...]'
            else:
              display_text += flag_arg_value
      return display_text

    def _MetaTextForChoice(choice):
      if (self.experimental_autocomplete_enabled and
          FlagIsRequired(suggestions[choice])):
        return 'required'

    ranked_completions = _GetRankedCompletions()
    for choice in ranked_completions:
      if choice.startswith(last_token_name):
        yield Completion(
            choice,
            offset,
            display=_DisplayTextForChoice(choice),
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


def CursorAheadOfToken(cursor_position, token):
  """Returns whether the cursor is ahead of the given token.

  Args:
    cursor_position: the position of the cursor
    token: the token to check

  Returns:
    True if the cursor is ahead of the given token, False otherwise.
  """
  return cursor_position > token.end


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


def IsGroup(token):
  """Returns whether the passed token is a group token.

  Args:
    token: the token to check.

  Returns:
    True if the passed token is a group, False otherwise.
  """
  return token.token_type == parser.ArgTokenType.GROUP


def IsFlagArg(token):
  """Returns whether the passed token is a flag argument token.

  Args:
    token: the token to check.

  Returns:
    True if the passed token is a flag argument, False otherwise.
  """
  return token.token_type == parser.ArgTokenType.FLAG_ARG


def IsEmptyFlagArg(token):
  """Returns whether the passed token is an empty-valued flag argument token.

  Args:
    token: the token to check.

  Returns:
    True if the passed token is an empty-valued flag argument, False otherwise.
  """
  return IsFlagArg(token) and not token.value


def RankedCompletions(suggestions, invocation):
  """Ranks a dictionary of completions based on different priorities.

  Args:
    suggestions: A dictionary of all the autocomplete suggestions as they appear
    in the gcloud_tree.
    invocation: A GcloudInvocation for which to rank the completions.

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
    return flag in [token.value for token in invocation.flags]

  def _ShouldPrioritizeUnusedRequiredFlag(string):
    """Returns whether the passed string is an unused required flag.

    Args:
      string: the string to check.

    Returns:
      True if the string passed is an unused required flag, False otherwise.
    """
    return (IsFlag(string) and FlagIsRequired(suggestions[string]) and
            not _FlagAlreadyUsed(string))

  def _FlagFromGroupAlreadyUsed(flag_group):
    """Return whether any of the flags belonging to the group has been used.

    Args:
      flag_group: an iterable containing strings with the names of the flags for
      which to check whether any of them have already been used.

    Returns:
      True if any flag in the group has already been used, False otherwise.
    """
    return any(_FlagAlreadyUsed(flag) for flag in flag_group)

  def _ShouldPrioritizeUnusedLocationFlag(string):
    """Returns whether the passed string is an unused location flag.

    Unused in this particular context means not only that the actual flag being
    tested has been used, but also that no other location flag has been used
    before (that is, location flags are mutually exclusive for the purpose of
    prioritization).

    Args:
      string: the flag to check.

    Returns:
      True if the string passed is an unused location flag, False otherwise.
    """
    return (IsFlag(string) and string in _LOCATION_FLAGS and
            not _FlagFromGroupAlreadyUsed(_LOCATION_FLAGS))

  def _PrioritizedUnusedRequiredFlags(keys):
    """Ranks completions based on whether they're unused required flags.

    Args:
      keys: A list of all the autocomplete suggestions as they appear in the
      gcloud_tree.

    Returns:
      A sorted array with the keys of the input dictionary with unused, required
      flags appearing first.
    """
    res = sorted(keys, key=_ShouldPrioritizeUnusedLocationFlag, reverse=True)
    return sorted(res, key=_ShouldPrioritizeUnusedRequiredFlag, reverse=True)

  return _PrioritizedUnusedRequiredFlags(sorted(suggestions))
