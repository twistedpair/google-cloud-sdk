# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Build config for Run Compose."""

import os
from typing import Any, Dict, Optional

from apitools.base.py import encoding
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.builds import submit_util
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import platforms
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run.compose import tracker as tracker_stages
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import parallel


class BuildConfig:
  """Represents the build configuration for a service."""

  def __init__(
      self, context: Optional[str] = None, dockerfile: Optional[str] = None
  ):
    self.context = context
    self.dockerfile = dockerfile
    self.image_id: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'BuildConfig':
    return cls(
        context=data.get('context'),
        dockerfile=data.get('dockerfile'),
    )

  def to_dict(self) -> Dict[str, Any]:
    """Serializes the BuildConfig instance to a dictionary."""
    return {
        'context': self.context,
        'dockerfile': self.dockerfile,
        'image_id': self.image_id,
    }


def handle(
    source_build: Dict[str, BuildConfig],
    repo: str,
    project_name: str,
    region: str,
    tracker: progress_tracker.StagedProgressTracker,
    no_build: bool = False,
) -> None:
  """Performs source builds for all containers in parallel."""
  if no_build:
    _handle_no_build(source_build, project_name, region, tracker)
    return
  build_ops = []
  for container, build_config in source_build.items():
    try:
      build_op_ref, build_log_url, image_tag = _build_from_source(
          build_config, container, repo, project_name, region, tracker
      )
      build_ops.append(
          (container, build_config, build_op_ref, build_log_url, image_tag)
      )
    except submit_util.FailedBuildException as e:
      log.error(f'Build failed for container {container}: {e}')
      raise
    except exceptions.Error as e:
      log.error(f'An error occurred during build submission: {e}')
      raise

  if not build_ops:
    return

  def _run_build(args):
    container, build_config, build_op_ref, build_log_url, image_tag = args
    return _poll_and_handle_build_result(
        container, build_config, build_op_ref, build_log_url, tracker, image_tag
    )

  task_args = [
      (
          container,
          build_config,
          build_op_ref,
          build_log_url,
          image_tag,
      )
      for container, build_config, build_op_ref, build_log_url, image_tag in build_ops
  ]

  num_threads = min(len(task_args), 10)
  with parallel.GetPool(num_threads) as pool:
    results = pool.Map(_run_build, task_args)

  if not all(results):
    raise exceptions.Error('One or more container builds failed.')


def _poll_and_handle_build_result(
    container: str,
    build_config: BuildConfig,
    build_op_ref: resources.Resource,
    build_log_url: str,
    tracker: progress_tracker.StagedProgressTracker,  # pytype: disable=invalid-annotation
    image_tag: str,
) -> bool:
  """Polls a build operation and updates the tracker."""
  try:
    response_dict = _poll_until_build_completes(build_op_ref)
    if response_dict and response_dict['status'] != 'SUCCESS':
      tracker.FailStage(
          tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
              container=container
          ),
          None,
          message=(
              'Container build failed and logs are available at'
              ' [{build_log_url}].'.format(build_log_url=build_log_url)
          ),
      )
      return False
    else:
      image_with_digest = None
      if response_dict.get('results') and response_dict.get('results').get(
          'images'
      ):
        for img in response_dict.get('results').get('images'):
          if img.get('name') == image_tag:
            digest = img.get('digest')
            if digest:
              image_name_without_tag, _, _ = image_tag.rpartition(':')
              image_with_digest = image_name_without_tag + '@' + digest
              break

      if image_with_digest:
        build_config.image_id = image_with_digest
        log.debug(f"Image '{image_with_digest}' created.")
      else:
        build_config.image_id = image_tag
        log.debug(f"Image '{image_tag}' created.")
      tracker.CompleteStage(
          tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
              container=container
          )
      )
      return True
  except exceptions.Error as e:
    log.error(f'An error occurred while waiting for build of {container}: {e}')
    tracker.FailStage(
        tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
            container=container
        ),
        None,
        message=(
            'Error waiting for build to complete: {e}. Logs are available at'
            ' [{build_log_url}].'.format(e=e, build_log_url=build_log_url)
        ),
    )
    return False


def _get_service(service_name, region):
  """Get service if it exists, else return None."""
  project = properties.VALUES.core.project.Get(required=True)
  conn_context = connection_context.GetConnectionContext(
      None,
      platforms.PLATFORM_MANAGED,
      region_label=region,
  )
  service_ref = resources.REGISTRY.Parse(
      service_name,
      params={'namespacesId': project},
      collection='run.namespaces.services',
  )
  with serverless_operations.Connect(conn_context) as client:
    return client.GetService(service_ref)


def _handle_no_build(
    source_build: Dict[str, BuildConfig],
    project_name: str,
    region: str,
    tracker: progress_tracker.StagedProgressTracker,
) -> None:
  """Handles --no-build flag."""
  if not source_build:
    return

  project = properties.VALUES.core.project.Get(required=True)
  service_ref = resources.REGISTRY.Parse(
      project_name,
      params={'namespacesId': project},
      collection='run.namespaces.services',
  )
  conn_context = connection_context.GetConnectionContext(
      None,
      platform=platforms.PLATFORM_MANAGED,
      region_label=region,
  )
  with serverless_operations.Connect(conn_context) as client:
    existing_service = client.GetService(service_ref)
  if not existing_service:
    raise exceptions.Error(
        '--no-build cannot be used for the first deployment of service'
        f" '{project_name}'."
    )
  container_to_image_map = {}
  if existing_service and existing_service.template.spec.containers:
    for c in existing_service.template.spec.containers:
      container_to_image_map[c.name] = c.image

  for container, build_config in source_build.items():
    stage_key = tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
        container=container
    )
    try:
      tracker.StartStage(stage_key)
      image = container_to_image_map.get(container)
      if not image:
        raise exceptions.Error(
            f"Could not find image for container '{container}' in service"
            f" '{project_name}'."
        )
      build_config.image_id = image
      tracker.UpdateStage(
          stage_key, f'Using image [{image}] from deployed service.'
      )
      tracker.CompleteStage(stage_key)
    except Exception as e:
      tracker.FailStage(stage_key, e, 'Image retrieval failed.')
      raise


def _write_cloudbuild_config(context: str, image_tag: str) -> str:
  """Writes a cloudbuild.yaml file to the service source directory.

  Args:
    context: The build context directory.
    image_tag: The full tag for the image to be built.

  Returns:
    The path to the written cloudbuild.yaml file.
  """
  config_data = {
      'steps': [{
          'id': f'Build Docker Image: {image_tag}',
          'name': 'gcr.io/cloud-builders/docker',
          'args': ['buildx', 'build', '--load', '-t', image_tag, '.'],
      }],
      'images': [image_tag],
  }

  out_dir = os.path.join(context, 'out')
  file_path = os.path.join(out_dir, 'cloudbuild.yaml')
  try:
    files.MakeDir(out_dir)
    with files.FileWriter(file_path) as f:
      yaml.dump(config_data, f)
    log.debug(f"Wrote Cloud Build config to '{file_path}'")
    return file_path
  except Exception as e:
    raise exceptions.Error(
        f"Failed to write Cloud Build config to '{file_path}': {e}"
    )


def _build_from_source(
    config: BuildConfig,
    container: str,
    repo: str,
    project_name: str,
    region: str,
    tracker: progress_tracker.StagedProgressTracker,
) -> tuple[resources.Resource, str, str]:
  """Performs source build for a given container using build config."""
  source_path = config.context
  if source_path is None:
    raise ValueError('Build context is required for source build.')

  image_tag = '{repo}/{project_name}_{container}:{tag}'.format(
      repo=repo, project_name=project_name, container=container, tag='latest'
  )

  # Write the cloudbuild.yaml file to the service source directory.
  config_path = _write_cloudbuild_config(source_path, image_tag)

  # Get the Cloud Build API message module
  messages = cloudbuild_util.GetMessagesModule()

  # Create the build configuration. This will upload the source
  # and set up the build steps to use the Dockerfile.
  log.debug(
      f"Creating build config for image '{image_tag}' from source"
      f" '{source_path}'"
  )
  build_config = submit_util.CreateBuildConfig(
      tag=None,
      no_cache=False,
      messages=messages,
      substitutions=None,
      arg_config=config_path,
      is_specified_source=True,
      no_source=False,
      source=source_path,
      gcs_source_staging_dir=None,
      ignore_file=None,
      arg_gcs_log_dir=None,
      arg_machine_type=None,
      arg_disk_size=None,
      arg_worker_pool=None,
      arg_dir=None,
      arg_revision=None,
      arg_git_source_dir=None,
      arg_git_source_revision=None,
      arg_service_account=None,
      buildpack=None,
      hide_logs=True,
      # skip_set_source defaults to False, so SetSource is called internally
  )

  log.debug('Submitting build to Google Cloud Build')
  build_op_ref, build_log_url = _build_using_cloud_build(
      container, tracker, messages, build_config, region
  )
  return build_op_ref, build_log_url, image_tag


def _build_using_cloud_build(
    container, tracker, build_messages, build_config, region
):
  """Build an image from source if a user specifies a source when deploying."""
  build, _ = submit_util.Build(
      build_messages,
      True,
      build_config,
      hide_logs=True,
      build_region=region,
  )
  build_op = (
      f'projects/{build.projectId}/locations/{region}/operations/{build.id}'
  )
  build_op_ref = resources.REGISTRY.ParseRelativeName(
      build_op, collection='cloudbuild.projects.locations.operations'
  )
  build_log_url = build.logUrl
  stage_key = tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
      container=container
  )
  tracker.StartStage(stage_key)
  tracker.UpdateStage(
      stage_key,
      'Logs are available at [{build_log_url}].'.format(
          build_log_url=build_log_url
      ),
  )
  return build_op_ref, build_log_url


def _poll_until_build_completes(build_op_ref):
  client = cloudbuild_util.GetClientInstance()
  poller = waiter.CloudOperationPoller(
      client.projects_builds, client.operations
  )
  operation = waiter.PollUntilDone(poller, build_op_ref)
  return encoding.MessageToPyValue(operation.response)
