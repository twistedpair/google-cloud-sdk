# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Util for Artifact Guard API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import requests
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files

API_NAME = 'artifactscanguard'
API_VERSION = 'v1alpha'


def GetMessagesModule(api_version=API_VERSION):
  return apis.GetMessagesModule(API_NAME, api_version)


def GetClientInstance(api_version=API_VERSION):
  return apis.GetClientInstance(API_NAME, api_version)


def UploadFileToSignedUrl(
    url, file_path, content_type='application/octet-stream'
):
  """Uploads a local file to a signed URL via HTTP PUT."""
  try:
    data = files.ReadBinaryFileContents(file_path)
    session = requests.GetSession()
    response = session.put(
        url, data=data, headers={'Content-Type': content_type}
    )
    if response.status_code < 200 or response.status_code >= 300:
      raise exceptions.Error(
          'Upload to {} failed with status {}: {}'.format(
              url, response.status_code, response.content
          )
      )
  except Exception as e:
    raise exceptions.Error(
        'Failed to upload file [{}] to [{}]: {}'.format(file_path, url, e)
    )


def GetPipelineContext(args):
  """Constructs PipelineContext message from command arguments."""
  messages = GetMessagesModule()
  context = messages.PipelineContext()
  if args.jenkins_build_tag and args.jenkins_build_id:
    context.jenkins = messages.Jenkins(
        buildTag=args.jenkins_build_tag, buildId=args.jenkins_build_id
    )
  elif args.github_run_id:
    context.githubAction = messages.GithubAction(
        runId=args.github_run_id,
        workflow=args.github_workflow,
        repository=args.github_repository,
    )
  elif args.cloud_build_id and args.cloud_build_project_id:
    context.cloudBuild = messages.CloudBuild(
        buildId=args.cloud_build_id,
        projectId=args.cloud_build_project_id,
        triggerId=args.cloud_build_trigger_id,
    )
  return context


def GetSignedUrls(parent_resource, image_name, image_digest, image_tag):
  """Calls DataGateway to get signed URLs for SBOM/pURL uploads.

  Args:
    parent_resource: str, parent resource name.
    image_name: str, name of the image.
    image_digest: str, digest of the image.
    image_tag: list[str], list of tags for the image.

  Returns:
    The result of the DataGateway operation, containing signed URLs and GCS
    URIs.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE

  if parent_resource.startswith('projects/'):
    req = messages.ArtifactscanguardProjectsLocationsArtifactEvaluationsDataGatewayRequest(
        parent=parent_resource,
        artifactMetadata_imageName=image_name,
        artifactMetadata_imageDigest=image_digest,
        artifactMetadata_imageTag=image_tag,
    )
    op = client.projects_locations_artifactEvaluations.DataGateway(req)
  else:
    req = messages.ArtifactscanguardOrganizationsLocationsArtifactEvaluationsDataGatewayRequest(
        parent=parent_resource,
        artifactMetadata_imageName=image_name,
        artifactMetadata_imageDigest=image_digest,
        artifactMetadata_imageTag=image_tag,
    )
    op = client.organizations_locations_artifactEvaluations.DataGateway(req)
  return op.response


def RunArtifactEvaluation(
    parent_resource,
    connector_id,
    image_name,
    image_digest,
    image_tag,
    sbom_uri,
    purl_uri,
    pipeline_context,
):
  """Calls RunArtifactEvaluation to initiate a scan.

  Args:
    parent_resource: str, parent resource name.
    connector_id: str, connector ID.
    image_name: str, name of the image.
    image_digest: str, digest of the image.
    image_tag: list[str], list of tags for the image.
    sbom_uri: str, GCS URI of the SBOM file.
    purl_uri: str, GCS URI of the pURL file.
    pipeline_context: PipelineContext message.

  Returns:
    The long-running operation for the scan.
  """
  client = GetClientInstance()
  messages = client.MESSAGES_MODULE

  artifact_metadata = messages.ArtifactMetadata(
      imageName=image_name,
      imageDigest=image_digest,
      imageTag=image_tag,
      sbomUri=sbom_uri,
      purlUri=purl_uri,
  )

  evaluation_request = messages.RunArtifactEvaluationRequest(
      artifactMetadata=artifact_metadata,
      pipelineContext=pipeline_context,
      pipelineConnector=connector_id,
  )

  if parent_resource.startswith('projects/'):
    req = messages.ArtifactscanguardProjectsLocationsArtifactEvaluationsRunRequest(
        parent=parent_resource,
        runArtifactEvaluationRequest=evaluation_request,
    )
    return client.projects_locations_artifactEvaluations.Run(req)
  else:
    req = messages.ArtifactscanguardOrganizationsLocationsArtifactEvaluationsRunRequest(
        parent=parent_resource,
        runArtifactEvaluationRequest=evaluation_request,
    )
    return client.organizations_locations_artifactEvaluations.Run(req)


def WaitForOperation(operation, message):
  """Waits for a long-running operation to complete.

  Args:
    operation: operation to poll.
    message: str, message to display while waiting.

  Returns:
    The result of the operation.
  """
  client = GetClientInstance()
  if operation.name.startswith('projects/'):
    op_resource = resources.REGISTRY.Parse(
        operation.name,
        collection='artifactscanguard.projects.locations.operations',
    )
    poller = waiter.CloudOperationPollerNoResources(
        client.projects_locations_operations
    )
    return waiter.WaitFor(poller, op_resource, message)
  else:
    op_resource = resources.REGISTRY.Parse(
        operation.name,
        collection='artifactscanguard.organizations.locations.operations',
    )
    poller = waiter.CloudOperationPollerNoResources(
        client.organizations_locations_operations
    )
    return waiter.WaitFor(poller, op_resource, message)
