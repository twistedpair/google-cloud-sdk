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
"""Support library for creating deployments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import os
import random
import string
import textwrap
import uuid

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.blueprints import blueprints_util
from googlecloudsdk.api_lib.krmapihosting import util as krmapihosting_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.blueprints import deterministic_snapshot
from googlecloudsdk.command_lib.blueprints import error_handling
from googlecloudsdk.command_lib.blueprints import git_blueprint_util
from googlecloudsdk.command_lib.blueprints import staging_bucket_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import times
import six

_PREVIEW_FORMAT_TEXT = 'text'
_PREVIEW_FORMAT_JSON = 'json'
# Name of the CC instance to create if a user requests cluster creation.
_DEFAULT_KRMAPIHOSTING_INSTANCE_PREFIX = 'blueprints-cluster-'
# Length of the random suffix aedded to the CC instance name.
_KRMAPIHOSTING_INSTANCE_SUFFIX_LENGTH = 5
# The Master CIDR block to use for the created KRM API Hosting instance.
# Note: This is set to not conflict with the default ACP CIDR block, which
# is '172.16.0.128/28'
_DEFAULT_KRMAPIHOSTING_MASTER_CIDR_BLOCK = '172.16.0.144/28'

# The maximum amount of time to wait for the long-running operation.
_MAX_WAIT_TIME_MS = 3 * 60 * 60 * 1000


def _UploadSourceDirToGCS(gcs_client, source, gcs_source_staging, ignore_file):
  """Uploads a local directory to GCS.

  Uploads one file at a time rather than tarballing/zipping for compatibility
  with the back-end.

  Args:
    gcs_client: a storage_api.StorageClient instance for interacting with GCS.
    source: string, a path to a local directory.
    gcs_source_staging: resources.Resource, the bucket to upload to. This must
      already exist.
    ignore_file: optional string, a path to a gcloudignore file.
  """

  source_snapshot = deterministic_snapshot.DeterministicSnapshot(
      source, ignore_file=ignore_file)

  size_str = resource_transform.TransformSize(source_snapshot.uncompressed_size)
  log.status.Print('Uploading {num_files} file(s)'
                   ' totalling {size}.'.format(
                       num_files=len(source_snapshot.files), size=size_str))

  for file_metadata in source_snapshot.GetSortedFiles():
    full_local_path = os.path.join(file_metadata.root, file_metadata.path)

    target_obj_ref = 'gs://{0}/{1}/{2}'.format(gcs_source_staging.bucket,
                                               gcs_source_staging.object,
                                               file_metadata.path)
    target_obj_ref = resources.REGISTRY.Parse(
        target_obj_ref, collection='storage.objects')

    gcs_client.CopyFileToGCS(full_local_path, target_obj_ref)


def _UploadSourceToGCS(source, stage_bucket, ignore_file):
  """Uploads local content to GCS.

  This will ensure that the source and destination exist before triggering the
  upload.

  Args:
    source: string, a local path.
    stage_bucket: optional string. When not provided, the default staging bucket
      will be used (see GetDefaultStagingBucket). This string is of the
      format "gs://bucket-name/". A "source" object will be created under this
        bucket, and any uploaded artifacts will be stored there.
    ignore_file: string, a path to a gcloudignore file.

  Returns:
    A string in the format "gs://path/to/resulting/upload".

  Raises:
    RequiredArgumentException: if stage-bucket is owned by another project.
    BadFileException: if the source doesn't exist or isn't a directory.
  """
  gcs_client = storage_api.StorageClient()

  # The object name to use for our GCS storage.
  gcs_object_name = 'source'

  if stage_bucket is None:
    used_default_bucket_name = True
    gcs_source_bucket_name = staging_bucket_util.GetDefaultStagingBucket()
    gcs_source_staging_dir = 'gs://{0}/{1}'.format(gcs_source_bucket_name,
                                                   gcs_object_name)
  else:
    used_default_bucket_name = False
    gcs_source_bucket_name = stage_bucket
    gcs_source_staging_dir = stage_bucket + gcs_object_name

  # By calling REGISTRY.Parse on "gs://my-bucket/foo", the result's "bucket"
  # property will be "my-bucket" and the "object" property will be "foo".
  gcs_source_staging_dir_ref = resources.REGISTRY.Parse(
      gcs_source_staging_dir, collection='storage.objects')

  # Make sure the bucket exists
  try:
    gcs_client.CreateBucketIfNotExists(
        gcs_source_staging_dir_ref.bucket,
        check_ownership=used_default_bucket_name)
  except storage_api.BucketInWrongProjectError:
    # If we're using the default bucket but it already exists in a different
    # project, then it could belong to a malicious attacker (b/33046325).
    raise c_exceptions.RequiredArgumentException(
        'stage-bucket', 'A bucket with name {} already exists and is owned by '
        'another project. Specify a bucket using '
        '--stage-bucket.'.format(gcs_source_staging_dir_ref.bucket))

  # This will look something like this:
  # "1615850562.234312-044e784992744951b0cd71c0b011edce"
  staged_object = '{stamp}-{uuid}'.format(
      stamp=times.GetTimeStampFromDateTime(times.Now()),
      uuid=uuid.uuid4().hex,
  )

  if gcs_source_staging_dir_ref.object:
    staged_object = gcs_source_staging_dir_ref.object + '/' + staged_object

  gcs_source_staging = resources.REGISTRY.Create(
      collection='storage.objects',
      bucket=gcs_source_staging_dir_ref.bucket,
      object=staged_object)

  if not os.path.exists(source):
    raise c_exceptions.BadFileException(
        'could not find source [{}]'.format(source))

  if not os.path.isdir(source):
    raise c_exceptions.BadFileException(
        'source is not a directory [{}]'.format(source))

  _UploadSourceDirToGCS(gcs_client, source, gcs_source_staging, ignore_file)

  upload_bucket = 'gs://{0}/{1}'.format(gcs_source_staging.bucket,
                                        gcs_source_staging.object)

  return upload_bucket


def _CreateBlueprint(messages, source, source_git_subdir, stage_bucket,
                     ignore_file):
  """Returns the Blueprint message.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    source: string, a Git repo path.
    source_git_subdir: optional string. If "source" represents a Git repo, then
      this argument represents the directory within that Git repo to use.
    stage_bucket: optional string. When not provided, the default staging bucket
      will be used (see GetDefaultStagingBucket). This string is of the
      format "gs://bucket-name/". A "source" object will be created under this
        bucket, and any uploaded artifacts will be stored there.
    ignore_file: string, a path to a gcloudignore file.

  Returns:
    A messages.Blueprint to use with deployment or preview operation.
  """
  blueprint = messages.Blueprint()

  if source.startswith('gs://'):
    # The source is already in GCS, so just pass it to the API.
    blueprint.gcsSource = source
  elif source.startswith('https://'):
    blueprint.gitSource = git_blueprint_util.GetBlueprintSourceForGit(
        messages, source, source_git_subdir)
  else:
    # The source is local.
    upload_bucket = _UploadSourceToGCS(source, stage_bucket, ignore_file)
    blueprint.gcsSource = upload_bucket

  return blueprint


def _VerifyConfigControllerInstance(config_controller, project, location):
  """Validates the existance and configuration of the provided CC instance.

  Checks that the specified ConfigController instance exists, and has the
  ConfigController bundle enabled.

  Args:
    config_controller: string, the fully qualified name of the config-controller
      instance. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".
    project: string, the project the CC instance must be in.
    location: string, the location the CC instance must be in.

  Raises:
    InvalidArgumentException: if CC instance does not exist, doesn't have the
      CC bundle enabled, or is in the wrong region/project.
  """
  try:
    resp = krmapihosting_util.GetKrmApiHost(config_controller)
  except apitools_exceptions.HttpNotFoundError:
    raise c_exceptions.InvalidArgumentException(
        'config-controller',
        'The KRM API Host instance [{}] does not exist'.format(
            config_controller))
  except apitools_exceptions.HttpForbiddenError:
    # If checking the cluster fails due to denied permissions, continue with
    # deployment anyways, since we shouldn't hard fail on this permission not
    # being set.
    log.warning(
        'Unable to verify that the KRM API Host instance [{}] exists and is '
        'configured correctly due to lack of permissions '
        '(krmapihosting.krmApiHost.get).', config_controller)
    return

  cc_ref = resources.REGISTRY.Parse(
      resp.name, collection='krmapihosting.projects.locations.krmApiHosts')

  location_ref = cc_ref.Parent()
  project_ref = location_ref.Parent()
  if location_ref.Name() != location or project_ref.Name() != project:
    raise c_exceptions.InvalidArgumentException(
        'config-controller',
        'KRM API Host instance [{}] must be in location [{}] '
        'and in project [{}]'.format(config_controller, location, project))

  # If CC isn't enabled or if we can't read the bundleConfig from the response,
  # consider it to be an illegal argument.
  try:
    if not resp.bundlesConfig.configControllerConfig.enabled:
      raise ValueError('configController bundle not enabled')
  except (AttributeError, ValueError):
    raise c_exceptions.InvalidArgumentException(
        'config-controller',
        'KRM API Host instance [{}] does not have the configController bundle '
        'enabled'.format(config_controller))


def _GetOrCreateConfigControllerInstance(config_controller,
                                         deployment_full_name, async_):
  """Gets or creates a Config Controller instance for deployment.

  If no CC instance exists, the user will be prompted to create one.
  If one CC instance exists, that instance will be returned.
  If multiple CC instance exist, the user will be prompted which one to use.

  Args:
    config_controller: optional string. The config_controller flag provided by
      the user, if applicable.
    deployment_full_name: the fully qualified name of the deployment for which
      the CC instance will be used. e.g. "projects/p/locations/l/deployments/d".
    async_: bool, if True, we cannot create a new CC instance, since that would
      require waiting on an LRO before proceeding to mutate the deployment.

  Returns:
    The fully qualified krmApiHost name of the chosen/created instance.

  Raises:
    RequiredArgumentException: If unable to list CC instances.
    InvalidArgumentException: If --async is set along with --config-controller.
  """
  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments')
  location_ref = deployment_ref.Parent()
  project_ref = location_ref.Parent()
  # Get just the ID from the fully qualified name.

  if config_controller:
    # Make sure the ConfigController instance exists
    _VerifyConfigControllerInstance(
        config_controller,
        project=project_ref.Name(),
        location=location_ref.Name())
    return config_controller

  try:
    existing_instances = krmapihosting_util.ListKrmApiHosts(
        location_ref.RelativeName())
  except apitools_exceptions.HttpForbiddenError:
    raise c_exceptions.RequiredArgumentException(
        '--config_controller',
        'Unable to list Config Controller instances (missing '
        '"krmapihosting.krmApiHost.list"). Please specify a Config Controller '
        'instance with --config-controller, or grant yourself the '
        '"krmapihosting.krmApiHost.list" permission.')

  # If there is exactly 1 CC instance, use that one.
  if len(existing_instances) == 1:
    instance_name = existing_instances[0].name
    log.status.Print(
        'Using Config Controller instance [{}] for deployment.'.format(
            instance_name))
    return instance_name

  if async_:
    # If we can't infer a CC instance, and async_ is set, then fail.
    # If `--async` is set, we should not wait on an LRO. Thus, we cannot
    # create a CC instance from gcloud if `--async` is set, because we'd need
    # to wait for that LRO to complete before starting the Deployment
    # operation.
    raise c_exceptions.InvalidArgumentException(
        'config-controller',
        '--config-controller must be set if --async is set')

  # If no CC instance exists, prompt whether to create one.
  if not existing_instances:
    console_io.PromptContinue(
        message='No Config Controller instances were found in this project and '
        'region. Blueprints Controller requires a pre-existing Config '
        'Controller instance to deploy configurations to.',
        prompt_string='Would you like to create one? (This may take up to 20 '
        'minutes)',
        cancel_on_no=True)
    return _CreateConfigControllerInstance(location_ref.RelativeName())

  # If multiple CC instances exist, prompt for which one to use (or create)
  # a new one.
  choices = [instance.name for instance in existing_instances
            ] + ['Create a new Config Controller instance']
  index = console_io.PromptChoice(
      options=choices,
      message='Please choose which Config Controller instance to deploy to:\n')
  # If prompting is disabled, the return value is `None`. In this case, require
  # the user to explicitly provide a CC instance.
  if index is None:
    raise c_exceptions.RequiredArgumentException(
        'config-controller',
        'Please specify a Config Controller instance to deploy to with '
        '--config-controller.')
  elif index == len(choices) - 1:
    return _CreateConfigControllerInstance(location_ref.RelativeName())
  return existing_instances[index].name


def _RandomConfigControllerInstanceName():
  suffix = ''.join(
      random.choice(string.ascii_lowercase + string.digits)
      for _ in range(_KRMAPIHOSTING_INSTANCE_SUFFIX_LENGTH))
  return _DEFAULT_KRMAPIHOSTING_INSTANCE_PREFIX + suffix


def _CreateConfigControllerInstance(location_full_name):
  """Creates a Config Controller instance in the specified location.

  Args:
    location_full_name: string, the fully qualified name of the location in
      which to create the instance, e.g. "projects/p/locations/l".

  Returns:
    The fully qualified krmApiHost name of the created instance.
  """
  messages = krmapihosting_util.GetMessagesModule()
  krm_api_host = messages.KrmApiHost(
      bundlesConfig=messages.BundlesConfig(
          configControllerConfig=messages.ConfigControllerConfig(enabled=True)),
      managementConfig=messages.ManagementConfig(
          standardManagementConfig=messages.StandardManagementConfig(
              masterIpv4CidrBlock=_DEFAULT_KRMAPIHOSTING_MASTER_CIDR_BLOCK)))
  op = krmapihosting_util.CreateKrmApiHost(
      parent=location_full_name,
      krm_api_host_id=_RandomConfigControllerInstanceName(),
      krm_api_host=krm_api_host)
  log.debug('Config Controller Cluster Creation LRO: %s', op.name)
  cluster_name = krmapihosting_util.WaitForCreateKrmApiHostOperation(
      op,
      progress_message='Waiting for instance to create (this can take up to 20 minutes)',
      max_wait_ms=_MAX_WAIT_TIME_MS).name

  log.status.Print(
      textwrap.dedent('''\
          To use this as the default instance for future Deployments, run:

            $ gcloud config set blueprints/config_controller {0}

          Or set "--config-controller={0}"'''.format(cluster_name)) + '\n')
  return cluster_name


def Apply(source,
          deployment_full_name,
          stage_bucket,
          labels,
          messages,
          ignore_file,
          async_,
          reconcile_timeout,
          source_git_subdir='.',
          config_controller=None,
          target_git=None,
          target_git_subdir=None,
          clusterless=True):
  """Updates the deployment if one exists, otherwise one will be created.

  Bundles parameters for creating/updating a deployment.

  Args:
    source: string, either a local path, a GCS bucket, or a Git repo.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    stage_bucket: an optional string. When not provided, the default staging
      bucket will be used. This is of the format "gs://bucket-name/".
    labels: dictionary of string → string, labels to be associated with the
      deployment.
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    ignore_file: optional string, a path to a gcloudignore file.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    reconcile_timeout: timeout in seconds. If the blueprint apply step takes
      longer than this timeout, the deployment will fail. 0 implies no timeout.
    source_git_subdir: optional string. If "source" represents a Git repo, then
      this argument represents the directory within that Git repo to use.
    config_controller: optional string, the fully qualified name of the
      config-controller instance to use. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".
    target_git: optional string, a Git repo to use as a deployment target.
    target_git_subdir: optional string. Represents the directory within the
      target Git repo to use.
    clusterless: optional bool, defaulted to True. If True, then clusterless
      actuation is used, otherwise clusterful actuation is used.

  Returns:
    The resulting Deployment resource or, in the case that async_ is True, a
      long-running operation.

  Raises:
    InvalidArgumentException: If an invalid set of flags is provided (e.g.
      trying to run with --target-git-subdir but without --target-git).
  """

  if target_git_subdir and not target_git:
    raise c_exceptions.InvalidArgumentException(
        'target-git-subdir',
        '--target-git-subdir cannot be set if --target-git is not set')

  blueprint = _CreateBlueprint(messages, source, source_git_subdir,
                               stage_bucket, ignore_file)

  labels_message = {}
  # Whichever labels the user provides will become the full set of labels in the
  # resulting deployment.
  if labels is not None:
    labels_message = messages.Deployment.LabelsValue(additionalProperties=[
        messages.Deployment.LabelsValue.AdditionalProperty(
            key=key, value=value) for key, value in six.iteritems(labels)
    ])

  deployment = messages.Deployment(
      blueprint=blueprint,
      labels=labels_message,
      reconcileTimeout=six.text_type(reconcile_timeout) + 's',
  )

  # Check if a deployment with the given name already exists. If it does, we'll
  # update that deployment. If not, we'll create it.
  try:
    existing_deployment = blueprints_util.GetDeployment(deployment_full_name)
  except apitools_exceptions.HttpNotFoundError:
    existing_deployment = None

  is_creating_deployment = existing_deployment is None
  op = None

  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments')
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  git_target = git_blueprint_util.GetBlueprintTargetForGit(
      messages, target_git, target_git_subdir) if target_git else None

  if clusterless and (git_target or config_controller):
    raise c_exceptions.InvalidArgumentException(
        'clusterless',
        '--target-git and --config-controller cannot be set if '
        'deployment is meant to be clusterless'
    )

  if is_creating_deployment:
    op = _CreateDeploymentOp(deployment, deployment_full_name,
                             config_controller, git_target, async_, clusterless)
  else:
    op = _UpdateDeploymentOp(deployment, existing_deployment,
                             deployment_full_name, config_controller,
                             git_target, labels, clusterless)

  log.debug('LRO: %s', op.name)

  # If the user chose to run asynchronously, then we'll match the output that
  # the automatically-generated Delete command issues and return immediately.
  if async_:
    log.status.Print('{0} request issued for: [{1}]'.format(
        'Create' if is_creating_deployment else 'Update', deployment_id))

    log.status.Print('Check operation [{}] for status.'.format(op.name))

    return op

  progress_message = '{} the deployment'.format(
      'Creating' if is_creating_deployment else 'Updating')

  applied_deployment = blueprints_util.WaitForApplyDeploymentOperation(
      op, progress_message)

  if applied_deployment.state == messages.Deployment.StateValueValuesEnum.FAILED:
    error_handling.DeploymentFailed(applied_deployment)
  elif _ShouldPrintKptApplyResults(messages, applied_deployment):
    revision_ref = blueprints_util.GetRevision(
        applied_deployment.latestRevision)
    error_handling.PrintKptApplyResultsError(
        revision_ref.applyResults.artifacts)

  return applied_deployment


def _ShouldPrintKptApplyResults(messages, deployment):
  """Returns if kpt apply results should be printed for the deployment.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    deployment: messages.Deployment. The applied deployment.

  Returns:
    bool. Whether gcloud should fetch kpt apply results and print them.
  """
  # If the deployment performed actions, succeeded without a timeout defined,
  # and has a latest revision, then we should fetch that revision and print its
  # apply results.
  return (_DeploymentPerformsActuation(deployment) and deployment.state
          == messages.Deployment.StateValueValuesEnum.ACTIVE and
          deployment.latestRevision and not deployment.reconcileTimeout)


def _DeploymentPerformsActuation(deployment):
  """Returns whether the deployment performs actuation.

  Args:
    deployment: messages.Deployment. The applied deployment.

  Returns:
    bool. Whether the deployment performs actuation as part of applying it.
  """
  # Currently, deployments perform actuation unless they target a Git repo.
  return deployment.gitTarget is None


def _CreateDeploymentOp(deployment, deployment_full_name, config_controller,
                        git_target, async_, clusterless):
  """Initiates and returns a CreateDeployment operation.

  Args:
    deployment: A partially filled messages.Deployment. The deployment will be
      filled with its target (e.g. configController, gitTarget, etc.) before the
      operation is initiated.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    config_controller: optional string, the fully qualified name of the
      config-controller instance to use. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".
    git_target: optional messages.GitTarget. The Git target for the deployment.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    clusterless: bool, if True, deployment is done without a cluster, otherwise
      deployment uses a config-controller instance.

  Returns:
    The CreateDeployment operation.

  Raises:
    InvalidArgumentException: If an invalid set of flags is provided (e.g.
      trying to run with --async but without a target), or if a
      target is set with clusterless being True.
  """
  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments')
  location_ref = deployment_ref.Parent()
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  # TODO(b/202192430): This logic assumes --config-controller is the "default"
  # target, which is correct for now, since --git-target is hidden. However,
  # if we decide to consolidate these into a single --target flag (or
  # --target-git is becomes unhidden), then some of these error messages will
  # need to be reworked.
  if clusterless:
    deployment.clusterless = clusterless
  elif git_target:
    deployment.gitTarget = git_target
  else:
    deployment.configController = _GetOrCreateConfigControllerInstance(
        config_controller, deployment_full_name, async_)

  log.info('Creating the deployment')
  return blueprints_util.CreateDeployment(deployment, deployment_id,
                                          location_ref.RelativeName())


def _UpdateDeploymentOp(deployment, existing_deployment, deployment_full_name,
                        config_controller, git_target, labels, clusterless):
  """Initiates and returns an UpdateDeployment operation.

  Args:
    deployment: A partially filled messages.Deployment. The deployment will be
      filled with its target (e.g. configController, gitTarget, etc.) before the
      operation is initiated.
    existing_deployment: A messages.Deployment. The existing deployment to
      update.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    config_controller: optional string, the fully qualified name of the
      config-controller instance to use. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".
    git_target: optional messages.GitTarget. The Git target for the deployment.
    labels: dictionary of string → string, labels to be associated with the
      deployment.
    clusterless: bool, if True, deployment is clusterless, otherwise it is
      clusterfull.

  Returns:
    The UpdateDeployment operation.

  Raises:
    InvalidArgumentException: If the user tries to update a field that cannot be
    updated.
  """
  if clusterless and (config_controller or git_target):
    msg = '--clusterless cannot be True if there is a target set'
    if not existing_deployment.clusterless:
      msg = ('--clusterless cannot be True if the existing deployment is not '
             'clusterless')
      raise c_exceptions.InvalidArgumentException('clusterless', msg)

  if (config_controller is not None and
      config_controller != existing_deployment.configController):
    msg = '--config-controller cannot be updated for an existing deployment'
    if existing_deployment.configController:
      msg = ('--config-controller for the existing deployment is "{}", and '
             'cannot be updated.'.format(existing_deployment.configController))
    raise c_exceptions.InvalidArgumentException('config-controller', msg)

  if git_target != existing_deployment.gitTarget:
    raise c_exceptions.InvalidArgumentException(
        '--target-git',
        '--target-git and --target-git-subdir cannot be updated for an '
        'existing deployment')

  log.info('Updating the existing deployment')

  # If the user didn't specify labels here, then we don't want to overwrite
  # the existing labels on the deployment, so we provide them back to the
  # underlying API.
  if labels is None:
    deployment.labels = existing_deployment.labels

  return blueprints_util.UpdateDeployment(deployment, deployment_full_name)


def PreviewApply(source,
                 deployment_full_name,
                 stage_bucket,
                 messages,
                 location,
                 ignore_file,
                 source_git_subdir='.',
                 preview_format=_PREVIEW_FORMAT_TEXT,
                 config_controller=None):
  """Executes preview of a deployment.

  Bundles parameters for creating/updating a deployment.

  Args:
    source: string, either a local path, a GCS bucket, or a Git repo.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    stage_bucket: an optional string. When not provided, the default staging
      bucket will be used. This is of the format "gs://bucket-name/".
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    location: string, a region like "us-central1".
    ignore_file: optional string, a path to a gcloudignore file.
    source_git_subdir: optional string. If "source" represents a Git repo, then
      this argument represents the directory within that Git repo to use.
    preview_format: output format for preview results. Either "text" or "json".
    config_controller: optional string, the fully qualified name of the
      config-controller instance to use. Only valid for previewing without an
      existing deployment. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".

  Returns:
    Returns a messages.Preview that contains preview results.
  """
  location_ref = resources.REGISTRY.Create(
      collection='config.projects.locations',
      projectsId=properties.VALUES.core.project.GetOrFail(),
      locationsId=location)

  blueprint = _CreateBlueprint(messages, source, source_git_subdir,
                               stage_bucket, ignore_file)

  # Check if a deployment with the given name already exists. If it does, we'll
  # update that deployment. If not, we'll create it.
  try:
    existing_deployment = blueprints_util.GetDeployment(deployment_full_name)
  except apitools_exceptions.HttpNotFoundError:
    existing_deployment = None

  is_creating_deployment = existing_deployment is None

  preview = messages.Preview(
      applyInput=messages.ApplyInput(
          blueprint=blueprint,
          deployment='' if is_creating_deployment else deployment_full_name))

  if is_creating_deployment:
    preview.applyInput.configController = _GetOrCreateConfigControllerInstance(
        config_controller, deployment_full_name, async_=False)
  # This just allows --config-controller to be set as a 'passthrough' as long
  # as it matches the value on the existing deployment. The value of the flag
  # is not used.
  elif config_controller != existing_deployment.configController:
    msg = ('--config-controller cannot differ from existing Deployment when '
           'previewing an update.')
    if existing_deployment.configController:
      msg += ' Existing deployment has config_controller: [{}].'.format(
          existing_deployment.configController)
    raise c_exceptions.InvalidArgumentException('config-controller', msg)
  op = blueprints_util.CreatePreview(preview, location_ref.RelativeName())

  log.debug('LRO: %s', op.name)

  preview_result = blueprints_util.WaitForApplyPreviewOperation(op)

  _PrintPreview(messages, preview_result, preview_format)

  return preview_result


def _PrintPreview(messages,
                  preview_result,
                  preview_format=_PREVIEW_FORMAT_TEXT):
  """Prints preview results.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    preview_result: a messages.Preview resource.
    preview_format: a string that specifies the output format for printing.
  """
  if preview_result.state == messages.Preview.StateValueValuesEnum.COMPLETED:
    gcs_path = preview_result.previewResults.artifacts
    if preview_format == _PREVIEW_FORMAT_TEXT:
      _FetchAndPrintPreviewResults(gcs_path)
    elif preview_format == _PREVIEW_FORMAT_JSON:
      _FetchAndPrintPreviewResultsJSON(gcs_path)
    log.status.Print('Preview results are available at {0}'.format(gcs_path))
  elif preview_result.state == messages.Preview.StateValueValuesEnum.FAILED:
    error_handling.PreviewFailed(preview_result)


def _FetchAndPrintPreviewResults(gcs_path):
  """Fetches from GCS and prints preview results.

  Args:
    gcs_path: string, the full Cloud Storage path to the folder containing
      preview results files.
  """
  results_path = '{0}/result.json'.format(gcs_path)
  results_content = error_handling.GetTextFileContentsFromStorageBucket(
      results_path)

  try:
    results_data = json.loads(results_content)
  except ValueError as e:
    log.debug('Unable to parse preview results JSON: {}'.format(e))
    log.status.Print('Failed to parse preview results.')
    return

  summary = results_data.get('Summary')
  details = results_data.get('Details')
  log.status.Print('{0}'.format(details))
  log.status.Print('{0}'.format(summary))


def _FetchAndPrintPreviewResultsJSON(gcs_path):
  """Fetches from GCS and prints preview verbose JSON results.

  Args:
    gcs_path: string, the full Cloud Storage path to the folder containing
      preview results files.
  """
  results_path = '{0}/verbose.json'.format(gcs_path)
  results_content = error_handling.GetTextFileContentsFromStorageBucket(
      results_path)
  log.status.Print('{0}'.format(results_content))


def PreviewDelete(deployment_full_name,
                  messages,
                  location,
                  preview_format=_PREVIEW_FORMAT_TEXT,
                  config_controller=None):
  """Execute preview of delete operation of an existing deployment.

  Args:
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    location: string, a region like "us-central1".
    preview_format: output format for preview results. Either "text" or "json".
    config_controller: optional string, the fully qualified name of a
      config-controller instance. This is not actually _used_ in the request,
      but is allowed so that users can "pass through" the existing value, for
      convenience. e.g.
      "projects/{project}/locations/{location}/krmApiHosts/{instance}".

  Returns:
    Returns a messages.Preview that contains preview results.
  """
  parent_resource = resources.REGISTRY.Create(
      collection='config.projects.locations',
      projectsId=properties.VALUES.core.project.GetOrFail(),
      locationsId=location)

  # Check if a deployment with the given name exists.
  try:
    existing_deployment = blueprints_util.GetDeployment(deployment_full_name)
  except apitools_exceptions.HttpNotFoundError:
    existing_deployment = None

  if existing_deployment is None:
    log.status.Print(
        'Specified deployment does not exist: {0}'.format(deployment_full_name))
    return

  # This just allows --config-controller to be set as a 'passthrough' as long
  # as it matches the value on the existing deployment. The value of the flag
  # is not used.
  if (config_controller is not None and
      config_controller != existing_deployment.configController):
    msg = ('--config-controller cannot differ from existing Deployment when '
           'previewing a deletion.')
    if existing_deployment.configController:
      msg += ' Existing deployment has config_controller: [{}].'.format(
          existing_deployment.configController)
    raise c_exceptions.InvalidArgumentException('config-controller', msg)

  preview = messages.Preview(
      deleteInput=messages.DeleteInput(deployment=deployment_full_name))
  op = blueprints_util.CreatePreview(preview, parent_resource.RelativeName())

  log.debug('LRO: %s', op.name)

  preview_result = blueprints_util.WaitForDeletePreviewOperation(op)

  _PrintPreview(messages, preview_result, preview_format)

  return preview_result
