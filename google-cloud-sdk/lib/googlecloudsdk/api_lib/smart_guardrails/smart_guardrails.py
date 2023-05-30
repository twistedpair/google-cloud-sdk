# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Smart Guardrails Recommendation Utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.recommender import insight

_WARNING_MESSAGE = """Shutting down this project will immediately:
  - Stop all traffic and billing.
  - Start deleting resources.
  - Schedule the final deletion of the project after 30 days.
  - Block your access to the project.
  - Notify the owner of the project.

Learn more about the shutdown process at
https://cloud.google.com/resource-manager/docs/creating-managing-projects#shutting_down_projects
"""

_RISK_MESSAGE = (
    "WARNING: The risk of losing data or interrupting service "
    "when deleting this project is high"
)

_RECOMMENDATIONS_HOME_URL = (
    "https://console.cloud.google.com/home/recommendations"
)

_MAX_NUMBER_OF_REASONS = 3


def _GetAssociatedRecommendationLink(gcloud_insight, project_id):
  """Returns a message with a link to the associated recommendation.

  Args:
    gcloud_insight: Insight object returned by the recommender API.
    project_id: Project ID.

  Returns:
    A string message with a link to the associated recommendation.
  """
  for reco in gcloud_insight.associatedRecommendations:
    if reco.recommendation:
      return (
          "Before proceeding, view the risk assessment at {0}/view-link/{1}"
      ).format(_RECOMMENDATIONS_HOME_URL, reco.recommendation)
  return (
      "Failed to get an associated recommendation link. "
      "All recommendations can be viewed at {0}?project={1}"
  ).format(_RECOMMENDATIONS_HOME_URL, project_id)


def _GetResourceRiskReasons(gcloud_insight):
  """Extracts a list of string reasons from the resource change insight.

  Args:
    gcloud_insight: Insight object returned by the recommender API.

  Returns:
    A list of strings. If no reasons could be found, then returns empty list.
  """
  reasons = []
  for additional_property in gcloud_insight.content.additionalProperties:
    if additional_property.key == "importance":
      for p in additional_property.value.object_value.properties:
        if p.key == "detailedReasons":
          for reason in p.value.array_value.entries:
            reasons.append(reason.string_value)
  return reasons


def _GetDeletionRiskMessage(gcloud_insight):
  """Returns a risk message for project deletion.

  Args:
    gcloud_insight: Insight object returned by the recommender API.

  Returns:
    String risk message with reasons if any.
  """
  reasons = _GetResourceRiskReasons(gcloud_insight)[:_MAX_NUMBER_OF_REASONS]
  if not reasons:
    return _RISK_MESSAGE + ".\n"
  message = _RISK_MESSAGE + " because in the past 30 days:\n"
  message += "".join("  - {0}\n".format(reason) for reason in reasons)
  return message


def GetProjectDeletionRisk(release_track, project_id):
  """Returns a risk assesment message for project deletion.

  Args:
    release_track: Release track of the recommender.
    project_id: Project ID.

  Returns:
    String message prompt to be displayed for project deletion.
    If the project deletion is high risk, the message includes the
    Active Assist warning.
  """
  client = insight.CreateClient(release_track)
  parent_name = (
      "projects/{0}/locations/global/insightTypes/"
      "google.resourcemanager.project.ChangeRiskInsight"
  ).format(project_id)
  result = client.List(parent_name, page_size=1, limit=1)
  for r in result:
    # Return the first risk insight as we expect only one
    # change risk insight per project.
    return "{0}\n{1}\n{2}".format(
        _WARNING_MESSAGE,
        _GetDeletionRiskMessage(r),
        _GetAssociatedRecommendationLink(r, project_id),
    )
  # If there are no risks to deleting a project,
  # return a standard warning message.
  return _WARNING_MESSAGE
