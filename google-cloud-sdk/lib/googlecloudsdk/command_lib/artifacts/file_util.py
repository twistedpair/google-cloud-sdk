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
"""File utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import re

from apitools.base.protorpclite import protojson
from googlecloudsdk.api_lib.artifacts import exceptions
from googlecloudsdk.api_lib.artifacts import filter_rewriter
from googlecloudsdk.api_lib.util import common_args
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.command_lib.artifacts import util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def EscapeFileName(ref):
  """Escapes slashes, pluses and hats from request names."""
  return resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.files",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      filesId=ref.filesId.replace("/", "%2F")
      .replace("+", "%2B")
      .replace("^", "%5E"),
  )


def EscapeFileNameHook(ref, unused_args, req):
  """Escapes slashes, pluses and hats from request names."""
  file = resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.files",
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      repositoriesId=ref.repositoriesId,
      filesId=ref.filesId.replace("/", "%2F")
      .replace("+", "%2B")
      .replace("^", "%5E"),
  )
  req.name = file.RelativeName()
  return req


def EscapeFileNameFromIDs(project_id, location_id, repo_id, file_id):
  """Escapes slashes and pluses from request names."""
  return resources.REGISTRY.Create(
      "artifactregistry.projects.locations.repositories.files",
      projectsId=project_id,
      locationsId=location_id,
      repositoriesId=repo_id,
      filesId=file_id.replace("/", "%2F")
      .replace("+", "%2B")
      .replace("^", "%5E"),
  )


def ConvertFilesHashes(files):
  """Convert hashes of file list to hex strings."""
  return [ConvertFileHashes(f, None) for f in files]


def ConvertFileHashes(response, unused_args):
  """Convert file hashes to hex strings."""

  # File hashes are "bytes", and if it's returned directly, it will be
  # automatically encoded with base64.
  # We want to display them as hex strings instead.

  # The returned file obj restricts the field type, so we can't simply update
  # the "bytes" field to a "string" field.
  # Convert it to a json object and then update the field as a workaround.
  json_obj = json.loads(protojson.encode_message(response))

  hashes = []
  for h in response.hashes:
    hashes.append({
        "type": h.type,
        "value": h.value.hex(),
    })
  if hashes:
    json_obj["hashes"] = hashes

  # Proto map fields are converted into type "AnnotationsValue" in the response,
  # which contains a list of key-value pairs as "additionalProperties".
  # We want to convert this back to a dict.
  annotations = {}
  if response.annotations:
    for p in response.annotations.additionalProperties:
      annotations[p.key] = p.value
  if annotations:
    json_obj["annotations"] = annotations

  return json_obj


def ListGenericFiles(args):
  """Lists the Generic Files stored."""
  client = requests.GetClient()
  messages = requests.GetMessages()
  project = util.GetProject(args)
  location = util.GetLocation(args)
  repo = util.GetRepo(args)
  package = args.package
  version = args.version
  version_path = resources.Resource.RelativeName(
      resources.REGISTRY.Create(
          "artifactregistry.projects.locations.repositories.packages.versions",
          projectsId=project,
          locationsId=location,
          repositoriesId=repo,
          packagesId=package,
          versionsId=version,
      )
  )
  arg_filters = 'owner="{}"'.format(version_path)
  repo_path = resources.Resource.RelativeName(
      resources.REGISTRY.Create(
          "artifactregistry.projects.locations.repositories",
          projectsId=project,
          locationsId=location,
          repositoriesId=repo,
      )
  )
  files = requests.ListFiles(client, messages, repo_path, arg_filters)

  return files


def ListFiles(args):
  """Lists files in a given project.

  Args:
    args: User input arguments.

  Returns:
    List of files.
  """
  client = requests.GetClient()
  messages = requests.GetMessages()
  project = util.GetProject(args)
  location = args.location or properties.VALUES.artifacts.location.Get()
  repo = util.GetRepo(args)
  package = args.package
  version = args.version
  tag = args.tag
  page_size = args.page_size
  order_by = common_args.ParseSortByArg(args.sort_by)
  _, server_filter = filter_rewriter.Rewriter().Rewrite(args.filter)

  if order_by is not None:
    if "," in order_by:
      # Multi-ordering is not supported yet on backend, fall back to client-side
      # sort-by.
      order_by = None
    if package or version or tag:
      # Cannot use server-side sort-by with --package, --version or --tag,
      # fall back to client-side sort-by.
      order_by = None

  if args.limit is not None and args.filter is not None:
    if server_filter is not None:
      # Apply limit to server-side page_size to improve performance when
      # server-side filter is used.
      page_size = args.limit
    else:
      # Fall back to client-side paging with client-side filtering.
      page_size = None

  if server_filter:
    if package or version or tag:
      # Cannot use server-side filter with --package, --version or --tag,
      # fallback to client-side filter.
      server_filter = None

  # Parse fully qualified path in package argument
  if package:
    if re.match(
        r"projects\/.*\/locations\/.*\/repositories\/.*\/packages\/.*", package
    ):
      params = (
          package.replace("projects/", "", 1)
          .replace("/locations/", " ", 1)
          .replace("/repositories/", " ", 1)
          .replace("/packages/", " ", 1)
          .split(" ")
      )
      project, location, repo, package = [params[i] for i in range(len(params))]

  # Escape slashes, pluses and carets in package name
  if package:
    package = package.replace("/", "%2F").replace("+", "%2B")
    package = package.replace("^", "%5E")

  # Retrieve version from tag name
  if version and tag:
    raise exceptions.InvalidInputValueError(
        "Specify either --version or --tag with --package argument."
    )
  if package and tag:
    tag_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages.tags",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package,
            tagsId=tag,
        )
    )
    version = requests.GetVersionFromTag(client, messages, tag_path)

  if package and version:
    version_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages.versions",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package,
            versionsId=version,
        )
    )
    server_filter = 'owner="{}"'.format(version_path)
  elif package:
    package_path = resources.Resource.RelativeName(
        resources.REGISTRY.Create(
            "artifactregistry.projects.locations.repositories.packages",
            projectsId=project,
            locationsId=location,
            repositoriesId=repo,
            packagesId=package,
        )
    )
    server_filter = 'owner="{}"'.format(package_path)
  elif version or tag:
    raise exceptions.InvalidInputValueError(
        "Package name is required when specifying version or tag."
    )

  repo_path = resources.Resource.RelativeName(
      resources.REGISTRY.Create(
          "artifactregistry.projects.locations.repositories",
          projectsId=project,
          locationsId=location,
          repositoriesId=repo,
      )
  )
  server_args = {
      "client": client,
      "messages": messages,
      "repo": repo_path,
      "server_filter": server_filter,
      "page_size": page_size,
      "order_by": order_by,
  }
  server_args_skipped, lfiles = util.RetryOnInvalidArguments(
      requests.ListFiles, **server_args
  )

  if not server_args_skipped:
    # If server-side filter or sort-by is parsed correctly and the request
    # succeeds, remove the client-side filter and sort-by.
    if server_filter and server_filter == args.filter:
      args.filter = None
    if order_by:
      args.sort_by = None
  return ConvertFilesHashes(lfiles)
