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
"""Creates an image from Source."""

import re

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.command_lib.builds import submit_util
from googlecloudsdk.command_lib.run import artifact_registry
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import stages
from googlecloudsdk.command_lib.run.sourcedeploys import sources
from googlecloudsdk.command_lib.run.sourcedeploys import types
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


_BUILD_NAME_PATTERN = re.compile(
    'projects/(?P<projectId>[^/]*)/locations/(?P<location>[^/]*)/builds/(?P<build>[^/]*)'
)
_DEFAULT_IMAGE_REPOSITORY_NAME = '/cloud-run-source-deploy'


# TODO(b/383160656): Bundle these "build_" variables into an object
# pylint:disable=unused-argument - release_track is piped through everywhere.
# It shouldn't be removed just because there are no pre-GA features in progress.
def CreateImage(
    tracker,
    build_image,
    build_source,
    build_pack,
    repo_to_create,
    release_track,
    already_activated_services,
    region: str,
    resource_ref,
    delegate_builds=False,
    base_image=None,
    service_account=None,
    build_worker_pool=None,
    build_machine_type=None,
    build_env_vars=None,
    enable_automatic_updates=False,
    source_bucket=None,
    kms_key=None,
):
  """Creates an image from Source."""
  if repo_to_create:
    tracker.StartStage(stages.CREATE_REPO)
    tracker.UpdateHeaderMessage('Creating Container Repository.')
    artifact_registry.CreateRepository(
        repo_to_create, already_activated_services
    )
    tracker.CompleteStage(stages.CREATE_REPO)

  base_image_from_build = None
  source = None

  tracker.StartStage(stages.UPLOAD_SOURCE)
  if kms_key:
    tracker.UpdateHeaderMessage('Using the source from the specified bucket.')
    _ValidateCmekDeployment(
        build_source, build_image, kms_key
    )
    source = sources.GetGcsObject(build_source)
  else:
    tracker.UpdateHeaderMessage('Uploading sources.')
    source = sources.Upload(build_source, region, resource_ref, source_bucket)
  tracker.CompleteStage(stages.UPLOAD_SOURCE)
  submit_build_request = _PrepareSubmitBuildRequest(
      build_image,
      build_pack,
      region,
      base_image,
      source,
      resource_ref,
      service_account,
      build_worker_pool,
      build_machine_type,
      build_env_vars,
      enable_automatic_updates,
      release_track,
  )
  try:
    response_dict, build_log_url, base_image_from_build = _SubmitBuild(
        tracker,
        submit_build_request,
    )
  except apitools_exceptions.HttpNotFoundError as e:
    # This happens if user didn't have permission to access the builds API.
    if base_image or delegate_builds:
      # If the customer enabled automatic base image updates or set the
      # --delegate-builds falling back is not possible.
      raise e

    # If the user didn't explicitly opt-in to the API, we can fall back to
    # the old client orchestrated builds functionality.
    response_dict, build_log_url = _CreateImageWithoutSubmitBuild(
        tracker,
        build_image,
        build_source,
        build_pack,
        already_activated_services,
        remote_source=source,
    )

  if response_dict and response_dict['status'] != 'SUCCESS':
    tracker.FailStage(
        stages.BUILD_READY,
        None,
        message=(
            'Container build failed and '
            'logs are available at [{build_log_url}].'.format(
                build_log_url=build_log_url
            )
        ),
    )
    return None, None, None, None, None  # Failed to create an image
  else:
    tracker.CompleteStage(stages.BUILD_READY)
    return (
        response_dict['results']['images'][0]['digest'],
        base_image_from_build,
        response_dict['id'],
        source,
        response_dict['name'],
    )


def _CreateImageWithoutSubmitBuild(
    tracker,
    build_image,
    build_source,
    build_pack,
    already_activated_services,
    remote_source,
):
  """Creates an image from source by calling GCB direcly, bypassing the SubmitBuild API."""
  build_messages, build_config = _PrepareBuildConfig(
      tracker,
      build_image,
      build_source,
      build_pack,
      remote_source,
  )
  response_dict, build_log_url = _BuildFromSource(
      tracker,
      build_messages,
      build_config,
      skip_activation_prompt=already_activated_services,
  )
  return response_dict, build_log_url


def _PrepareBuildConfig(
    tracker,
    build_image,
    build_source,
    build_pack,
    remote_source,
):
  """Prepare build config for cloud build."""

  build_messages = cloudbuild_util.GetMessagesModule()

  if remote_source:
    # add the source uri as a label to the image
    # https://github.com/GoogleCloudPlatform/buildpacks/blob/main/cmd/utils/label/README.md
    uri = sources.GetGsutilUri(remote_source)
    if build_pack is not None:
      envs = build_pack[0].get('envs', [])
      envs.append(f'GOOGLE_LABEL_SOURCE={uri}')  # "google.source"
      build_pack[0].update({'envs': envs})

    # force disable Kaniko since we don't support customizing the build here.
    properties.VALUES.builds.use_kaniko.Set(False)
    build_config = submit_util.CreateBuildConfig(
        build_image,
        no_cache=False,
        messages=build_messages,
        substitutions=None,
        arg_config=None,
        is_specified_source=True,
        no_source=False,
        source=build_source,
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
        buildpack=build_pack,
        hide_logs=True,
        skip_set_source=True,
        client_tag='gcloudrun',
    )

    # is docker build
    if build_pack is None:
      assert build_config.steps[0].name == 'gcr.io/cloud-builders/gcb-internal'
      # https://docs.docker.com/engine/reference/commandline/image_build/
      build_config.steps[0].args.extend(['--label', f'google.source={uri}'])

    build_config.source = build_messages.Source(
        storageSource=build_messages.StorageSource(
            bucket=remote_source.bucket,
            object=remote_source.name,
            generation=remote_source.generation,
        )
    )
  else:
    tracker.StartStage(stages.UPLOAD_SOURCE)
    tracker.UpdateHeaderMessage('Uploading sources.')
    # force disable Kaniko since we don't support customizing the build here.
    properties.VALUES.builds.use_kaniko.Set(False)
    build_config = submit_util.CreateBuildConfig(
        build_image,
        no_cache=False,
        messages=build_messages,
        substitutions=None,
        arg_config=None,
        is_specified_source=True,
        no_source=False,
        source=build_source,
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
        buildpack=build_pack,
        hide_logs=True,
        client_tag='gcloudrun',
    )
    tracker.CompleteStage(stages.UPLOAD_SOURCE)

  return build_messages, build_config


def _ValidateCmekDeployment(
    source: str, image_repository: str, kms_key: str
) -> None:
  """Validate the CMEK parameters of the deployment."""
  if not kms_key:
    return

  if not sources.IsGcsObject(source):
    raise exceptions.ArgumentError(
        f'Invalid source location: {source}.'
        ' Deployments encrypted with a customer-managed encryption key (CMEK)'
        ' expect the source to be passed in a pre-configured Cloud Storage'
        ' bucket. See'
        ' https://cloud.google.com/run/docs/securing/using-cmek#source-deploy'
        ' for more details.'
    )
  if not image_repository:
    raise exceptions.ArgumentError(
        'Deployments encrypted with a customer-managed encryption key (CMEK)'
        ' require a pre-configured Artifact Registry repository to be passed'
        ' via the `--image` flag. See'
        ' https://cloud.google.com/run/docs/securing/using-cmek#source-deploy'
        ' for more details.'
    )
  if _IsDefaultImageRepository(image_repository):
    raise exceptions.ArgumentError(
        'The default Artifact Registry repository can not be used when'
        ' deploying with a customer-managed encryption key (CMEK). Please'
        ' provide a pre-configured repository using the `--image` flag. See'
        ' https://cloud.google.com/run/docs/securing/using-cmek#source-deploy'
        ' for more details.'
    )


def _BuildFromSource(
    tracker, build_messages, build_config, skip_activation_prompt=False
):
  """Build an image from source if a user specifies a source when deploying."""
  build_region = cloudbuild_util.DEFAULT_REGION
  build, _ = submit_util.Build(
      build_messages,
      True,
      build_config,
      hide_logs=True,
      build_region=build_region,
      skip_activation_prompt=skip_activation_prompt,
  )
  build_op = f'projects/{build.projectId}/locations/{build_region}/operations/{build.id}'
  build_op_ref = resources.REGISTRY.ParseRelativeName(
      build_op, collection='cloudbuild.projects.locations.operations'
  )
  build_log_url = build.logUrl
  tracker.StartStage(stages.BUILD_READY)
  tracker.UpdateHeaderMessage('Building Container.')
  tracker.UpdateStage(
      stages.BUILD_READY,
      'Logs are available at [{build_log_url}].'.format(
          build_log_url=build_log_url
      ),
  )

  response_dict = _PollUntilBuildCompletes(build_op_ref)
  return response_dict, build_log_url


def _PrepareSubmitBuildRequest(
    docker_image,
    build_pack,
    region,
    base_image,
    source,
    resource_ref,
    service_account,
    build_worker_pool,
    build_machine_type,
    build_env_vars,
    enable_automatic_updates,
    release_track,
):
  """Upload the provided build source and prepare submit build request."""
  messages = apis.GetMessagesModule(global_methods.SERVERLESS_API_NAME, 'v2')
  parent = 'projects/{project}/locations/{region}'.format(
      project=properties.VALUES.core.project.Get(required=True), region=region
  )
  storage_source = messages.GoogleCloudRunV2StorageSource(
      bucket=source.bucket, object=source.name, generation=source.generation
  )
  tags = _GetBuildTags(resource_ref)

  if build_pack:
    # submit a buildpacks build
    function_target = None
    project_descriptor = build_pack[0].get('project_descriptor', None)
    for env in build_pack[0].get('envs', []):
      if env.startswith('GOOGLE_FUNCTION_TARGET'):
        function_target = env.split('=')[1]

    if build_env_vars is not None:
      build_env_vars = messages.GoogleCloudRunV2BuildpacksBuild.EnvironmentVariablesValue(
          additionalProperties=[
              messages.GoogleCloudRunV2BuildpacksBuild.EnvironmentVariablesValue.AdditionalProperty(
                  key=key, value=value
              )
              for key, value in sorted(build_env_vars.items())
          ]
      )
    return messages.RunProjectsLocationsBuildsSubmitRequest(
        parent=parent,
        googleCloudRunV2SubmitBuildRequest=messages.GoogleCloudRunV2SubmitBuildRequest(
            storageSource=storage_source,
            imageUri=build_pack[0].get('image'),
            buildpackBuild=messages.GoogleCloudRunV2BuildpacksBuild(
                baseImage=base_image,
                functionTarget=function_target,
                environmentVariables=build_env_vars,
                enableAutomaticUpdates=enable_automatic_updates,
                projectDescriptor=project_descriptor,
            ),
            dockerBuild=None,
            tags=tags,
            serviceAccount=service_account,
            workerPool=build_worker_pool,
            machineType=build_machine_type,
            releaseTrack=_MapToReleaseTrackEnum(release_track, messages),
        ),
    )

  # submit a docker build
  return messages.RunProjectsLocationsBuildsSubmitRequest(
      parent=parent,
      googleCloudRunV2SubmitBuildRequest=messages.GoogleCloudRunV2SubmitBuildRequest(
          storageSource=storage_source,
          imageUri=docker_image,
          buildpackBuild=None,
          dockerBuild=messages.GoogleCloudRunV2DockerBuild(),
          tags=tags,
          serviceAccount=service_account,
          workerPool=build_worker_pool,
          machineType=build_machine_type,
          releaseTrack=_MapToReleaseTrackEnum(release_track, messages),
      ),
  )


def _GetBuildTags(resource_ref):
  return [f'{types.GetKind(resource_ref)}_{resource_ref.Name()}']


def _SubmitBuild(
    tracker,
    submit_build_request,
):
  """Call Build API to submit a build.

  Arguments:
    tracker: StagedProgressTracker, to report on the progress of releasing.
    submit_build_request: SubmitBuildRequest, the request to submit build.

  Returns:
    response_dict: Build resource returned by Cloud build.
    build_log_url: The url to build log
    build_response.baseImageUri: The rectified uri of the base image that should
    be used in automatic base image update.
  """
  run_client = apis.GetClientInstance(global_methods.SERVERLESS_API_NAME, 'v2')
  build_messages = cloudbuild_util.GetMessagesModule()

  build_response = run_client.projects_locations_builds.Submit(
      submit_build_request
  )
  if build_response.baseImageWarning:
    tracker.AddWarning(build_response.baseImageWarning)
  build_op = build_response.buildOperation
  json = encoding.MessageToJson(build_op.metadata)
  build = encoding.JsonToMessage(
      build_messages.BuildOperationMetadata, json
  ).build
  build_region = _GetBuildRegion(build.name)
  name = f'projects/{build.projectId}/locations/{build_region}/operations/{build.id}'

  build_op_ref = resources.REGISTRY.ParseRelativeName(
      name, collection='cloudbuild.projects.locations.operations'
  )
  build_log_url = build.logUrl
  tracker.StartStage(stages.BUILD_READY)
  tracker.UpdateHeaderMessage('Building Container.')
  tracker.UpdateStage(
      stages.BUILD_READY,
      'Logs are available at [{build_log_url}].'.format(
          build_log_url=build_log_url
      ),
  )
  response_dict = _PollUntilBuildCompletes(build_op_ref)
  return response_dict, build_log_url, build_response.baseImageUri


def _PollUntilBuildCompletes(build_op_ref):
  client = cloudbuild_util.GetClientInstance()
  poller = waiter.CloudOperationPoller(
      client.projects_builds, client.operations
  )
  operation = waiter.PollUntilDone(poller, build_op_ref)
  return encoding.MessageToPyValue(operation.response)


def _GetBuildRegion(build_name):
  match = _BUILD_NAME_PATTERN.match(build_name)
  if match:
    return match.group('location')
  raise ValueError(f'Invalid build name: {build_name}')


def _IsDefaultImageRepository(image_repository: str) -> bool:
  """Checks if the image repository is the default one."""
  return _DEFAULT_IMAGE_REPOSITORY_NAME in image_repository


def _MapToReleaseTrackEnum(release_track, messages):
  """Returns the enum value for the release track."""
  release_track_enum_value = None
  if release_track and release_track != calliope_base.ReleaseTrack.GA:
    release_track_enum_cls = (
        messages.GoogleCloudRunV2SubmitBuildRequest.ReleaseTrackValueValuesEnum
    )
    release_track_enum_value = release_track_enum_cls(release_track.name)
  return release_track_enum_value
