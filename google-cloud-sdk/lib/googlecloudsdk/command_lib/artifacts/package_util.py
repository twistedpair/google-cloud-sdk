# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Package utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.artifacts import filter_rewriter
from googlecloudsdk.api_lib.util import common_args
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.command_lib.artifacts import util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def ListPackages(args):
  """Lists packages in a given project.

  Args:
    args: User input arguments.

  Returns:
    List of packages.
  """
  client = requests.GetClient()
  messages = requests.GetMessages()
  repo = util.GetRepo(args)
  project = util.GetProject(args)
  location = args.location or properties.VALUES.artifacts.location.Get()
  page_size = args.page_size
  order_by = common_args.ParseSortByArg(args.sort_by)
  _, server_filter = filter_rewriter.Rewriter().Rewrite(args.filter)
  limit = args.limit

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
      "limit": limit,
  }
  server_args_skipped, lpkgs = util.RetryOnInvalidArguments(
      requests.ListPackages, **server_args
  )

  if not server_args_skipped:
    # If server-side filter or sort-by is parsed correctly and the request
    # succeeds, remove the client-side filter and sort-by.
    if server_filter and server_filter == args.filter:
      args.filter = None
    if order_by:
      args.sort_by = None
  log.status.Print(
      "Listing items under project {}, location {}, repository {}.\n".format(
          project, location, repo
      )
  )

  return util.UnescapePackageName(lpkgs, None)
