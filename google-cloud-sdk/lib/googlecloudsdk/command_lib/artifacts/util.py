# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utility for interacting with Artifact Registry requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re

from googlecloudsdk.api_lib import artifacts
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

_INVALID_REPO_NAME_ERROR = (
    "Names may only contain lowercase letters, numbers, and hyphens, and must "
    "begin with a letter and end with a letter or number.")

_VALID_LOCATIONS = [
    "northamerica-northeast1",
    "us-central1",
    "us-east1",
    "us-east4",
    "us-west1",
    "us-west2",
    "southamerica-east1",
    "europe-north1",
    "europe-west1",
    "europe-west2",
    "europe-west3",
    "europe-west4",
    "europe-west6",
    "asia-east1",
    "asia-east2",
    "asia-northeast1",
    "asia-northeast2",
    "asia-south1",
    "asia-southeast1",
    "australia-southeast1",
    "asia",
    "europe",
    "us",
]

_REPO_REGEX = "^[a-z]([a-z0-9-]*[a-z0-9])?$"


def _GetMessagesForResource(resource_ref):
  return artifacts.Messages(resource_ref.GetCollectionInfo().api_version)


def _GetClientForResource(resource_ref):
  return artifacts.Client(resource_ref.GetCollectionInfo().api_version)


def _IsValidLocation(location):
  return location.lower() in _VALID_LOCATIONS


def _IsValidRepoName(repo_name):
  return re.match(_REPO_REGEX, repo_name) is not None


def GetProject(args):
  """Gets project resource from either argument flag or attribute."""
  return args.project or properties.VALUES.core.project.GetOrFail()


def GetRepo(args):
  """Gets repository resource from either argument flag or attribute."""
  return args.repository or properties.VALUES.artifacts.repository.GetOrFail()


def GetLocation(args):
  """Gets location resource from either argument flag or attribute."""
  return args.location or properties.VALUES.artifacts.location.GetOrFail()


def GetLocationList():
  """Gets a list of all supported locations."""
  return _VALID_LOCATIONS


def AppendRepoDataToRequest(repo_ref, repo_args, request):
  """Adds repository data to CreateRepositoryRequest."""
  if not _IsValidRepoName(repo_ref.repositoriesId):
    raise ar_exceptions.InvalidInputValueError(_INVALID_REPO_NAME_ERROR)
  if not _IsValidLocation(repo_args.location):
    raise ar_exceptions.UnsupportedLocationError(
        "{} is not a valid location. Valid locations are [{}].".format(
            repo_args.location, ", ".join(_VALID_LOCATIONS)))
  messages = _GetMessagesForResource(repo_ref)
  repo = messages.Repository(
      name=repo_ref.RelativeName(),
      description=repo_args.description,
      format=messages.Repository.FormatValueValuesEnum(
          repo_args.repository_format.upper()))
  request.repository = repo
  request.repositoryId = repo_ref.repositoriesId
  return request


def DeleteVersionTags(ver_ref, ver_args, request):
  """Deletes tags associate with the specified version."""
  if not ver_args.delete_tags:
    return request
  client = _GetClientForResource(ver_ref)
  messages = _GetMessagesForResource(ver_ref)
  list_tags_req = messages.ArtifactregistryProjectsLocationsRepositoriesPackagesTagsListRequest(
      parent=ver_ref.Parent().RelativeName())
  list_tags_res = client.projects_locations_repositories_packages_tags.List(
      list_tags_req)
  for tag in list_tags_res.tags:
    if tag.version != ver_ref.RelativeName():
      continue
    delete_tag_req = messages.ArtifactregistryProjectsLocationsRepositoriesPackagesTagsDeleteRequest(
        name=tag.name)
    err = client.projects_locations_repositories_packages_tags.Delete(
        delete_tag_req)
    if not isinstance(err, messages.Empty):
      raise ar_exceptions.ArtifactRegistryError(
          "Failed to delete tag {}: {}".format(tag.name, err))
  return request


def DeletePackageTags(pkg_ref, pkg_args, request):
  """Deletes tags associate with the specified package."""
  if not pkg_args.delete_tags:
    return request
  client = _GetClientForResource(pkg_ref)
  messages = _GetMessagesForResource(pkg_ref)
  list_tags_req = messages.ArtifactregistryProjectsLocationsRepositoriesPackagesTagsListRequest(
      parent=pkg_ref.RelativeName())
  list_tags_res = client.projects_locations_repositories_packages_tags.List(
      list_tags_req)
  for tag in list_tags_res.tags:
    delete_tag_req = messages.ArtifactregistryProjectsLocationsRepositoriesPackagesTagsDeleteRequest(
        name=tag.name)
    err = client.projects_locations_repositories_packages_tags.Delete(
        delete_tag_req)
    if not isinstance(err, messages.Empty):
      raise ar_exceptions.ArtifactRegistryError(
          "Failed to delete tag {}: {}".format(tag.name, err))
  return request


def AppendTagDataToRequest(tag_ref, tag_args, request):
  """Adds tag data to CreateTagRequest."""
  parts = request.parent.split("/")
  pkg_path = "/".join(parts[:len(parts) - 2])
  request.parent = pkg_path
  messages = _GetMessagesForResource(tag_ref)
  tag = messages.Tag(
      name=tag_ref.RelativeName(),
      version=pkg_path + "/versions/" + tag_args.version)
  request.tag = tag
  request.tagId = tag_ref.tagsId
  return request


def SetTagUpdateMask(tag_ref, tag_args, request):
  """Set update mask to UpdateTagRequest."""
  messages = _GetMessagesForResource(tag_ref)
  parts = request.name.split("/")
  pkg_path = "/".join(parts[:len(parts) - 2])
  tag = messages.Tag(
      name=tag_ref.RelativeName(),
      version=pkg_path + "/versions/" + tag_args.version)
  request.tag = tag
  request.updateMask = "version"
  return request


def SlashEscapePackageName(pkg_ref, unused_args, request):
  """Escapes slashes in package name for ListVersionsRequest."""
  request.parent = "{}/packages/{}".format(
      pkg_ref.Parent().RelativeName(), pkg_ref.packagesId.replace("/", "%2F"))
  return request


def SlashUnescapePackageName(response, unused_args):
  """Unescape slashes in package name from ListPackagesResponse."""
  ret = []
  for ver in response:
    ver.name = os.path.basename(ver.name)
    ver.name = ver.name.replace("%2F", "/").replace("%2f", "/")
    ret.append(ver)
  return ret


def AppendParentInfoToListReposResponse(response, args):
  """Adds log to clarify parent resources for ListRepositoriesRequest."""
  if response:
    log.status.Print("Listing items under project {}, location {}.\n".format(
        GetProject(args), GetLocation(args)))
  return response


def AppendParentInfoToListPackagesResponse(response, args):
  """Adds log to clarify parent resources for ListPackagesRequest."""
  if response:
    log.status.Print(
        "Listing items under project {}, location {}, repository {}.\n".format(
            GetProject(args), GetLocation(args), GetRepo(args)))
  return response


def AppendParentInfoToListVersionsAndTagsResponse(response, args):
  """Adds log to clarify parent resources for ListVersions or ListTags."""
  if response:
    log.status.Print(
        "Listing items under project {}, location {}, repository {}, "
        "package {}.\n".format(
            GetProject(args), GetLocation(args), GetRepo(args), args.package))
  return response
