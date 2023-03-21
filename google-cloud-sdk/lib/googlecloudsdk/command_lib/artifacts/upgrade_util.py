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
from googlecloudsdk.command_lib.artifacts import requests as artifacts

_DOMAIN_TO_BUCKET_PREFIX = frozendict.frozendict({
    "gcr.io": "",
    "us.gcr.io": "us.",
    "asia.gcr.io": "asia.",
    "eu.gcr.io": "eu.",
})


# Set of GCS permissions for GCR that are relevant to AR.
_PERMISSIONS = (
    "storage.buckets.get",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.buckets.create",
)

_ADMIN = "roles/artifactregistry.admin"
_REPO_ADMIN = "roles/artifactregistry.repoAdmin"
_WRITER = "roles/artifactregistry.writer"
_READER = "roles/artifactregistry.reader"

# In order of most to least privilege, so we can exit early if we match any.
_AR_ROLES = (_ADMIN, _REPO_ADMIN, _WRITER, _READER)

# Maps an AR role to the equivalent set of GCR permissions.
_ROLE_TO_PERMISSIONS = frozendict.frozendict({
    _READER: (
        "storage.objects.get",
        "storage.objects.list",
    ),
    _WRITER: (
        "storage.buckets.get",
        "storage.objects.get",
        "storage.objects.list",
        "storage.objects.create",
    ),
    _REPO_ADMIN: (
        "storage.buckets.get",
        "storage.objects.get",
        "storage.objects.list",
        "storage.objects.create",
        "storage.objects.delete",
    ),
    _ADMIN: (
        "storage.buckets.get",
        "storage.objects.get",
        "storage.objects.list",
        "storage.objects.create",
        "storage.objects.delete",
        "storage.buckets.create",
    ),
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


def iam_policy(domain, project, parent):
  """Generates an AR-equivalent IAM policy for a GCR registry.

  Args:
    domain: The domain of the GCR registry.
    project: The project of the GCR registry.
    parent: The parent scope to consider when generating the IAM Policy.

  Returns:
    An iam.Policy.

  Raises:
    Exception: A problem was encountered while generating the policy.
  """
  bucket = bucket_resource_name(domain, project)
  analysis = analyze_iam_policy(_PERMISSIONS, bucket, parent)

  # If we see any false fullyExplored, that indicates that AnalyzeIamPolicy is
  # returning incomplete information, so the generated policy might be wrong,
  # so we conservatively bail out in that case.
  if not analysis.fullyExplored or not analysis.mainAnalysis.fullyExplored:
    errors = list(err.cause for err in analysis.mainAnalysis.nonCriticalErrors)
    error_msg = "\n".join(errors)
    raise ar_exceptions.ArtifactRegistryError(error_msg)

  member_to_perms = collections.defaultdict(set)
  for result in analysis.mainAnalysis.analysisResults:
    if not result.fullyExplored:
      raise ar_exceptions.ArtifactRegistryError(_ANALYSIS_NOT_FULLY_EXPLORED)

    if result.iamBinding.condition is not None:
      # AR doesn't support IAM conditions.
      raise ar_exceptions.ArtifactRegistryError(
          "Conditional IAM binding is not supported."
      )

    # Aggregate the GCR permissions for each IAM principal.
    perms = set()
    for acl in result.accessControlLists:
      for access in acl.accesses:
        perms.add(access.permission)

    for member in result.iamBinding.members:
      if is_convenience(member):
        # convenience values are GCR legacy. They are not needed in AR.
        continue
      member_to_perms[member] = member_to_perms[member].union(perms)

  # Map permissions of each principal to the least privilege equivalent for AR.
  role_to_members = collections.defaultdict(list)
  for member, granted_perms in member_to_perms.items():
    for role in _AR_ROLES:
      equivlant_perms = _ROLE_TO_PERMISSIONS[role]
      if granted_perms.issuperset(equivlant_perms):
        role_to_members[role].append(member)
        break

  # Convert the map to an iam.Policy object so that gcloud can format it nicely.
  messages = artifacts.GetMessages()
  bindings = list()

  for role in _AR_ROLES:
    members = role_to_members.get(role)
    if not members:
      continue
    bindings.append(
        messages.Binding(
            role=role,
            members=members,
        )
    )

  return messages.Policy(bindings=bindings)


def is_convenience(s):
  return (
      s.startswith("projectOwner:")
      or s.startswith("projectEditor:")
      or s.startswith("projectViewer:")
  )


def analyze_iam_policy(permissions, resource, parent):
  """Calls AnalyzeIamPolicy for the given resource.

  Args:
    permissions: for the access selector
    resource: for the resource selector
    parent: for the scope

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
          scope=parent,
      )
  )
