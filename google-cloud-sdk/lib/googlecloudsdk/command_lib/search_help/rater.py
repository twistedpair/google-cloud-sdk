# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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

"""Contains a class to rate commands based on relevance."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.search_help import lookup


# TODO(b/67707688): When using "OR" style matching, add rating for how many
# terms are found. Currently this class assumes that all terms being searched
# are present in the command being rated, which fits with the current behavior
# in search_util.py.
class CommandRater(object):
  """A class to rate the results of searching a command."""

  # The below multipliers reflect heuristics for how "important" a term is
  # in a command based on where it's found.
  _COMMAND_NAME_MULTIPLIER = 1.0  # command name
  _ARG_NAME_MULTIPLIER = 0.5  # arg name (positional or flag)
  _PATH_MULTIPLIER = 0.5  # the command path
  _DEFAULT_MULTIPLIER = 0.25  # anything not controlled by other multipliers.

  def Rate(self, results):
    """Produce a simple relevance rating for a set of command search results.

    Returns a float in the range (0, 1]. For each term that's found, the rating
    is multiplied by a number reflecting how "important" its location is, with
    command name being the most and flag or positional names being the second
    most important.

    Args:
      results: {str: str}, dict of terms to locations where they were found.
        Only one location is provided for each term.

    Returns:
      rating: float, the rating of the results.
    """
    rating = 1.0
    locations = list(results.values())
    for location in locations:
      if location == lookup.NAME:
        rating *= self._COMMAND_NAME_MULTIPLIER
      elif location == lookup.PATH:
        rating *= self._PATH_MULTIPLIER
      elif (location.split(lookup.DOT)[0] in [lookup.FLAGS, lookup.POSITIONALS]
            and location.split(lookup.DOT)[-1] == lookup.NAME):
        rating *= self._ARG_NAME_MULTIPLIER
      else:
        rating *= self._DEFAULT_MULTIPLIER
    return rating


def Rate(results):
  """Get a rating for a command.

  Args:
    results: {str: str}, dict from terms to where they are found.

  Returns:
    (float) a relevance rating in the range (0, 1].
  """
  return CommandRater().Rate(results)
