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
"""Utilities for the cloud deploy release commands."""


import datetime
import enum
import os.path
import shutil
import tarfile
import uuid

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.cloudbuild import snapshot
from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.api_lib.clouddeploy import delivery_pipeline
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.deploy import deploy_util
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.command_lib.deploy import rollout_util
from googlecloudsdk.command_lib.deploy import skaffold_util
from googlecloudsdk.command_lib.deploy import staging_bucket_util
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import times
import six


_RELEASE_COLLECTION = (
    'clouddeploy.projects.locations.deliveryPipelines.releases'
)
_ALLOWED_SOURCE_EXT = ['.zip', '.tgz', '.gz']
_SOURCE_STAGING_TEMPLATE = 'gs://{}/source'
RESOURCE_NOT_FOUND = (
    'The following resources are snapped in the release, '
    'but no longer exist:\n{}\n\nThese resources were cached '
    'when the release was created, but their source '
    'may have been deleted.\n\n'
)
RESOURCE_CREATED = (
    'The following target is not snapped in the release:\n{}\n\n'
    "You may have specified a target that wasn't "
    'cached when the release was created.\n\n'
)
RESOURCE_CHANGED = (
    'The following snapped releases resources differ from '
    'their current definition:\n{}\n\nThe pipeline or targets '
    'were cached when the release was created, but the source '
    'has changed since then. You should review the differences '
    'before proceeding.\n'
)
_DATE_PATTERN = '$DATE'
_TIME_PATTERN = '$TIME'


GENERATED_SKAFFOLD = 'skaffold.yaml'


class Tools(enum.Enum):
  DOCKER = 'docker'
  HELM = 'helm'
  KPT = 'kpt'
  KUBECTL = 'kubectl'
  KUSTOMIZE = 'kustomize'
  SKAFFOLD = 'skaffold'


def RenderPattern(release_id):
  """Finds and replaces keywords in the release name.

    When adding to the list of keywords that can be expanded, care must be taken
    when two words share the same prefix ie. ($D and $DATE). In that case the
    longer keyword ($DATE) must be processed before the shorter one ($D).
  Args:
    release_id: str, the release name template.

  Returns:
    The formatted release name
  """
  time_now = datetime.datetime.utcnow()
  formatted_id = release_id.replace(_DATE_PATTERN, time_now.strftime('%Y%m%d'))
  formatted_id = formatted_id.replace(_TIME_PATTERN, time_now.strftime('%H%M'))
  _CheckForRemainingDollars(formatted_id)
  return formatted_id


def _CheckForRemainingDollars(release_id):
  """Find and notify user about dollar signs in release name."""

  dollar_positions = []
  for i in range(len(release_id)):
    if release_id[i] == '$':
      dollar_positions.append(six.text_type(i))
  if dollar_positions:
    raise exceptions.InvalidReleaseNameError(release_id, dollar_positions)


def SetBuildArtifacts(images, messages, release_config):
  """Set build_artifacts field of the release message.

  Args:
    images: dict[str,dict], docker image name and tag dictionary.
    messages: Module containing the Cloud Deploy messages.
    release_config: apitools.base.protorpclite.messages.Message, Cloud Deploy
      release message.

  Returns:
    Cloud Deploy release message.
  """
  if not images:
    return release_config
  build_artifacts = []
  for key, value in sorted(six.iteritems(images)):  # Sort for tests
    build_artifacts.append(messages.BuildArtifact(image=key, tag=value))
  release_config.buildArtifacts = build_artifacts

  return release_config


def LoadBuildArtifactFile(path):
  """Load images from a file containing JSON build data.

  Args:
    path: str, build artifacts file path.

  Returns:
    Docker image name and tag dictionary.
  """
  with files.FileReader(path) as f:  # Returns user-friendly error messages
    try:
      structured_data = yaml.load(f, file_hint=path)
    except yaml.Error as e:
      raise exceptions.ParserError(path, e.inner_error)
    images = {}
    for build in structured_data['builds']:
      # For b/191063894. Supporting both name for now.
      images[build.get('image', build.get('imageName'))] = build['tag']

    return images


def CreateReleaseConfig(
    source,
    gcs_source_staging_dir,
    ignore_file,
    images,
    build_artifacts,
    description,
    docker_version,
    helm_version,
    kpt_version,
    kubectl_version,
    kustomize_version,
    skaffold_version,
    skaffold_file,
    location,
    pipeline_uuid,
    from_k8s_manifest,
    from_run_manifest,
    pipeline_obj,
    deploy_parameters=None,
    hide_logs=False,
):
  """Returns a build config."""

  # If either a kubernetes manifest or Cloud Run manifest was given, this means
  # a Skaffold file should be generated, so we should not check at this stage
  # if the Skaffold file exists.
  if not (from_k8s_manifest or from_run_manifest):
    _VerifySkaffoldFileExists(source, skaffold_file)

  messages = client_util.GetMessagesModule(client_util.GetClientInstance())
  release_config = messages.Release()
  release_config.description = description
  release_config = _SetSource(
      release_config,
      source,
      gcs_source_staging_dir,
      ignore_file,
      location,
      pipeline_uuid,
      from_k8s_manifest,
      from_run_manifest,
      skaffold_file,
      pipeline_obj,
      hide_logs,
  )
  release_config = _SetVersion(
      release_config,
      messages,
      docker_version,
      helm_version,
      kpt_version,
      kubectl_version,
      kustomize_version,
      skaffold_version,
  )
  release_config = _SetImages(messages, release_config, images, build_artifacts)
  release_config = _SetDeployParameters(
      messages,
      deploy_util.ResourceType.RELEASE,
      release_config,
      deploy_parameters,
  )

  return release_config


def _CreateAndUploadTarball(
    gcs_client,
    gcs_source_staging,
    source,
    ignore_file,
    hide_logs,
):
  """Creates a local tarball and uploads it to GCS.

     After creating and uploading the tarball, this sets the Skaffold config URI
     in the release config.

  Args:
    gcs_client: client for Google Cloud Storage API.
    gcs_source_staging: directory in Google cloud storage to use for staging
    source: the location of the source files
    ignore_file: the ignore file to use
    hide_logs: whether to show logs, defaults to False

  Returns:
    the gcs uri where the tarball was uploaded.
  """
  source_snapshot = snapshot.Snapshot(source, ignore_file=ignore_file)
  size_str = resource_transform.TransformSize(source_snapshot.uncompressed_size)
  if not hide_logs:
    log.status.Print(
        'Creating temporary archive of {num_files} file(s)'
        ' totalling {size} before compression.'.format(
            num_files=len(source_snapshot.files), size=size_str
        )
    )
  # This makes a tarball of the snapshot and then copies to GCS.
  staged_source_obj = source_snapshot.CopyArchiveToGCS(
      gcs_client,
      gcs_source_staging,
      ignore_file=ignore_file,
      hide_logs=hide_logs,
  )
  return 'gs://{bucket}/{object}'.format(
      bucket=staged_source_obj.bucket, object=staged_source_obj.name
  )


def _SetVersion(
    release_config,
    messages,
    docker_version,
    helm_version,
    kpt_version,
    kubectl_version,
    kustomize_version,
    skaffold_version,
):
  """Set the version for the release config.

  Sets the ToolVersions for the release config or the SkaffoldVersion for the
  release config.

  The ToolVersions are always used if any of the tool version fields are set:
    docker_version
    helm_version
    kpt_version
    kubectl_version
    kustomize_version
  The ToolVersion of skaffold_version is only used if and only if the specified
  version is a full semver or 'latest'.

  The SkaffoldVersion on the release config is set if and only if
  skaffold_version is the only version specified and it does not match the
  full semver or 'latest'. This is purposefully done to allow uses to continue
  referencing existing supported Cloud Deploy images: e.g. 2.14/2.16.

  Args:
    release_config: a Release message
    messages: Module containing the Cloud Deploy messages.
    docker_version: the docker version to use, can be None.
    helm_version: the helm version to use, can be None.
    kpt_version: the kpt version to use, can be None.
    kubectl_version: the kubectl version to use, can be None.
    kustomize_version: the kustomize version to use, can be None.
    skaffold_version: the skaffold version to use, can be None.

  Returns:
    Modified release_config
  """
  # None and empty strings are handled in this manner.
  should_default = (
      not docker_version
      and not helm_version
      and not kpt_version
      and not kubectl_version
      and not kustomize_version
      and not skaffold_version
  )
  if should_default:
    return release_config
  # Skaffold is a different case because we want to allow users that specify
  # 2.14/2.16 to continue being able to do so until the image is expired.
  should_skaffold_use_tool_version = skaffold_version == 'latest' or (
      skaffold_version and skaffold_version.count('.') == 2
  )
  use_tool_version = (
      docker_version
      or helm_version
      or kpt_version
      or kubectl_version
      or kustomize_version
      or should_skaffold_use_tool_version
  )
  if not use_tool_version:
    release_config.skaffoldVersion = skaffold_version
    return release_config
  tool_versions = messages.ToolVersions(
      docker=docker_version,
      helm=helm_version,
      kpt=kpt_version,
      kubectl=kubectl_version,
      kustomize=kustomize_version,
      skaffold=skaffold_version,
  )
  release_config.toolVersions = tool_versions
  return release_config


def _SetSource(
    release_config,
    source,
    gcs_source_staging_dir,
    ignore_file,
    location,
    pipeline_uuid,
    kubernetes_manifest,
    cloud_run_manifest,
    skaffold_file,
    pipeline_obj,
    hide_logs=False,
):
  """Set the source for the release config.

  Sets the source for the release config and creates a default Cloud Storage
  bucket with location for staging if gcs-source-staging-dir is not specified.

  Args:
    release_config: a Release message
    source: the location of the source files
    gcs_source_staging_dir: directory in google cloud storage to use for staging
    ignore_file: the ignore file to use
    location: the cloud region for the release
    pipeline_uuid: the unique id of the release's parent pipeline.
    kubernetes_manifest: path to kubernetes manifest (e.g. /home/user/k8.yaml).
      If provided, a Skaffold file will be generated and uploaded to GCS on
      behalf of the customer.
    cloud_run_manifest: path to Cloud Run manifest (e.g.
      /home/user/service.yaml).If provided, a Skaffold file will be generated
      and uploaded to GCS on behalf of the customer.
    skaffold_file: path of the skaffold file relative to the source directory
      that contains the Skaffold file.
    pipeline_obj: the pipeline_obj used for this release.
    hide_logs: whether to show logs, defaults to False

  Returns:
    Modified release_config
  """
  default_gcs_source = False
  default_bucket_name = staging_bucket_util.GetDefaultStagingBucket(
      pipeline_uuid
  )

  if gcs_source_staging_dir is None:
    default_gcs_source = True
    gcs_source_staging_dir = _SOURCE_STAGING_TEMPLATE.format(
        default_bucket_name
    )

  if not gcs_source_staging_dir.startswith('gs://'):
    raise c_exceptions.InvalidArgumentException(
        parameter_name='--gcs-source-staging-dir',
        message=gcs_source_staging_dir,
    )

  gcs_client = storage_api.StorageClient()
  suffix = '.tgz'
  if source.startswith('gs://') or os.path.isfile(source):
    _, suffix = os.path.splitext(source)

  # Next, stage the source to Cloud Storage.
  staged_object = '{stamp}-{uuid}{suffix}'.format(
      stamp=times.GetTimeStampFromDateTime(times.Now()),
      uuid=uuid.uuid4().hex,
      suffix=suffix,
  )
  gcs_source_staging_dir = resources.REGISTRY.Parse(
      gcs_source_staging_dir, collection='storage.objects'
  )

  try:
    gcs_client.CreateBucketIfNotExists(
        gcs_source_staging_dir.bucket,
        location=location,
        check_ownership=default_gcs_source,
        enable_uniform_level_access=True,
        enable_public_access_prevention=True,
    )
  except storage_api.BucketInWrongProjectError:
    # If we're using the default bucket but it already exists in a different
    # project, then it could belong to a malicious attacker (b/33046325).
    raise c_exceptions.RequiredArgumentException(
        'gcs-source-staging-dir',
        'A bucket with name {} already exists and is owned by '
        'another project. Specify a bucket using '
        '--gcs-source-staging-dir.'.format(default_bucket_name),
    )

  if gcs_source_staging_dir.object:
    staged_object = gcs_source_staging_dir.object + '/' + staged_object
  gcs_source_staging = resources.REGISTRY.Create(
      collection='storage.objects',
      bucket=gcs_source_staging_dir.bucket,
      object=staged_object,
  )

  gcs_uri = ''
  skaffold_is_generated = False
  if source.startswith('gs://'):
    gcs_source = resources.REGISTRY.Parse(source, collection='storage.objects')
    staged_source_obj = gcs_client.Rewrite(gcs_source, gcs_source_staging)
    gcs_uri = 'gs://{bucket}/{object}'.format(
        bucket=staged_source_obj.bucket, object=staged_source_obj.name
    )
  else:
    # If a Skaffold file should be generated
    if kubernetes_manifest or cloud_run_manifest:
      skaffold_is_generated = True
      gcs_uri = _UploadTarballGeneratedSkaffoldAndManifest(
          kubernetes_manifest,
          cloud_run_manifest,
          gcs_client,
          gcs_source_staging,
          ignore_file,
          hide_logs,
          pipeline_obj,
      )
    elif os.path.isdir(source):
      gcs_uri = _CreateAndUploadTarball(
          gcs_client,
          gcs_source_staging,
          source,
          ignore_file,
          hide_logs,
      )
    # When its a tar file
    elif os.path.isfile(source):
      if not hide_logs:
        log.status.Print(
            'Uploading local file [{src}] to [gs://{bucket}/{object}].'.format(
                src=source,
                bucket=gcs_source_staging.bucket,
                object=gcs_source_staging.object,
            )
        )
      staged_source_obj = gcs_client.CopyFileToGCS(source, gcs_source_staging)
      gcs_uri = 'gs://{bucket}/{object}'.format(
          bucket=staged_source_obj.bucket, object=staged_source_obj.name
      )

  release_config = _SetSkaffoldConfigPath(
      release_config, skaffold_file, skaffold_is_generated
  )
  release_config.skaffoldConfigUri = gcs_uri

  return release_config


def _GetProfileToTargetMapping(pipeline_obj):
  """Get mapping of profile to list of targets where the profile is activated."""
  profile_to_targets = {}
  for stage in pipeline_obj.serialPipeline.stages:
    for profile in stage.profiles:
      if profile not in profile_to_targets:
        profile_to_targets[profile] = []
      profile_to_targets[profile].append(stage.targetId)
  return profile_to_targets


def _GetUniqueProfilesToTargetMapping(profile_to_targets):
  """Get mapping of profile to target that is only activated in a single target."""
  target_to_unique_profile = {}
  for profile, targets in profile_to_targets.items():
    if len(targets) == 1:
      target_to_unique_profile[targets[0]] = profile
  return target_to_unique_profile


def _GetTargetAndUniqueProfiles(pipeline_obj):
  """Get one unique profile for every target if it exists.

  Args:
    pipeline_obj: The Delivery Pipeline object.

  Returns:
    A map of target_id to profile.

  Raises:
   Error: If the pipeline targets don't each have a dedicated profile.
  """
  profile_to_targets = _GetProfileToTargetMapping(pipeline_obj)
  target_to_unique_profile = _GetUniqueProfilesToTargetMapping(
      profile_to_targets
  )

  # Every target should have one unique profile.
  if len(target_to_unique_profile) != len(pipeline_obj.serialPipeline.stages):
    raise core_exceptions.Error(
        'Target should use one profile not shared with another target.'
    )
  return target_to_unique_profile


def _UploadTarballGeneratedSkaffoldAndManifest(
    kubernetes_manifest,
    cloud_run_manifest,
    gcs_client,
    gcs_source_staging,
    ignore_file,
    hide_logs,
    pipeline_obj,
):
  """Generates a Skaffold file and uploads the file and k8 manifest to GCS.

  Args:
    kubernetes_manifest: path to kubernetes manifest (e.g. /home/user/k8.yaml).
      If provided, a Skaffold file will be generated and uploaded to GCS on
      behalf of the customer.
    cloud_run_manifest: path to Cloud Run manifest (e.g.
      /home/user/service.yaml). If provided, a Skaffold file will be generated
      and uploaded to GCS on behalf of the customer.
    gcs_client: client for Google Cloud Storage API.
    gcs_source_staging: directory in google cloud storage to use for staging
    ignore_file: the ignore file to use
    hide_logs: whether to show logs, defaults to False
    pipeline_obj: the pipeline_obj used for this release.

  Returns:
    the gcs uri where the tarball was uploaded.
  """
  with files.TemporaryDirectory() as temp_dir:
    manifest = ''
    skaffold_yaml = ''
    if kubernetes_manifest:
      manifest = kubernetes_manifest
      skaffold_yaml = skaffold_util.CreateSkaffoldFileForManifest(
          pipeline_obj,
          os.path.basename(manifest),
          skaffold_util.GKE_GENERATED_SKAFFOLD_TEMPLATE,
      )
    elif cloud_run_manifest:
      manifest = cloud_run_manifest
      skaffold_yaml = skaffold_util.CreateSkaffoldFileForManifest(
          pipeline_obj,
          os.path.basename(manifest),
          skaffold_util.CLOUD_RUN_GENERATED_SKAFFOLD_TEMPLATE,
      )
    # Check that the manifest file exists.
    if not os.path.exists(manifest):
      raise c_exceptions.BadFileException(
          'could not find manifest file [{src}]'.format(src=manifest)
      )
    # Create the YAML data. Copying to a temp directory to avoid editing
    # the local directory.
    shutil.copy(manifest, temp_dir)

    skaffold_path = os.path.join(temp_dir, GENERATED_SKAFFOLD)
    with files.FileWriter(skaffold_path) as f:
      # Prepend the auto-generated line to the YAML file
      f.write('# Auto-generated by Google Cloud Deploy\n')
      # Dump the yaml data to the Skaffold file.
      yaml.dump(skaffold_yaml, f, round_trip=True)
    gcs_uri = _CreateAndUploadTarball(
        gcs_client,
        gcs_source_staging,
        temp_dir,
        ignore_file,
        hide_logs,
    )
    log.status.Print(
        'Generated Skaffold file can be found here: {gcs_uri}'.format(
            gcs_uri=gcs_uri,
        )
    )
    return gcs_uri


def _VerifySkaffoldFileExists(source, skaffold_file):
  """Checks that the specified source contains a skaffold file.

  Args:
    source: the location of the source files
    skaffold_file: path of the skaffold file relative to the source directory

  Raises:
    BadFileException: If the source directory or files can't be found.
  """
  if not skaffold_file:
    skaffold_file = 'skaffold.yaml'
  if source.startswith('gs://'):
    log.status.Print(
        'Skipping skaffold file check. '
        'Reason: source is not a local archive or directory'
    )
  elif not os.path.exists(source):
    raise c_exceptions.BadFileException(
        'could not find source [{src}]'.format(src=source)
    )
  elif os.path.isfile(source):
    _VerifySkaffoldFileIsInArchive(source, skaffold_file)
  else:
    _VerifySkaffoldFileIsInFolder(source, skaffold_file)


def _VerifySkaffoldFileIsInArchive(source, skaffold_file):
  """Verifies the skaffold or deploy config file is in the archive.

  Args:
    source: the location of the source archive.
    skaffold_file: path of the skaffold file in the source archive.

  Raises:
    BadFileException: If the config file is not a readable compressed file or
    can't be found.
  """
  _, ext = os.path.splitext(source)
  if ext not in _ALLOWED_SOURCE_EXT:
    raise c_exceptions.BadFileException(
        'local file [{src}] is none of ' + ', '.join(_ALLOWED_SOURCE_EXT)
    )
  if not tarfile.is_tarfile(source):
    raise c_exceptions.BadFileException(
        'Specified source file is not a readable compressed file archive'
    )
  with tarfile.open(source, mode='r:gz') as archive:
    try:
      archive.getmember(skaffold_file)
    except KeyError:
      raise c_exceptions.BadFileException(
          'Could not find skaffold file. File [{skaffold}]'
          ' does not exist in source archive'.format(skaffold=skaffold_file)
      )


def _VerifySkaffoldFileIsInFolder(source, skaffold_file):
  """Verifies the skaffold or deploy config file is in the folder.

  Args:
    source: the location of the source files
    skaffold_file: path of the skaffold file relative to the source directory

  Raises:
    BadFileException: If the config file can't be found.
  """
  path_to_skaffold = os.path.join(source, skaffold_file)
  if not os.path.exists(path_to_skaffold):
    raise c_exceptions.BadFileException(
        'Could not find skaffold file. File [{skaffold}] does not exist'.format(
            skaffold=path_to_skaffold
        )
    )


def _SetImages(messages, release_config, images, build_artifacts):
  """Set the image substitutions for the release config."""
  if build_artifacts:
    images = LoadBuildArtifactFile(build_artifacts)

  return SetBuildArtifacts(images, messages, release_config)


def _SetSkaffoldConfigPath(release_config, skaffold_file, is_generated):
  """Set the path for skaffold configuration file relative to source directory."""
  if skaffold_file:
    release_config.skaffoldConfigPath = skaffold_file
  if is_generated:
    release_config.skaffoldConfigPath = GENERATED_SKAFFOLD

  return release_config


def _SetDeployParameters(
    messages, resource_type, release_config, deploy_parameters
):
  """Set the deploy parameters for the release config."""
  if deploy_parameters:
    dps_value_msg = getattr(messages, resource_type.value).DeployParametersValue
    dps_value = dps_value_msg()
    for key, value in deploy_parameters.items():
      dps_value.additionalProperties.append(
          dps_value_msg.AdditionalProperty(key=key, value=value)
      )

    release_config.deployParameters = dps_value
  return release_config


def ListCurrentDeployedTargets(release_ref, targets):
  """Lists the targets where the given release is the latest.

  Args:
    release_ref: protorpc.messages.Message, protorpc.messages.Message, release
      reference.
    targets: protorpc.messages.Message, protorpc.messages.Message, list of
      target objects.

  Returns:
    A list of target references where this release is deployed.
  """
  matching_targets = []
  release_name = release_ref.RelativeName()
  pipeline_ref = release_ref.Parent()
  for obj in targets:
    target_name = obj.name
    target_ref = target_util.TargetReferenceFromName(target_name)
    # Gets the latest rollout of this target
    rollout_obj = target_util.GetCurrentRollout(target_ref, pipeline_ref)
    if rollout_obj is None:
      continue
    rollout_ref = rollout_util.RolloutReferenceFromName(rollout_obj.name)
    deployed_release_name = rollout_ref.Parent().RelativeName()
    if release_name == deployed_release_name:
      matching_targets.append(target_ref)
  return matching_targets


def DiffSnappedPipeline(release_ref, release_obj, to_target=None):
  """Detects the differences between current delivery pipeline and target definitions, from those associated with the release being promoted.

  Changes are determined through etag value differences.

  This runs the following checks:
    - if the to_target is one of the snapped targets in the release.
    - if the snapped targets still exist.
    - if the snapped targets have been changed.
    - if the snapped pipeline still exists.
    - if the snapped pipeline has been changed.

  Args:
    release_ref: protorpc.messages.Message, release resource object.
    release_obj: apitools.base.protorpclite.messages.Message, release message.
    to_target: str, the target to promote the release to. If specified, this
      verifies if the target has been snapped in the release.

  Returns:
    the list of the resources that no longer exist.
    the list of the resources that have been changed.
    the list of the resources that aren't snapped in the release.
  """
  resource_not_found = []
  resource_changed = []
  resource_created = []
  # check if the to_target is one of the snapped targets in the release.
  if to_target:
    ref_dict = release_ref.AsDict()
    # Creates shared target by default.
    target_ref = target_util.TargetReference(
        to_target,
        ref_dict['projectsId'],
        ref_dict['locationsId'],
    )
    # Only compare the resource ID, for the case that
    # if release_ref is parsed from arguments, it will use project ID,
    # whereas, the project number is stored in the DB.

    if target_ref.Name() not in [
        target_util.TargetId(obj.name) for obj in release_obj.targetSnapshots
    ]:
      resource_created.append(target_ref.RelativeName())

  for obj in release_obj.targetSnapshots:
    target_name = obj.name
    # Check if the snapped targets still exist.
    try:
      target_obj = target_util.GetTarget(
          target_util.TargetReferenceFromName(target_name)
      )
      # Checks if the snapped targets have been changed.
      if target_obj.etag != obj.etag:
        resource_changed.append(target_name)
    except apitools_exceptions.HttpError as error:
      log.debug('Failed to get target {}: {}'.format(target_name, error))
      log.status.Print('Unable to get target {}\n'.format(target_name))
      resource_not_found.append(target_name)

  name = release_obj.deliveryPipelineSnapshot.name
  # Checks if the pipeline exists.
  try:
    pipeline_obj = delivery_pipeline.DeliveryPipelinesClient().Get(name)
    # Checks if the pipeline has been changed.
    if pipeline_obj.etag != release_obj.deliveryPipelineSnapshot.etag:
      resource_changed.append(release_ref.Parent().RelativeName())
  except apitools_exceptions.HttpError as error:
    log.debug('Failed to get pipeline {}: {}'.format(name, error.content))
    log.status.Print('Unable to get delivery pipeline {}'.format(name))
    resource_not_found.append(name)

  return resource_created, resource_changed, resource_not_found


def PrintDiff(release_ref, release_obj, target_id=None, prompt=''):
  """Prints differences between current and snapped delivery pipeline and target definitions.

  Args:
    release_ref: protorpc.messages.Message, release resource object.
    release_obj: apitools.base.protorpclite.messages.Message, release message.
    target_id: str, target id, e.g. test/stage/prod.
    prompt: str, prompt text.
  """
  resource_created, resource_changed, resource_not_found = DiffSnappedPipeline(
      release_ref, release_obj, target_id
  )

  if resource_created:
    prompt += RESOURCE_CREATED.format('\n'.join(BulletedList(resource_created)))
  if resource_not_found:
    prompt += RESOURCE_NOT_FOUND.format(
        '\n'.join(BulletedList(resource_not_found))
    )
  if resource_changed:
    prompt += RESOURCE_CHANGED.format('\n'.join(BulletedList(resource_changed)))

  log.status.Print(prompt)


def BulletedList(str_list):
  """Converts a list of string to a bulleted list.

  The returned list looks like ['- string1','- string2'].

  Args:
    str_list: [str], list to be converted.

  Returns:
    list of the transformed strings.
  """
  for i in range(len(str_list)):
    str_list[i] = '- ' + str_list[i]

  return str_list


def GetSnappedTarget(release_obj, target_id):
  """Get the snapped target in a release by target ID.

  Args:
    release_obj: apitools.base.protorpclite.messages.Message, release message
      object.
    target_id: str, target ID.

  Returns:
    target message object.
  """
  target_obj = None

  for ss in release_obj.targetSnapshots:
    if target_util.TargetId(ss.name) == target_id:
      target_obj = ss
      break

  return target_obj


def CheckReleaseSupportState(release_obj, action):
  """Checks the support state on a release.

  If the release is in maintenance mode, a warning will be logged.
  If the release is in expiration mode, an exception will be raised.

  Args:
    release_obj: The release object to check.
    action: the action that is being performed that requires the check.

  Raises: an core_exceptions.Error if any support state is unsupported
  """
  tools_in_maintenance = []
  tools_unsupported = []
  messages = client_util.GetMessagesModule(client_util.GetClientInstance())
  tools = [
      Tools.DOCKER,
      Tools.HELM,
      Tools.KPT,
      Tools.KUBECTL,
      Tools.KUSTOMIZE,
      Tools.SKAFFOLD,
  ]
  for t in tools:
    state = _GetToolVersionSupportState(release_obj, t)
    if not state:
      continue
    tool_version_enum = (
        messages.ToolVersionSupportedCondition.ToolVersionSupportStateValueValuesEnum
    )
    if state == tool_version_enum.TOOL_VERSION_SUPPORT_STATE_UNSUPPORTED:
      tools_unsupported.append(t)
    elif state == tool_version_enum.TOOL_VERSION_SUPPORT_STATE_MAINTENANCE_MODE:
      tools_in_maintenance.append(t)
    else:
      continue
  # A singular unsupported tool prevents a release from being supported.
  if tools_unsupported:
    joined = ', '.join([t.value for t in tools_unsupported])
    raise core_exceptions.Error(
        f"You can't {action} because the versions used for tools: [{joined}] "
        'are no longer supported.\n'
        'https://cloud.google.com/deploy/docs/select-tool-version'
    )
  if tools_in_maintenance:
    joined = ', '.join([t.value for t in tools_in_maintenance])
    log.status.Print(
        f'WARNING: The versions used for tools: [{joined}] are in maintenance '
        'mode and will be unsupported soon.\n'
        'https://cloud.google.com/deploy/docs/select-tool-version'
    )
    return
  # The old skaffold support state is correctly backfilled even if the release
  # uses tools.
  # This is mostly for releases that don't use tools.
  skaffold_support_state = _GetSkaffoldSupportState(release_obj)
  skaffold_support_state_enum = (
      messages.SkaffoldSupportedCondition.SkaffoldSupportStateValueValuesEnum
  )
  if (
      skaffold_support_state
      == skaffold_support_state_enum.SKAFFOLD_SUPPORT_STATE_UNSUPPORTED
  ):
    raise core_exceptions.Error(
        f"You can't {action} because the Skaffold version that was"
        ' used to create the release is no longer supported.\n'
        'https://cloud.google.com/deploy/docs/using-skaffold/select-skaffold'
        '#skaffold_version_deprecation_and_maintenance_policy'
    )

  if (
      skaffold_support_state
      == skaffold_support_state_enum.SKAFFOLD_SUPPORT_STATE_MAINTENANCE_MODE
  ):
    log.status.Print(
        "WARNING: This release's Skaffold version is in maintenance mode and"
        ' will be unsupported soon.\n'
        ' https://cloud.google.com/deploy/docs/using-skaffold/select-skaffold'
        '#skaffold_version_deprecation_and_maintenance_policy'
    )


def _GetSkaffoldSupportState(release_obj):
  """Gets the Skaffold Support State from the release.

  Args:
    release_obj: release message obj.

  Returns:
    None or SkaffoldSupportStateValueValuesEnum
  """
  # NOMUTANTS
  if release_obj.condition and release_obj.condition.skaffoldSupportedCondition:
    return release_obj.condition.skaffoldSupportedCondition.skaffoldSupportState
  return None


def _GetToolVersionSupportState(release_obj, tool):
  """Gets the Tool Version Support State from the release for a particular tool.

  Args:
    release_obj: release message obj.
    tool: Tools.Enum.

  Returns:
    None or ToolVersionSupportStateValueValuesEnum
  """
  if not release_obj.condition:
    return None
  if tool == Tools.DOCKER:
    if release_obj.condition.dockerVersionSupportedCondition:
      return (
          release_obj.condition.dockerVersionSupportedCondition.toolVersionSupportState
      )
  elif tool == Tools.HELM:
    if release_obj.condition.helmVersionSupportedCondition:
      return (
          release_obj.condition.helmVersionSupportedCondition.toolVersionSupportState
      )
  elif tool == Tools.KPT:
    if release_obj.condition.kptVersionSupportedCondition:
      return (
          release_obj.condition.kptVersionSupportedCondition.toolVersionSupportState
      )
  elif tool == Tools.KUBECTL:
    if release_obj.condition.kubectlVersionSupportedCondition:
      return (
          release_obj.condition.kubectlVersionSupportedCondition.toolVersionSupportState
      )
  elif tool == Tools.KUSTOMIZE:
    if release_obj.condition.kustomizeVersionSupportedCondition:
      return (
          release_obj.condition.kustomizeVersionSupportedCondition.toolVersionSupportState
      )
  elif tool == Tools.SKAFFOLD:
    if release_obj.condition.skaffoldVersionSupportedCondition:
      return (
          release_obj.condition.skaffoldVersionSupportedCondition.toolVersionSupportState
      )
  return None
