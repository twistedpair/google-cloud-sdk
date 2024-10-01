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
"""Attachment utils for Artifact Registry commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.command_lib.artifacts import docker_util
from googlecloudsdk.command_lib.artifacts import requests


def GetAttachmentToDownload(args):
  """Get the artifact registry Attachment."""
  if not args.oci_version_name:
    return GetAttachment(args.CONCEPTS.attachment.Parse())

  oci_version = docker_util.ParseDockerVersionStr(args.oci_version_name)
  client = requests.GetClient()
  messages = requests.GetMessages()
  request = messages.ArtifactregistryProjectsLocationsRepositoriesAttachmentsListRequest(
      parent=oci_version.image.docker_repo.GetRepositoryName(),
  )
  request.filter = 'oci_version_name="{name}"'.format(
      name=oci_version.GetVersionName()
  )
  response = client.projects_locations_repositories_attachments.List(request)
  if not response.attachments:
    raise ar_exceptions.InvalidInputValueError(
        'OCI version name {} is not found in repository {}.'.format(
            oci_version.GetVersionName(),
            oci_version.image.docker_repo.GetRepositoryName(),
        )
    )
  if len(response.attachments) != 1:
    raise ar_exceptions.InvalidInputValueError(
        'OCI version name {} points to more than one attachment.'.format(
            oci_version.GetVersionName()
        )
    )
  return response.attachments[0]


def GetAttachment(attachment_ref):
  """Get the artifact registry Attachment."""
  client = requests.GetClient()
  messages = requests.GetMessages()
  request = messages.ArtifactregistryProjectsLocationsRepositoriesAttachmentsGetRequest(
      name=attachment_ref.RelativeName()
  )
  attachment = client.projects_locations_repositories_attachments.Get(request)
  return attachment
