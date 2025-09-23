# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utility for parsing Artifact Registry versions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import json

from apitools.base.protorpclite import protojson
from googlecloudsdk.api_lib.artifacts import filter_rewriter
from googlecloudsdk.api_lib.util import common_args
from googlecloudsdk.command_lib.artifacts import containeranalysis_util as ca_util
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.command_lib.artifacts import util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def ShortenRelatedTags(response, unused_args):
  """Convert the tag resources into tag IDs."""
  tags = []
  for t in response.relatedTags:
    tag = resources.REGISTRY.ParseRelativeName(
        t.name, "artifactregistry.projects.locations.repositories.packages.tags"
    )
    tags.append(tag.tagsId)

  json_obj = json.loads(protojson.encode_message(response))
  json_obj.pop("relatedTags", None)
  if tags:
    json_obj["relatedTags"] = tags
  # Restore the display format of `metadata` after json conversion.
  if response.metadata is not None:
    json_obj["metadata"] = {
        prop.key: prop.value.string_value
        for prop in response.metadata.additionalProperties
    }
  return json_obj


def ListOccurrences(response, args):
  """Call CA APIs for vulnerabilities if --show-package-vulnerability is set."""
  if not args.show_package_vulnerability:
    return response

  # TODO(b/246801021) Assume all versions are mavenArtifacts until versions API
  # is aware of the package type.
  project, maven_resource = _GenerateMavenResourceFromResponse(response)

  metadata = ca_util.GetMavenArtifactOccurrences(project, maven_resource)

  if metadata.ArtifactsDescribeView():
    response.update(metadata.ArtifactsDescribeView())
  else:
    response.update(
        {"package_vulnerability_summary": "No vulnerability data found."}
    )

  return response


def ConvertFingerprint(response, unused_args):
  """Convert fingerprint and annotations to a dict."""
  if hasattr(response, "check_initialized"):
    # It's a protorpc message.
    resource = json.loads(protojson.encode_message(response))
  else:
    # It's a json already.
    resource = response

  if "fingerprints" in resource and resource["fingerprints"]:
    for h in resource["fingerprints"]:
      if isinstance(h.get("value"), str):
        # In dicts from tests, the value is base64 encoded string.
        h["value"] = base64.b64decode(h["value"]).hex()

  if "annotations" in resource and resource.get("annotations"):
    # The value from scenario test is a dict, not a message.
    if "additionalProperties" in resource["annotations"]:
      annotations = {}
      for p in resource["annotations"].get("additionalProperties", []):
        annotations[p["key"]] = p["value"]
      resource["annotations"] = annotations
  return resource


def _GenerateMavenResourceFromResponse(response):
  """Convert Versions Describe Response to maven artifact resource name."""
  r = resources.REGISTRY.ParseRelativeName(
      response["name"],
      "artifactregistry.projects.locations.repositories.packages.versions",
  )

  # mavenArtifacts is only present in the v1 API, not the default v1beta2 API
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName("artifactregistry", "v1")

  maven_artifacts_id = r.packagesId + ":" + r.versionsId

  maven_resource = resources.Resource.RelativeName(
      registry.Create(
          "artifactregistry.projects.locations.repositories.mavenArtifacts",
          projectsId=r.projectsId,
          locationsId=r.locationsId,
          repositoriesId=r.repositoriesId,
          mavenArtifactsId=maven_artifacts_id,
      )
  )

  return r.projectsId, maven_resource


def ListVersions(args):
  """Lists package versions in a given package.

  Args:
    args: User input arguments.

  Returns:
    List of package versiions.
  """
  client = requests.GetClient()
  messages = requests.GetMessages()
  page_size = args.page_size
  repo = util.GetRepo(args)
  project = util.GetProject(args)
  location = args.location or properties.VALUES.artifacts.location.Get()
  package = args.package
  escaped_pkg = package.replace("/", "%2F").replace("+", "%2B")
  escaped_pkg = escaped_pkg.replace("^", "%5E")
  order_by = common_args.ParseSortByArg(args.sort_by)
  limit = args.limit
  _, server_filter = filter_rewriter.Rewriter().Rewrite(args.filter)

  if order_by is not None:
    if "," in order_by:
      # Multi-ordering is not supported yet on backend, fall back to client-side
      # sort-by.
      order_by = None

  if args.limit is not None and args.filter is not None:
    if server_filter is not None:
      # Apply limit to server-side page_size to improve performance when
      # server-side filter is used.
      page_size = args.limit
    else:
      # Fall back to client-side paging with client-side filtering.
      page_size = None
      limit = None

  pkg_path = resources.Resource.RelativeName(
      resources.REGISTRY.Create(
          "artifactregistry.projects.locations.repositories.packages",
          projectsId=project,
          locationsId=location,
          repositoriesId=repo,
          packagesId=escaped_pkg,
      )
  )

  server_args = {
      "client": client,
      "messages": messages,
      "pkg": pkg_path,
      "server_filter": server_filter,
      "page_size": page_size,
      "order_by": order_by,
      "limit": limit,
  }
  server_args_skipped, lversions = util.RetryOnInvalidArguments(
      requests.ListVersions, **server_args
  )

  if not server_args_skipped:
    # If server-side filter or sort-by is parsed correctly and the request
    # succeeds, remove the client-side filter and sort-by.
    if server_filter and server_filter == args.filter:
      args.filter = None
    if order_by:
      args.sort_by = None

  log.status.Print(
      "Listing items under project {}, location {}, repository {}, "
      "package {}.\n".format(project, location, repo, package)
  )
  return lversions
