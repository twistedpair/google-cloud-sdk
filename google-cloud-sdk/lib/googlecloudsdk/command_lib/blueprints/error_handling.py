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
import json
import textwrap

from googlecloudsdk.api_lib.blueprints import blueprints_util
from googlecloudsdk.api_lib.cloudbuild import logs as cloudbuild_logs
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import text


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


def GetTextFileContentsFromStorageBucket(gcs_path, last_n_lines=0):
  """Gets the contents of a text file in Cloud Storage.

  Args:
    gcs_path: string, the full Cloud Storage path to a log file, e.g.
      'gs://my-bucket/logs/log.txt'.
    last_n_lines: int, if set, only returns the last N lines from the file.

  Raises:
      BadFileException if the file read is not successful.

  Returns:
    A string representing the last_n_lines lines of the file.
  """
  object_ref = resources.REGISTRY.Parse(gcs_path, collection='storage.objects')
  gcs_client = storage_api.StorageClient()
  log_bytes = gcs_client.ReadObject(object_ref)

  wrapper = io.TextIOWrapper(log_bytes, encoding='utf-8')
  text_lines = wrapper.readlines()
  if last_n_lines:
    text_lines = text_lines[-last_n_lines:]
  return ''.join(text_lines)


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
  log_contents = GetTextFileContentsFromStorageBucket(
      log_file_path, last_n_lines=24)

  log.status.Print(
      'Log contents follow:\n{}\n(end of log contents)'.format(log_contents))


def GetApplyResultsPathInGCS(artifacts_path):
  """Gets a full Cloud Storage path to a apply-results file.

  Args:
    artifacts_path: string, the full Cloud Storage path to the folder containing
      apply artifacts, e.g. 'gs://my-bucket/artifacts'.

  Returns:
    A string representing the full Cloud Storage path to the apply-results JSON
    file.
  """
  return '{0}/apply-results.json'.format(artifacts_path)


def GetDeleteResultsPathInGCS(artifacts_path):
  """Gets a full Cloud Storage path to a destroy-results file.

  Args:
    artifacts_path: string, the full Cloud Storage path to the folder containing
      deletion artifacts, e.g. 'gs://my-bucket/artifacts'.

  Returns:
    A string representing the full Cloud Storage path to the destroy-results
    JSON file.
  """
  return '{0}/destroy-results.json'.format(artifacts_path)


def GetPipelineResultsPathInGCS(artifacts_path):
  """Gets a full Cloud Storage path to a pipeline results YAML file.

  Args:
    artifacts_path: string, the full Cloud Storage path to the folder containing
      pipeline artifacts, e.g. 'gs://my-bucket/artifacts'.

  Returns:
    A string representing the full Cloud Storage path to the pipeline results
    YAML file.
  """
  # TODO(b/197157657): Update this path once we have a consistent "last
  # executed kpt results YAML" path.
  return '{0}/results.yaml'.format(artifacts_path)


def PrintKptApplyResultsError(artifacts_folder,
                              action='apply',
                              max_resource_errors=25):
  """Prints information about a failed `kpt apply`.

  Args:
    artifacts_folder: string, the full Cloud Storage path to the folder
      containing the revision's apply artifacts,
      e.g. 'gs://my-bucket/artifacts'.
    action: The type of action performed. Valid values: 'apply', 'delete'.
    max_resource_errors: int, the maximum number of kpt resource errors to
      display before truncating.

  Returns:
    bool indicating whether an error was printed or not.
  """
  if action == 'apply':
    results_path = GetApplyResultsPathInGCS(artifacts_folder)
  elif action == 'delete':
    results_path = GetDeleteResultsPathInGCS(artifacts_folder)
  try:
    results_content = GetTextFileContentsFromStorageBucket(results_path)
  except exceptions.BadFileException as e:
    log.debug('Unable to fetch kpt results from path "%s": %s', results_path, e)
    return False

  try:
    results_data = [json.loads(line) for line in results_content.splitlines()]
  except ValueError as e:
    log.debug('Unable to parse kpt results JSON: {}'.format(e))
    return False

  resource_failures = [
      event for event in results_data
      if (event.get('type') == action and
          event.get('eventType') in ('resourceDeleted', 'resourceFailed'))
  ]

  if resource_failures:
    num_resource_failures = len(resource_failures)
    log.error('[kpt] {0} {1} failed to {2}:'.format(
        num_resource_failures,
        text.Pluralize(len(resource_failures), 'resource'),
        action))
    for failure_event in resource_failures[:max_resource_errors]:
      log.status.Print('- "{0}" ({1}) failed:\n    "{2}"\n'.format(
          failure_event.get('name'), failure_event.get('kind'),
          failure_event.get('error')))
    if num_resource_failures > max_resource_errors:
      log.status.Print('Some errors were truncated.')
    log.status.Print('See {0} for details.'.format(results_path))
  return bool(resource_failures)


def PrintKptPipelineResultsError(artifacts_folder):
  """Prints information about a failed kpt pipeline run.

  Args:
    artifacts_folder: string, the full Cloud Storage path to the folder
      containing the revision's pipeline artifacts,
      e.g. 'gs://my-bucket/artifacts'.

  Returns:
    bool indicating whether an error was printed or not.
  """
  pipeline_results_path = GetPipelineResultsPathInGCS(artifacts_folder)
  try:
    pipeline_results_content = GetTextFileContentsFromStorageBucket(
        pipeline_results_path)
    pipeline_results_data = yaml.load(pipeline_results_content)
  except exceptions.BadFileException as e:
    log.debug('Unable to fetch kpt pipeline results: %s', e)
    return False
  except yaml.YAMLParseError as e:
    log.debug('Unable to parse kpt pipeline YAML: %s', e)
    return False
  if pipeline_results_data.get('apiVersion') != 'kpt.dev/v1':
    log.debug('Unknown kpt API version: {}'.format(
        pipeline_results_data.get('apiVersion')))
    return False

  printed_error = False
  for pipeline_result in pipeline_results_data.get('items', []):
    error_messages = [
        result.get('message')
        for result in pipeline_result.get('results', [])
        if 'message' in result and result.get('severity') == 'error'
    ]
    exit_code = pipeline_result.get('exitCode')
    image = pipeline_result.get('image', '(Unknown)')
    stderr = pipeline_result.get('stderr')

    # TODO(b/197227175): This line is not marked as covered by Zapfhan, but it
    # is being executed in tests. gcloud mandates 100% coverage, so this should
    # get fixed.
    if exit_code == 0 or not (error_messages or stderr):
      continue

    log.status.Print('- Function with image "{}" exited with code {}'.format(
        image, exit_code or '(Unknown)'))
    printed_error = True
    if error_messages:
      for msg in error_messages:
        log.status.Print('  - Error: "{}"'.format(msg))
    elif stderr:
      log.status.Print('  - Stderr:\n{}'.format('\n'.join(
          textwrap.wrap(
              stderr, initial_indent=' ' * 6, subsequent_indent=' ' * 6))))
    log.status.Print()
  if printed_error:
    log.status.Print('See {0} for details.'.format(pipeline_results_path))
  return printed_error


def PrintApplyRunError(apply_results):
  """Prints error details for a failed apply run.

  Attempts to display kpt-specific errors, and falls back to displaying Cloud
  Build logs if kpt errors are inaccessible.

  Args:
    apply_results: ApplyResults proto, the apply results from the failed
      revision.
  """
  kpt_error_found = PrintKptApplyResultsError(
      apply_results.artifacts, action='apply')
  if not kpt_error_found:
    PrintCloudBuildResults(apply_results.logs, apply_results.build)


def PrintDeleteRunError(delete_results):
  """Prints error details for a failed delete run.

  Attempts to display kpt-specific errors, and falls back to displaying Cloud
  Build logs if kpt errors are inaccessible.

  Args:
    delete_results: ApplyResults proto, the delete results from the delete
      operation.
  """
  kpt_error_found = PrintKptApplyResultsError(
      delete_results.artifacts, action='delete')
  if not kpt_error_found:
    PrintCloudBuildResults(delete_results.logs, delete_results.build)


def PrintPipelineRunError(pipeline_results):
  """Prints error details for a failed pipeline run.

  Attempts to display kpt-specific errors, and falls back to displaying Cloud
  Build logs if kpt errors are inaccessible.

  Args:
    pipeline_results: PipelineResults proto, the apply results from the failed
      revision.
  """
  kpt_error_found = PrintKptPipelineResultsError(pipeline_results.artifacts)
  if not kpt_error_found:
    PrintCloudBuildResults(pipeline_results.logs, pipeline_results.build)


def RevisionFailed(revision_ref):
  """Displays troubleshooting information to the user.

  This is the revision-equivalent of DeploymentFailed. It's called when the
  revision is determined to be the source of the issue.

  Args:
    revision_ref: a Revision resource.
  """
  messages = blueprints_util.GetMessagesModule()

  log.error(revision_ref.stateDetail)

  revision_error_code = revision_ref.errorCode
  if revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.PIPELINE_BUILD_RUN_FAILED:
    PrintPipelineRunError(revision_ref.pipelineResults)
  elif revision_error_code == messages.Revision.ErrorCodeValueValuesEnum.APPLY_BUILD_RUN_FAILED:
    PrintApplyRunError(revision_ref.applyResults)


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

  log.error(deployment_ref.stateDetail)

  if deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.REVISION_FAILED:
    revision_ref = blueprints_util.GetRevision(deployment_ref.latestRevision)
    RevisionFailed(revision_ref)
  elif deployment_error_code == messages.Deployment.ErrorCodeValueValuesEnum.DELETE_BUILD_RUN_FAILED:
    PrintDeleteRunError(deployment_ref.deleteResults)
