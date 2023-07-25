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
from googlecloudsdk.command_lib.projects import util as project_util

_PROJECT_WARNING_MESSAGE = """Shutting down this project will immediately:
  - Stop all traffic and billing.
  - Start deleting resources.
  - Schedule the final deletion of the project after 30 days.
  - Block your access to the project.
  - Notify the owner of the project.

Learn more about the shutdown process at
https://cloud.google.com/resource-manager/docs/creating-managing-projects#shutting_down_projects
"""

_PROJECT_RISK_MESSAGE = (
    "WARNING: The risk of losing data or interrupting service "
    "when deleting this project is high"
)

_PROJECT_REASONS_PREFIX = " because in the past 30 days"

_SA_RISK_MESSAGE = (
    "WARNING: Deleting this service account is highly likely to cause"
    " interruptions, because in the last 90 days it had significant usage"
)

_POLICY_BINDING_DELETE_RISK_MESSAGE = (
    "WARNING: Removing this role is likely to cause interruptions, because it"
    " was used in the last 90 days"
)

_PROJECT_INSIGHT_TYPE = "google.resourcemanager.project.ChangeRiskInsight"

_SA_INSIGHT_TYPE = "google.iam.serviceAccount.ChangeRiskInsight"

_POLICY_BINDING_INSIGHT_TYPE = "google.iam.policy.ChangeRiskInsight"

_RECOMMENDATIONS_HOME_URL = (
    "https://console.cloud.google.com/home/recommendations"
)

_MAX_NUMBER_OF_REASONS = 3


def _GetIamPolicyBindingMatcher(member, role):
  """Returns a function that matches an insight by policy binding.

  Args:
    member: Member string to fully match.
    role: Member role to fully match.

  Returns:
    A function that matches an insight object by policy binding. The returned
    function returns true iff both the member and the role match.
  """

  def Matcher(gcloud_insight):
    matches_member = False
    matches_role = False
    for additional_property in gcloud_insight.content.additionalProperties:
      if additional_property.key == "risk":
        for p in additional_property.value.object_value.properties:
          if p.key == "usageAtRisk":
            for f in p.value.object_value.properties:
              if f.key == "iamPolicyUtilization":
                for iam_p in f.value.object_value.properties:
                  if iam_p.key == "member":
                    if iam_p.value.string_value == member:
                      matches_member = True
                  if iam_p.key == "role":
                    if iam_p.value.string_value == role:
                      matches_role = True
    return matches_member and matches_role

  return Matcher


def _GetInsightLink(gcloud_insight):
  """Returns a message with a link to the associated recommendation.

  Args:
    gcloud_insight: Insight object returned by the recommender API.

  Returns:
    A string message with a link to the associated recommendation.
  """
  return (
      "Before proceeding, view the risk assessment at {0}/view-link/{1}"
  ).format(_RECOMMENDATIONS_HOME_URL, gcloud_insight.name)


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


def _GetDeletionRiskMessage(gcloud_insight, risk_message, reasons_prefix=""):
  """Returns a risk message for resource deletion.

  Args:
    gcloud_insight: Insight object returned by the recommender API.
    risk_message: String risk message.
    reasons_prefix: String prefix before listing reasons.

  Returns:
    Formatted string risk message with reasons if any. The reasons are
    extracted from the gcloud_insight object.
  """
  reasons = _GetResourceRiskReasons(gcloud_insight)[:_MAX_NUMBER_OF_REASONS]
  if not reasons:
    return risk_message + ".\n"
  message = "{0}{1}:\n".format(risk_message, reasons_prefix)
  message += "".join("  - {0}\n".format(reason) for reason in reasons)
  return message


def _GetRiskInsight(
    release_track, project_id, insight_type, request_filter=None, matcher=None
):
  """Returns the first insight fetched by the recommender API.

  Args:
    release_track: Release track of the recommender.
    project_id: Project ID.
    insight_type: String insight type.
    request_filter: Optional string filter for the recommender.
    matcher: Matcher for the insight object. None means match all.

  Returns:
    Insight object returned by the recommender API. Returns 'None' if no
    matching insights were found. Returns the first insight object that matches
    the matcher. If no matcher, returns the first insight object fetched.
  """
  client = insight.CreateClient(release_track)
  parent_name = ("projects/{0}/locations/global/insightTypes/{1}").format(
      project_id, insight_type
  )
  result = client.List(
      parent_name, page_size=100, limit=None, request_filter=request_filter
  )
  for r in result:
    if not matcher:
      return r
    if matcher(r):
      return r
  return None


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
  risk_insight = _GetRiskInsight(
      release_track, project_id, _PROJECT_INSIGHT_TYPE
  )
  if risk_insight:
    return "{0}\n{1}\n{2}".format(
        _PROJECT_WARNING_MESSAGE,
        _GetDeletionRiskMessage(
            gcloud_insight=risk_insight,
            risk_message=_PROJECT_RISK_MESSAGE,
            reasons_prefix=_PROJECT_REASONS_PREFIX,
        ),
        _GetInsightLink(risk_insight),
    )
  # If there are no risks to deleting a project,
  # return a standard warning message.
  return _PROJECT_WARNING_MESSAGE


def GetServiceAccountDeletionRisk(release_track, project_id, service_account):
  """Returns a risk assesment message for service account deletion.

  Args:
    release_track: Release track of the recommender.
    project_id: String project ID.
    service_account: Service Account email ID.

  Returns:
    String Active Assist risk warning message to be displayed in
    service account deletion prompt.
    If no risk exists, then returns 'None'.
  """
  project_number = project_util.GetProjectNumber(project_id)
  target_filter = (
      "targetResources: //iam.googleapis.com/projects/{0}/serviceAccounts/{1}"
  ).format(project_number, service_account)
  risk_insight = _GetRiskInsight(
      release_track, project_id, _SA_INSIGHT_TYPE, request_filter=target_filter
  )
  if risk_insight:
    return "{0}\n{1}".format(
        _GetDeletionRiskMessage(risk_insight, _SA_RISK_MESSAGE),
        _GetInsightLink(risk_insight),
    )
  return None


def GetIamPolicyBindingDeletionRisk(
    release_track, project_id, member, member_role
):
  """Returns a risk assesment message for IAM policy binding deletion.

  Args:
    release_track: Release track of the recommender.
    project_id: String project ID.
    member: IAM policy binding member.
    member_role: IAM policy binding member role.

  Returns:
    String Active Assist risk warning message to be displayed in IAM policy
    binding deletion prompt.
    If no risk exists, then returns 'None'.
  """
  # Remove prefixes like "user:", "group:", etc. from member
  # because the recommender generates a member id only.
  member = member[(member.find(":") + 1) :]
  policy_matcher = _GetIamPolicyBindingMatcher(member, member_role)
  risk_insight = _GetRiskInsight(
      release_track,
      project_id,
      _POLICY_BINDING_INSIGHT_TYPE,
      matcher=policy_matcher,
  )
  if risk_insight:
    return "{0}\n{1}".format(
        _GetDeletionRiskMessage(
            risk_insight, _POLICY_BINDING_DELETE_RISK_MESSAGE
        ),
        _GetInsightLink(risk_insight),
    )
  return None
