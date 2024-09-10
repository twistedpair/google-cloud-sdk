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
"""Tag utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.artifacts import filter_rewriter
from googlecloudsdk.command_lib.artifacts import requests
from googlecloudsdk.command_lib.artifacts import util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def ListTags(args):
  """Lists package tags in a given package.

  Args:
    args: User input arguments.

  Returns:
    List of package tags.
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
  _, server_filter = filter_rewriter.Rewriter().Rewrite(args.filter)

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
      "package": pkg_path,
      "server_filter": server_filter,
      "page_size": page_size,
  }
  server_args_skipped, ltags = util.RetryOnInvalidArguments(
      requests.ListTags, **server_args
  )

  if not server_args_skipped:
    # If server-side filter is parsed correctly and the request
    # succeeds, remove the client-side filter and sort-by.
    if server_filter and server_filter == args.filter:
      args.filter = None

  log.status.Print(
      "Listing items under project {}, location {}, repository {}, "
      "package {}.\n".format(project, location, repo, package)
  )
  return ltags
