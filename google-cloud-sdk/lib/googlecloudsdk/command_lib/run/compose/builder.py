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

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict

from apitools.base.py import encoding
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.command_lib.builds import submit_util
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import platforms
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.command_lib.run.compose import exceptions as compose_exceptions
from googlecloudsdk.command_lib.run.compose import exit_codes
from googlecloudsdk.command_lib.run.compose import tracker as tracker_stages
from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import parallel

_FINGERPRINTS_FILE_NAME = 'fingerprints.json'
_FINGERPRINT_KEY = 'fingerprint'
_IMAGE_ID_KEY = 'image_id'


class BuildConfig:
  """Represents the build configuration for a service."""

  def __init__(
      self, context: str | None = None, dockerfile: str | None = None
  ):
    self.context = context
    self.dockerfile = dockerfile
    self.image_id: str | None = None

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

  loaded_fingerprints = _load_source_fingerprints(project_name)
  fingerprints_to_save = {}
  build_ops = []

  for container, build_config in source_build.items():
    current_fingerprint = _calculate_source_fingerprint(build_config)
    if loaded_fingerprints.get(container, {}).get(
        _FINGERPRINT_KEY
    ) == current_fingerprint:
      image_id = loaded_fingerprints[container][_IMAGE_ID_KEY]
      build_config.image_id = image_id
      fingerprints_to_save[container] = loaded_fingerprints[container]
      stage_key = tracker_stages.StagedProgressTrackerStage.BUILD.get_key(
          container=container
      )
      tracker.StartStage(stage_key)
      tracker.UpdateStage(
          stage_key, f'Skipping build, using image [{image_id}] from cache.'
      )
      tracker.CompleteStage(stage_key)
      # This log is added to verify if the build is skipped in e2e.
      log.debug(
          f'Skipping build for container {container}, using image from cache.'
      )
      continue
    try:
      build_op_ref, build_log_url, image_tag = _build_from_source(
          build_config, container, repo, project_name, region, tracker
      )
      build_ops.append((
          container,
          build_config,
          build_op_ref,
          build_log_url,
          image_tag,
          current_fingerprint,
      ))
    except submit_util.FailedBuildException as e:
      log.error(f'Build failed for container {container}: {e}')
      raise compose_exceptions.BuildError(
          str(e), exit_codes.BUILD_FAILED
      ) from e
    except exceptions.Error as e:
      log.error(f'An error occurred during build submission: {e}')
      raise compose_exceptions.BuildError(
          f'An error occurred during build submission: {e}',
          exit_codes.BUILD_SUBMISSION_ERROR,
      ) from e

  if not build_ops:
    _save_source_fingerprints(fingerprints_to_save, project_name)
    return

  def _run_build(args):
    (
        container,
        build_config,
        build_op_ref,
        build_log_url,
        image_tag,
        fingerprint,
    ) = args
    success = _poll_and_handle_build_result(
        container, build_config, build_op_ref, build_log_url, tracker, image_tag
    )
    if success:
      return container, fingerprint, build_config.image_id
    else:
      return None

  task_args = [
      (
          container,
          build_config,
          build_op_ref,
          build_log_url,
          image_tag,
          fingerprint,
      )
      for (
          container,
          build_config,
          build_op_ref,
          build_log_url,
          image_tag,
          fingerprint,
      ) in build_ops
  ]

  num_threads = min(len(task_args), 10)
  with parallel.GetPool(num_threads) as pool:
    build_results = pool.Map(_run_build, task_args)

  num_build_successes = 0
  for result in build_results:
    if result:
      num_build_successes += 1
      container, fingerprint, image_id = result
      fingerprints_to_save[container] = {
          _FINGERPRINT_KEY: fingerprint,
          _IMAGE_ID_KEY: image_id,
      }

  _save_source_fingerprints(fingerprints_to_save, project_name)

  if num_build_successes != len(build_ops):
    raise compose_exceptions.BuildError(
        'One or more container builds failed.', exit_codes.BUILD_FAILED
    )


def _save_source_fingerprints(
    source_fingerprint_map: Dict[str, Dict[str, str]], project_name: str
) -> None:
  """Saves the source fingerprint map to a JSON file.

  Args:
    source_fingerprint_map: A dictionary mapping container names to a
      dictionary containing their 'fingerprint' and 'image_id'.
    project_name: The name of the project.
  """
  cfg_dir = config.Paths().global_config_dir
  out_dir = os.path.join(cfg_dir, 'surface', 'run', 'compose', project_name)
  files.MakeDir(out_dir)
  fingerprint_file = os.path.join(out_dir, _FINGERPRINTS_FILE_NAME)

  try:
    with files.FileWriter(fingerprint_file) as f:
      json.dump(source_fingerprint_map, f, indent=2)
    log.debug(f"Successfully saved fingerprints to '{fingerprint_file}'.")
  except files.Error as e:
    log.warning(f"Could not write fingerprint file '{fingerprint_file}': {e}")


def _load_source_fingerprints(project_name: str) -> Dict[str, Dict[str, str]]:
  """Loads the source fingerprint map from a JSON file.

  Args:
    project_name: The name of the project.

  Returns:
    A dictionary mapping container names to a dictionary containing their
    'fingerprint' and 'image_id'. Returns an empty map if the file is not
    found or cannot be parsed, as this loading is done on a best-effort basis.
  """
  cfg_dir = config.Paths().global_config_dir
  out_dir = os.path.join(cfg_dir, 'surface', 'run', 'compose', project_name)
  fingerprint_file = os.path.join(out_dir, _FINGERPRINTS_FILE_NAME)

  if os.path.exists(fingerprint_file):
    try:
      with files.FileReader(fingerprint_file) as f:
        return json.load(f)
    except json.JSONDecodeError as e:
      log.warning(
          f"Could not decode fingerprint file '{fingerprint_file}': {e}. "
          'Starting with an empty map.'
      )
      return {}
    except files.Error as e:
      log.warning(
          f"Could not read fingerprint file '{fingerprint_file}': {e}. "
          'Starting with an empty map.'
      )
      return {}
  else:
    log.debug(
        f"Fingerprint file '{fingerprint_file}' not found. "
        'Starting with an empty map.'
    )
    return {}


def _calculate_source_fingerprint(build_config: BuildConfig) -> str:
  """Calculates the fingerprint of the source code."""
  if build_config.context is None:
    return ''
  if not os.path.isdir(build_config.context):
    raise compose_exceptions.BuildError(
        f'Build context path is not a directory: {build_config.context}',
        exit_codes.BUILD_CONTEXT_INVALID,
    )

  sha1 = hashlib.sha256()
  for root, dirs, filenames in os.walk(build_config.context, topdown=True):
    dirs.sort()
    filenames.sort()
    for filename in filenames:
      filepath = os.path.join(root, filename)
      relpath = os.path.relpath(filepath, build_config.context)
      sha1.update(relpath.encode('utf-8'))
      try:
        with files.BinaryFileReader(filepath) as f:
          while chunk := f.read(8192):
            sha1.update(chunk)
      except files.Error as e:
        raise exceptions.Error(
            f'Could not read file {filepath} for fingerprinting: {e}'
        )
  return sha1.hexdigest()


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
    raise compose_exceptions.BuildError(
        '--no-build cannot be used for the first deployment of service'
        f" '{project_name}'.",
        exit_codes.BUILD_NO_BUILD_INVALID,
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


def _build_from_source(
    build_cfg: BuildConfig,
    container: str,
    repo: str,
    project_name: str,
    region: str,
    tracker: progress_tracker.StagedProgressTracker,
) -> tuple[resources.Resource, str, str]:
  """Performs source build for a given container using build config."""
  source_path = build_cfg.context
  if source_path is None:
    raise ValueError('Build context is required for source build.')

  image_tag = '{repo}/{project_name}_{container}:{tag}'.format(
      repo=repo, project_name=project_name, container=container, tag='latest'
  )

  # Get the Cloud Build API message module
  messages = cloudbuild_util.GetMessagesModule()

  # Create the build configuration. This will upload the source
  # and set up the build steps to use the Dockerfile.
  log.debug(
      f"Creating build config for image '{image_tag}' from source"
      f" '{source_path}'"
  )
  build_config = messages.Build(
      steps=[
          messages.BuildStep(
              id=f'Build Docker Image: {image_tag}',
              name='gcr.io/cloud-builders/docker',
              args=['buildx', 'build', '--load', '-t', image_tag, '.'],
          )
      ],
      images=[image_tag],
      timeout='3600s',
  )

  build_config = submit_util.SetSource(
      build_config,
      messages,
      is_specified_source=True,
      no_source=False,
      source=source_path,
      gcs_source_staging_dir=None,
      arg_dir=None,
      arg_revision=None,
      arg_git_source_dir=None,
      arg_git_source_revision=None,
      ignore_file=None,
      hide_logs=True,
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
