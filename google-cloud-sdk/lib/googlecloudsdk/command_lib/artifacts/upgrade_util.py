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
"""Utility for interacting with `artifacts docker upgrade` command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from apitools.base.py import encoding
import frozendict
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.api_lib.asset import client_util as asset
from googlecloudsdk.api_lib.cloudresourcemanager import projects_api as crm
from googlecloudsdk.command_lib.artifacts import requests as artifacts

_DOMAIN_TO_BUCKET_PREFIX = frozendict.frozendict({
    "gcr.io": "",
    "us.gcr.io": "us.",
    "asia.gcr.io": "asia.",
    "eu.gcr.io": "eu.",
})

_REPO_ADMIN = "roles/artifactregistry.repoAdmin"
_WRITER = "roles/artifactregistry.writer"
_READER = "roles/artifactregistry.reader"

# In order of most to least privilege, so we can grant the most privileged role.
_AR_ROLES = (_REPO_ADMIN, _WRITER, _READER)

# Set of GCS permissions for GCR that are relevant to AR.
_PERMISSIONS = (
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "storage.objects.delete",
)

# Maps a GCS permission for GCR to an equivalent AR role.
_PERMISSION_TO_ROLE = frozendict.frozendict({
    "storage.objects.get": _READER,
    "storage.objects.list": _READER,
    "storage.objects.create": _WRITER,
    "storage.objects.delete": _REPO_ADMIN,
})

_ANALYSIS_NOT_FULLY_EXPLORED = (
    "Too many IAM policies. Analysis cannot be fully completed."
)


def bucket_suffix(project):
  chunks = project.split(":", 1)
  if len(chunks) == 2:
    # domain-scoped project
    return "{0}.{1}.a.appspot.com".format(chunks[1], chunks[0])
  return project + ".appspot.com"


def bucket_resource_name(domain, project):
  prefix = _DOMAIN_TO_BUCKET_PREFIX[domain]
  suffix = bucket_suffix(project)
  return "//storage.googleapis.com/{0}artifacts.{1}".format(prefix, suffix)


def iam_policy(domain, project):
  """Generates an AR-equivalent IAM policy for a GCR registry.

  Args:
    domain: The domain of the GCR registry.
    project: The project of the GCR registry.

  Returns:
    An iam.Policy.

  Raises:
    Exception: A problem was encountered while generating the policy.
  """
  bucket = bucket_resource_name(domain, project)
  root = get_root(project)
  analysis = analyze_iam_policy(_PERMISSIONS, bucket, root)

  # If we see any false fullyExplored, that indicates that AnalyzeIamPolicy is
  # returning incomplete information, so the generated policy might be wrong,
  # so we conservatively bail out in that case.
  if not analysis.fullyExplored or not analysis.mainAnalysis.fullyExplored:
    errors = list(err.cause for err in analysis.mainAnalysis.nonCriticalErrors)
    error_msg = "\n".join(errors)
    raise ar_exceptions.ArtifactRegistryError(error_msg)

  perm_to_members = collections.defaultdict(set)
  for result in analysis.mainAnalysis.analysisResults:
    if not result.fullyExplored:
      raise ar_exceptions.ArtifactRegistryError(_ANALYSIS_NOT_FULLY_EXPLORED)

    if result.iamBinding.condition is not None:
      # AR doesn't support IAM conditions.
      raise ar_exceptions.ArtifactRegistryError(
          "Conditional IAM binding is not supported."
      )

    members = set()
    for member in result.iamBinding.members:
      if is_convenience(member):
        # convenience values are GCR legacy. They are not needed in AR.
        continue
      members.add(member)

    for acl in result.accessControlLists:
      for access in acl.accesses:
        perm = access.permission
        perm_to_members[perm].update(members)

  role_to_members = collections.defaultdict(set)
  for perm, members in perm_to_members.items():
    role = _PERMISSION_TO_ROLE[perm]
    role_to_members[role].update(members)

  # Convert the map to an iam.Policy object so that gcloud can format it nicely.
  messages = artifacts.GetMessages()
  bindings = list()

  # Grant the most privileged role to a member.
  upgraded_members = set()
  for role in _AR_ROLES:
    members = role_to_members[role]
    members.difference_update(upgraded_members)
    if not members:
      continue
    upgraded_members.update(members)
    bindings.append(
        messages.Binding(
            role=role,
            members=tuple(members),
        )
    )

  return messages.Policy(bindings=bindings)


def is_convenience(s):
  return (
      s.startswith("projectOwner:")
      or s.startswith("projectEditor:")
      or s.startswith("projectViewer:")
  )


def analyze_iam_policy(permissions, resource, scope):
  """Calls AnalyzeIamPolicy for the given resource.

  Args:
    permissions: for the access selector
    resource: for the resource selector
    scope: for the scope

  Returns:
    An CloudassetAnalyzeIamPolicyResponse.
  """
  client = asset.GetClient()
  service = client.v1
  messages = asset.GetMessages()

  encoding.AddCustomJsonFieldMapping(
      messages.CloudassetAnalyzeIamPolicyRequest,
      "analysisQuery_resourceSelector_fullResourceName",
      "analysisQuery.resourceSelector.fullResourceName",
  )
  encoding.AddCustomJsonFieldMapping(
      messages.CloudassetAnalyzeIamPolicyRequest,
      "analysisQuery_accessSelector_permissions",
      "analysisQuery.accessSelector.permissions",
  )

  return service.AnalyzeIamPolicy(
      messages.CloudassetAnalyzeIamPolicyRequest(
          analysisQuery_accessSelector_permissions=permissions,
          analysisQuery_resourceSelector_fullResourceName=resource,
          scope=scope,
      )
  )


def get_root(project_id):
  """Returns the root of a project.

  Args:
    project_id: Project ID.

  Returns:
    An organization if the project has one, otherwise the project itself.
  """
  ancestry = crm.GetAncestry(project_id=project_id)
  for resource in ancestry.ancestor:
    if resource.resourceId.type == "organization":
      return "organizations/{0}".format(resource.resourceId.id)
  return "projects/{0}".format(project_id)
