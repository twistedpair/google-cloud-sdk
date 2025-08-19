# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Common logic for gemini cloud assist commands."""

import textwrap
from googlecloudsdk.core import resource


def InputMarkdownShort(observation):
  """Returns a short human-readable string representation of an input observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """

  ret = textwrap.dedent("""\
        ### {}
        {}
        """).format(
      observation["id"],
      observation["text"],
  )
  return ret


def ObservationMarkdownShort(observation):
  """Returns a short human-readable string representation of an observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """
  ret = textwrap.dedent("""\
        ### {}""").format(
      observation["title"] if "title" in observation else "No Title",
  )
  return ret


def HypothesisMarkdownShort(observation):
  """Returns a short human-readable string representation of a hypothesis observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """
  short_text = ""
  if "text" in observation:
    split_text = observation["text"].split("\n")
    if len(split_text) > 2:
      short_text = "\n".join(
          [s for s in split_text[:2] if not s.startswith("#")]
      )
    else:
      short_text = observation["text"]

  ret = textwrap.dedent("""\
        ### {}
        {}
        """).format(
      observation["title"] if "title" in observation else "No Title",
      short_text,
  )
  return ret


def InvestigationMarkdownShort(investigation):
  """Returns a short human-readable string representation of an investigation.

  There is no gaurentee of output stability over time.

  Args:
    investigation: A dict representing an investigation.

  Returns:
    A string representing the investigation.
  """
  long_format = textwrap.dedent("""\
        # {}
        Name: {}
        Status: {}
        ## Inputs
        {}
        ## Observations
        {}

        ## Hypotheses
        {}
        """).format(
      investigation["title"] if "title" in investigation else "No Title",
      investigation["name"],
      investigation["executionState"],
      "\n".join(map(InputMarkdownShort, investigation["inputs"])),
      "\n".join(map(ObservationMarkdownShort, investigation["observations"])),
      "\n".join(map(HypothesisMarkdownShort, investigation["hypotheses"])),
  )
  return long_format


def GetTimestamp(observation):
  """Extracts the start and end times from an observation.

  Args:
    observation: A dict representing an observation.

  Returns:
    A tuple of two strings: start_time and end_time.
  """
  start_time = "None"
  end_time = "None"
  if "timeIntervals" in observation:
    if "startTime" in observation["timeIntervals"][0]:
      start_time = observation["timeIntervals"][0]["startTime"]
    if "endTime" in observation["timeIntervals"][0]:
      end_time = observation["timeIntervals"][0]["endTime"]
  return start_time, end_time


def InputMarkdownDetailed(observation):
  """Returns a detailed human-readable string representation of an input observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """
  start_time, end_time = GetTimestamp(observation)

  relevant_resources = (
      "".join([f"- {r}\n" for r in observation["relevantResources"]])
      if "relevantResources" in observation
      else ""
  )

  ret = textwrap.dedent("""\
        ### {}
        Start Time: {}
        End Time: {}
        {}
        #### Relevant Resources
        {}
        """).format(
      observation["id"],
      start_time,
      end_time,
      observation["text"],
      relevant_resources,
  )
  return ret


def ObservationMarkdownDetailed(observation):
  """Returns a detailed human-readable string representation of an observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """
  start_time, end_time = GetTimestamp(observation)
  relevant_resources = (
      "".join([f"- {r}\n" for r in observation["relevantResources"]])
      if "relevantResources" in observation
      else ""
  )
  ret = textwrap.dedent("""\
        ### {}
        Type: {}
        Start Time: {}
        End Time: {}
        {}
        #### Relevant Resources
        {}
        """).format(
      observation["title"] if "title" in observation else "No Title",
      observation["observationType"],
      start_time,
      end_time,
      observation["text"],
      relevant_resources,
  )
  return ret


def HypothesisMarkdownDetailed(observation):
  """Returns a detailed human-readable string representation of a hypothesis observation.

  There is no gaurentee of output stability over time.

  Args:
    observation: A dict representing an observation.

  Returns:
    A string representing the observation.
  """
  # Hypotheses use level-3 headings, we want them to become level-4 headings
  lines = observation["text"].split("\n")
  for i in range(len(lines)):
    if lines[i].startswith("#"):
      lines[i] = "#" + lines[i]
  edited_text = "\n".join(lines)

  ret = textwrap.dedent("""\
        ### {}
        {}
        """).format(
      observation["title"] if "title" in observation else "No Title",
      edited_text,
  )
  return ret


def InvestigationMarkdownDetailed(investigation):
  """Returns a detailed human-readable string representation of an investigation.

  There is no gaurentee of output stability over time.

  Args:
    investigation: A dict representing an investigation.

  Returns:
    A string representing the investigation.
  """
  long_format = textwrap.dedent("""\
        # {}
        Name: {}
        Status: {}
        ## Inputs
        {}
        ## Observations
        {}
        ## Hypotheses
        {}
        """).format(
      investigation["title"] if "title" in investigation else "No Title",
      investigation["name"],
      investigation["executionState"],
      "\n".join(map(InputMarkdownDetailed, investigation["inputs"])),
      "\n".join(
          map(ObservationMarkdownDetailed, investigation["observations"])
      ),
      "\n".join(map(HypothesisMarkdownDetailed, investigation["hypotheses"])),
  )
  return long_format


def ReformatInvestigation(investigation):
  """Transforms an investigation into an alternate format of the investigation.

  This format will have observations grouped by type, with some filtered out for
  improved human readability.

  Args:
    investigation: A dict representing an investigation.

  Returns:
    A dict representing the investigation.
  """
  investigation = resource.resource_projector.MakeSerializable(investigation)
  inputs, observations, hypotheses = ExtractObservations(investigation)
  return {
      "name": investigation["name"],
      "title": investigation.get("title", "No Title"),
      "executionState": investigation["executionState"],
      "inputs": inputs,
      "observations": observations,
      "hypotheses": hypotheses,
  }


_IGNORED_OBSERVATION_TYPES = [
    "OBSERVATION_TYPE_STRUCTURED_INPUT",
    "OBSERVATION_TYPE_RELATED_RESOURCES",
    "OBSERVATION_TYPE_KNOWLEDGE",
]


def ExtractObservations(investigation):
  """Extracts observations from an investigation.

  Attempts to mimic UI behavior as much as possible.
  Any observations missing observationType, observerType, text, or title will be
  ignored.
  The observations are returned as inputs, observations, and hypotheses.

  Args:
    investigation: A dict representing an investigation.

  Returns:
    A tuple of three lists: inputs, observations, and hypotheses.
  """
  inputs = []
  observations = []
  hypotheses = []

  if "observations" not in investigation:
    return inputs, observations, hypotheses

  for observation in investigation["observations"].values():
    if (
        "observationType" not in observation
        or "observerType" not in observation
        or "text" not in observation
    ):
      # This observation doesn't meet the minimum qualifications to be shown.
      continue

    if observation["observationType"] in _IGNORED_OBSERVATION_TYPES:
      continue

    if observation["observerType"] == "OBSERVER_TYPE_USER":
      inputs.append(observation)
      continue

    if observation["observationType"] == "OBSERVATION_TYPE_HYPOTHESIS":
      hypotheses.append(observation)
      continue

    observations.append(observation)

  return inputs, observations, hypotheses
