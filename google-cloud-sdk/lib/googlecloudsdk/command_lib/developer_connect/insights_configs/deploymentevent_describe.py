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
"""Commands for Developer Connect Insights Config Deployment Events."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.artifacts import vulnerabilities
from googlecloudsdk.api_lib.containeranalysis import requests as ca_requests
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources


def AddArtifactDetailsToResponse(response, args):
  """A hook function to modify the response of a deployment-event describe.

  This function enriches the deployment event with vulnerability and package
  dependency details by calling the Container Analysis API for each
  artifactDeployment. The response is converted to a dictionary to allow adding
  custom fields.

  Args:
    response: The original response from the API, expected to be a
      DeploymentEvent object.
    args: Command line arguments, contains the project.

  Returns:
    A dictionary representing the deployment event with added vulnerability
    information.
  """
  # The project is provided via the --project flag.
  project = args.project
  if not response:
    return {}

  event = response
  # Convert the proto message to a mutable dictionary.
  event_dict = encoding.MessageToPyValue(event)

  # Check for and iterate through artifact deployments.
  if hasattr(event, "artifactDeployments") and event.artifactDeployments:
    if "artifactDeployments" in event_dict:
      for artifact_dict in event_dict["artifactDeployments"]:
        artifact_ref = artifact_dict.get("artifactReference")
        if not artifact_ref:
          continue

        # Fetch and add package dependencies.
        artifact_dict["packages"] = (
            _FetchAndParsePackageDependencies(project, artifact_ref) or []
        )

        # Get vulnerabilities for the artifactReference from Container Analysis.
        # GetVulnerabilities queries for occurrences of kind "VULNERABILITY".
        cve_names = []
        try:
          # Container Analysis resource URIs often require the https:// prefix.
          resource_uri = "https://" + artifact_ref
          occurrences = vulnerabilities.GetVulnerabilities(
              project, resource_uri, None
          )
          occurrences_list = list(occurrences)
          # Process each occurrence to extract relevant vulnerability info.
          for occ in occurrences_list:
            if occ.vulnerability and occ.vulnerability.shortDescription:
              cve_names.append(occ.vulnerability.shortDescription)

          artifact_dict["vulnerabilities"] = cve_names
        except (apitools_exceptions.HttpError, exceptions.Error) as e:
          # Log the error and continue processing other artifacts.
          print(f"Error fetching vulnerabilities for {artifact_ref}: {e}")
          artifact_dict["vulnerabilities"] = []

  return event_dict


def _ParseSourceCommitUri(uri):
  """Parses a source commit URI to extract the base repo URL and commit SHA.

  Args:
    uri: The source commit URI string (e.g.,
      https://github.com/owner/repo/commit/sha).

  Returns:
    A tuple (base_repo_url, commit_sha) or (None, None) if parsing fails.
  """
  # Regex to match GitHub/GitLab/Bitbucket commit URIs
  # Group 1: Base repository URL
  # Group 2: Commit SHA
  match = re.match(
      r"(https?://(?:github\.com|gitlab\.com|bitbucket\.org)/[^/]+/[^/]+)/commit/([0-9a-fA-F]{40})",
      uri,
  )
  if match:
    return match.group(1), match.group(2)
  return None, None


def _ConstructGitDiffUri(base_repo_url, prev_sha, curr_sha):
  """Constructs a Git-diff URI for GitHub, GitLab, or Bitbucket.

  Args:
    base_repo_url: The base URL of the repository (e.g.,
      https://github.com/owner/repo).
    prev_sha: The commit SHA of the previous deployment.
    curr_sha: The commit SHA of the current deployment.

  Returns:
    The Git-diff URI string or None if the provider is not supported.
  """
  if "github.com" in base_repo_url:
    return f"{base_repo_url}/compare/{prev_sha}...{curr_sha}"
  elif "gitlab.com" in base_repo_url:
    return f"{base_repo_url}/-/compare/{prev_sha}...{curr_sha}"
  elif "bitbucket.org" in base_repo_url:
    # Bitbucket uses a different compare format
    return f"{base_repo_url}/compare/{prev_sha}..{curr_sha}"
  return None


def _GetLatestSourceCommitUri(artifact_deployments):
  """Gets the source commit URI from the artifact deployment with the latest deployTime."""
  if not artifact_deployments:
    return None

  latest_ad = None
  latest_deploy_time = None

  for ad in artifact_deployments:
    deploy_time_str = ad.get("deployTime")
    source_uris = ad.get("sourceCommitUris")

    if deploy_time_str and source_uris:
      # ISO format strings can be compared directly to find the latest time.
      if latest_deploy_time is None or deploy_time_str > latest_deploy_time:
        latest_deploy_time = deploy_time_str
        latest_ad = ad

  if latest_ad:
    # Return 1st URI from the sourceCommitUris of the latest artifactdeployment.
    return latest_ad.get("sourceCommitUris")[0]
  return None


def _FetchAndParsePackageDependencies(project, artifact_ref):
  """Fetches and parses PACKAGE occurrences from Container Analysis."""
  package_deps = []
  try:
    # Construct filter for PACKAGE occurrences for the specific artifact_ref
    # Container Analysis resource URIs often require the https:// prefix.
    resource_uri = "https://" + artifact_ref
    res_filter = f'kind="PACKAGE" AND resource_url="{resource_uri}"'
    # Use ca_requests to list occurrences.
    occurrences = ca_requests.ListOccurrences(project, res_filter)
    occurrences_list = list(occurrences)

    for occ in occurrences_list:
      if occ.package:
        pkg = occ.package
        detail = {
            "name": pkg.name,
            "version": pkg.version.fullName if pkg.version else None,
        }
        package_deps.append(detail)
  except (apitools_exceptions.HttpError, exceptions.Error) as e:
    print(f"Error fetching package dependencies for {artifact_ref}: {e}")
    return []

  return package_deps


def _ComputeOverallPackageDiff(current_ad, previous_ad):
  """Computes overall added, removed, and changed packages."""
  curr_map = {}
  for ad in current_ad:
    for p in ad.get("packages", []):
      if p.get("name") and p.get("version"):
        curr_map[p["name"]] = p["version"]

  prev_map = {}
  for ad in previous_ad:
    for p in ad.get("packages", []):
      if p.get("name") and p.get("version"):
        prev_map[p["name"]] = p["version"]

  added_pkgs = []
  removed_pkgs = []
  changed_vers = {}

  # Find added and changed
  for pkg_name, curr_ver in curr_map.items():
    if pkg_name not in prev_map:
      added_pkgs.append(f"{pkg_name}=={curr_ver}")
    elif prev_map[pkg_name] != curr_ver:
      changed_vers[pkg_name] = f"{prev_map[pkg_name]} -> {curr_ver}"

  # Find removed
  for pkg_name, prev_ver in prev_map.items():
    if pkg_name not in curr_map:
      removed_pkgs.append(f"{pkg_name}=={prev_ver}")

  diff = {}
  if added_pkgs:
    diff["addedPackages"] = ", ".join(sorted(added_pkgs))
  if removed_pkgs:
    diff["removedPackages"] = ", ".join(sorted(removed_pkgs))
  if changed_vers:
    diff["changedVersions"] = changed_vers

  return diff


def _PopulateVulnerabilities(artifact_dicts, project):
  """Fetches and populates vulnerabilities for a list of artifact deployments."""
  if not artifact_dicts:
    return
  for artifact_dict in artifact_dicts:
    artifact_ref = artifact_dict.get("artifactReference")
    if not artifact_ref or "vulnerabilities" in artifact_dict:
      continue
    cve_names = []
    try:
      resource_uri = "https://" + artifact_ref
      occurrences = vulnerabilities.GetVulnerabilities(
          project, resource_uri, None
      )
      for occ in occurrences:
        if occ.vulnerability and occ.vulnerability.shortDescription:
          cve_names.append(occ.vulnerability.shortDescription)
      artifact_dict["vulnerabilities"] = cve_names
    except (apitools_exceptions.HttpError, exceptions.Error) as e:
      print(f"Error fetching vulnerabilities for {artifact_ref}: {e}")
      artifact_dict["vulnerabilities"] = []


def _ComputeOverallVulnerabilityDiff(all_curr_vulns, all_prev_vulns):
  """Computes overall added and removed vulnerabilities."""
  new_vulnerabilities = sorted(list(all_curr_vulns - all_prev_vulns))
  removed_vulnerabilities = sorted(list(all_prev_vulns - all_curr_vulns))

  diff = {}
  if new_vulnerabilities:
    diff["addedVulnerabilities"] = ", ".join(new_vulnerabilities)
  if removed_vulnerabilities:
    diff["removedVulnerabilities"] = ", ".join(removed_vulnerabilities)
  return diff


def AddPreviousDiffToResponse(response, args):
  """A hook function to potentially add previous deployment diff information.

  This function computes and adds Git-diff, package diff, and vulnerability diff
  information between the current and the immediately preceding deployment event
  for the same runtime, if the --show-previous-diff flag is set.

  Args:
    response: The original response from the API, expected to be a
      DeploymentEvent object.
    args: Command line arguments.

  Returns:
    The event dictionary, potentially modified with diff information.
  """
  if not args.show_previous_diff:
    return response

  event_dict = response
  project = args.project

  # Initialize diff output structure
  event_dict["previousDeploymentDiff"] = {
      "gitDiffUri": {},
      "artifactDiffs": {
          "newArtifacts": [],
          "packageDiff": {"newPackages": {}, "changedVersions": {}},
          "vulnerabilityDiff": {},
      },
  }

  # 1. Extract Parent Insights Config and Runtime URI
  current_deployment_name = event_dict.get("name")
  if not current_deployment_name:
    # Return early if the current deployment name is missing.
    return event_dict

  try:
    resource_ref = resources.REGISTRY.Parse(
        current_deployment_name,
        collection="developerconnect.projects.locations.insightsConfigs.deploymentEvents",
    )
    insights_config_parent = resource_ref.Parent().RelativeName()
  except resources.InvalidResourceException as e:
    print(
        "--- AddPreviousDiffToResponse: Error parsing resource name"
        f" '{current_deployment_name}': {e} ---"
    )
    return event_dict

  runtime_uri = None
  runtime_config = event_dict.get("runtimeConfig")
  if runtime_config and runtime_config.get("uri"):
    runtime_uri = runtime_config["uri"]
  else:
    return event_dict

  # Fetch all deploymentEvents for the insightsConfig and runtime uri.
  client = apis.GetClientInstance("developerconnect", "v1")
  messages = apis.GetMessagesModule("developerconnect", "v1")
  list_request = messages.DeveloperconnectProjectsLocationsInsightsConfigsDeploymentEventsListRequest(
      parent=insights_config_parent,
      filter=f'runtime_config.uri = "{runtime_uri}"',
      pageSize=1000,
  )

  try:
    list_response = (
        client.projects_locations_insightsConfigs_deploymentEvents.List(
            list_request
        )
    )
    all_events_dicts = [
        encoding.MessageToPyValue(e)
        for e in (list_response.deploymentEvents or [])
    ]
  except Exception as e:  # pylint: disable=broad-except
    return event_dict

  if not all_events_dicts:
    return event_dict

  # Sort events by deployTime in descending order.
  def _SortKey(event_dict):
    return event_dict.get("deployTime", "")

  sorted_events = sorted(all_events_dicts, key=_SortKey, reverse=True)

  # Find the index of the current event in the sorted list.
  current_event_index = -1
  for i, event in enumerate(sorted_events):
    if event.get("name") == current_deployment_name:
      current_event_index = i
      break

  # If the current event is the first event, return early.
  if current_event_index == -1:
    return event_dict

  # Find the previous deployment event if any.
  previous_deployment = None
  if current_event_index + 1 < len(sorted_events):
    previous_deployment = sorted_events[current_event_index + 1]
    print(f"Found previous deployment: {previous_deployment.get('name')}")
  else:
    return event_dict

  # Compute Overall Git-Diff URI
  curr_source_uri = _GetLatestSourceCommitUri(
      event_dict.get("artifactDeployments", [])
  )
  prev_source_uri = _GetLatestSourceCommitUri(
      previous_deployment.get("artifactDeployments", [])
  )

  # Construct Git Diff URI
  if curr_source_uri and prev_source_uri:
    curr_base, curr_sha = _ParseSourceCommitUri(curr_source_uri)
    prev_base, prev_sha = _ParseSourceCommitUri(prev_source_uri)

    if (
        curr_base
        and curr_sha
        and prev_base
        and prev_sha
        and curr_base == prev_base
        and curr_sha != prev_sha
    ):
      git_diff_uri = _ConstructGitDiffUri(curr_base, prev_sha, curr_sha)
      if git_diff_uri:
        event_dict["previousDeploymentDiff"]["gitDiffUri"] = git_diff_uri
      else:
        print(" Failed to construct Git Diff URI.")
    else:
      print("Skipping Git Diff computation due to parsing issues or same SHAs.")
  else:
    print("Skipping Git Diff computation due to missing source URIs.")

  # Compute Package and Vulnerability Diffs per Artifact
  current_artifact_deployments = event_dict.get("artifactDeployments", [])
  previous_artifact_deployments = previous_deployment.get(
      "artifactDeployments", []
  )

  # Fetch Package Dependencies for all artifacts
  for ad in current_artifact_deployments:
    artifact_ref = ad.get("artifactReference")
    if artifact_ref and "packages" not in ad:
      ad["packages"] = (
          _FetchAndParsePackageDependencies(project, artifact_ref) or []
      )
  for ad in previous_artifact_deployments:
    artifact_ref = ad.get("artifactReference")
    if artifact_ref and "packages" not in ad:
      ad["packages"] = (
          _FetchAndParsePackageDependencies(project, artifact_ref) or []
      )

  # Compute Overall Package Diff
  package_diff = _ComputeOverallPackageDiff(
      current_artifact_deployments, previous_artifact_deployments
  )
  event_dict["previousDeploymentDiff"]["artifactDiffs"][
      "packageDiff"
  ] = package_diff

  # Populate vulnerabilities for both current and previous deployments
  _PopulateVulnerabilities(current_artifact_deployments, project)
  _PopulateVulnerabilities(previous_artifact_deployments, project)

  # Collect all vulnerabilities from current and previous deployments
  all_curr_vulns = set()
  for curr_ad in current_artifact_deployments:
    all_curr_vulns.update(curr_ad.get("vulnerabilities", []))

  all_prev_vulns = set()
  for prev_ad in previous_artifact_deployments:
    all_prev_vulns.update(prev_ad.get("vulnerabilities", []))

  # Compute overall vulnerability diff
  vulnerability_diff = _ComputeOverallVulnerabilityDiff(
      all_curr_vulns, all_prev_vulns
  )
  event_dict["previousDeploymentDiff"]["artifactDiffs"][
      "vulnerabilityDiff"
  ] = vulnerability_diff

  # Identify New Artifacts
  prev_artifacts_map = {
      ad.get("artifactReference"): ad
      for ad in previous_artifact_deployments
      if ad.get("artifactReference")
  }
  new_artifacts = [
      curr_ad.get("artifactReference")
      for curr_ad in current_artifact_deployments
      if curr_ad.get("artifactReference") not in prev_artifacts_map
  ]
  event_dict["previousDeploymentDiff"]["artifactDiffs"][
      "newArtifacts"
  ] = new_artifacts

  return event_dict["previousDeploymentDiff"]
