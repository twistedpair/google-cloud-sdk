# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Support library for troubleshooting errors."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from googlecloudsdk.api_lib.blueprints import blueprints_util
from googlecloudsdk.api_lib.cloudbuild import logs as cloudbuild_logs
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def GetCloudBuild(build_id):
  """Fetches a Cloud Build build in the global region.

  Args:
    build_id: string, a Cloud Build ID, e.g.
      '3a14eb82-7717-4160-b6f7-49c986ca449e'.

  Returns:
    A Build resource.
  """
  build_ref = resources.REGISTRY.Parse(
      None,
      collection='cloudbuild.projects.locations.builds',
      api_version='v1',
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail(),
          'locationsId': 'global',
          'buildsId': build_id,
      })
  build = cloudbuild_logs.CloudBuildClient().GetBuild(build_ref)
  return build


def GetTextFileContentsFromStorageBucket(gcs_path):
  """Gets the contents of a text file in Cloud Storage.

  Args:
    gcs_path: string, the full Cloud Storage path to a log file, e.g.
      'gs://my-bucket/logs/log.txt'.

  Returns:
    A string representing the last 24 lines of the file.
  """
  object_ref = resources.REGISTRY.Parse(gcs_path, collection='storage.objects')
  gcs_client = storage_api.StorageClient()
  log_bytes = gcs_client.ReadObject(object_ref)

  wrapper = io.TextIOWrapper(log_bytes, encoding='utf-8')
  text_lines = wrapper.readlines()
  last_lines = text_lines[-24:]
  return ''.join(last_lines)


def GetBuildLogPathInGCS(logs_folder, build_id):
  """Gets a full Cloud-Storage path to a log file.

  This is a simple convenience function that mirrors the naming convention that
  the Blueprints Controller API uses for log files.

  Args:
    logs_folder: string, the full Cloud Storage path to the folder containing
      the log file, e.g. 'gs://my-bucket/logs'.
    build_id: string, a Cloud Build ID, e.g.
      '3a14eb82-7717-4160-b6f7-49c986ca449e'.

  Returns:
    A string representing the full Cloud Storage path to a specific log file.
  """
  return '{0}/log-{1}.txt'.format(logs_folder, build_id)


def PrintCloudBuildResults(logs_folder, build_id):
  """Prints information about a Cloud Build build.

  This logs two things: a link to the Cloud Build build itself and the contents
  of the log as uploaded to Cloud Storage.

  Args:
    logs_folder: string, the full Cloud Storage path to the folder containing
      the log file, e.g. 'gs://my-bucket/logs'.
    build_id: string, a Cloud Build ID, e.g.
      '3a14eb82-7717-4160-b6f7-49c986ca449e'.
  """
  build = GetCloudBuild(build_id)
  log.status.Print('Cloud Build logs: {}'.format(build.logUrl))

  log_file_path = GetBuildLogPathInGCS(logs_folder, build_id)
  log_contents = GetTextFileContentsFromStorageBucket(log_file_path)

  log.status.Print(
      'Log contents follow:\n{}\n(end of log contents)'.format(log_contents))


def RevisionFailed(revision_ref):
  """Displays troubleshooting information to the user.

  This is the revision-equivalent of DeploymentFailed. It's called when the
  revision is determined to be the source of the issue.

  Args:
    revision_ref: a Revision resource.
  """
  messages = blueprints_util.GetMessagesModule()

  revision_error_code = revision_ref.errorCode
  if revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.BUCKET_CREATION_PERMISSION_DENIED:
    log.error('Permission was denied when creating the root Cloud Storage '
              'bucket. Ensure your project has the '
              'roles/cloudconfig.serviceAgent role bound to the Blueprints '
              'Controller service account.')
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.BUCKET_CREATION_FAILED:
    log.error('Creating the root Cloud Storage bucket failed: {}'.format(
        revision_ref.stateDetail))
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.CLOUD_BUILD_PERMISSION_DENIED:
    log.error(
        'Permission was denied to Cloud Build. Ensure your project has the '
        'roles/cloudconfig.serviceAgent role bound to the Blueprints '
        'Controller service account.')
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.PIPELINE_BUILD_API_FAILED:
    log.error('The pipeline build failed before it could run: {}'.format(
        revision_ref.stateDetail))
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.PIPELINE_BUILD_RUN_FAILED:
    log.error('The pipeline build failed while running.')
    PrintCloudBuildResults(revision_ref.pipelineResults.logs,
                           revision_ref.pipelineResults.build)
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.APPLY_BUILD_API_FAILED:
    log.error('The apply build failed before it could run: {}'.format(
        revision_ref.stateDetail))
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.APPLY_BUILD_RUN_FAILED:
    log.error('The apply build failed while running.')
    PrintCloudBuildResults(revision_ref.applyResults.logs,
                           revision_ref.applyResults.build)
  else:
    log.error('The deployment failed due to an unrecognized error code on the '
              'revision ("{}"): {}'.format(revision_error_code,
                                           revision_ref.stateDetail))


def DeploymentFailed(deployment_ref):
  """Displays troubleshooting information to the user.

  This parses the fields of a deployment in order to figure out what to output,
  e.g. instructions for how to continue, links, or log files themselves.

  This function is intended to be used not only when creating or updating a
  deployment, but also when describing or deleting a deployment.

  Args:
    deployment_ref: a Deployment resource.
  """

  messages = blueprints_util.GetMessagesModule()
  deployment_error_code = deployment_ref.errorCode

  if deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.REVISION_FAILED:
    revision_ref = blueprints_util.GetRevision(deployment_ref.latestRevision)
    RevisionFailed(revision_ref)
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.CLUSTER_CREATION_PERMISSION_DENIED:
    log.error('Permission was denied when creating the Config Controller '
              'cluster. Ensure your project has the '
              'roles/cloudconfig.serviceAgent role bound to the Blueprints '
              'Controller service account.')
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.CLOUD_BUILD_PERMISSION_DENIED:
    log.error(
        'Permission was denied to Cloud Build. Ensure your project has the '
        'roles/cloudconfig.serviceAgent role bound to the Blueprints '
        'Controller service account.')
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.CLUSTER_CREATION_FAILED:
    log.error('Failed to create the underlying Config Controller '
              'cluster: {}'.format(deployment_ref.stateDetail))
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.DELETE_BUILD_API_FAILED:
    log.error('The delete build failed before it could run: {}'.format(
        deployment_ref.stateDetail))
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.DELETE_BUILD_RUN_FAILED:
    log.error('The delete build failed while running.')
    PrintCloudBuildResults(
        deployment_ref.deleteResults.logs,
        deployment_ref.deleteResults.build)
  else:
    log.error('The deployment failed due to an unrecognized error code ("{}"): '
              '{}'.format(deployment_error_code, deployment_ref.stateDetail))
