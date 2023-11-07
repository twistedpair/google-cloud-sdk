# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Support library for managing deployments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import sys
import uuid

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import extra_types
from googlecloudsdk.api_lib.infra_manager import configmanager_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.infra_manager import deterministic_snapshot
from googlecloudsdk.command_lib.infra_manager import errors
from googlecloudsdk.command_lib.infra_manager import staging_bucket_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import times
import six


if sys.version_info >= (3, 6):
  # pylint: disable=g-import-not-at-top
  from googlecloudsdk.command_lib.infra_manager import tfvars_parser


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
      source, ignore_file=ignore_file
  )

  size_str = resource_transform.TransformSize(source_snapshot.uncompressed_size)
  log.status.Print(
      'Uploading {num_files} file(s) totalling {size}.'.format(
          num_files=len(source_snapshot.files), size=size_str
      )
  )

  for file_metadata in source_snapshot.GetSortedFiles():
    full_local_path = os.path.join(file_metadata.root, file_metadata.path)

    target_obj_ref = 'gs://{0}/{1}/{2}'.format(
        gcs_source_staging.bucket, gcs_source_staging.object, file_metadata.path
    )
    target_obj_ref = resources.REGISTRY.Parse(
        target_obj_ref, collection='storage.objects'
    )

    gcs_client.CopyFileToGCS(full_local_path, target_obj_ref)


def _UploadSourceToGCS(
    source, stage_bucket, deployment_short_name, location, ignore_file
):
  """Uploads local content to GCS.

  This will ensure that the source and destination exist before triggering the
  upload.

  Args:
    source: string, a local path.
    stage_bucket: optional string. When not provided, the default staging bucket
      will be used (see GetDefaultStagingBucket). This string is of the format
      "gs://bucket-name/". An "im_source_staging" object will be created under
      this bucket, and any uploaded artifacts will be stored there.
    deployment_short_name: short name of the deployment.
    location: location of the deployment.
    ignore_file: string, a path to a gcloudignore file.

  Returns:
    A string in the format "gs://path/to/resulting/upload".

  Raises:
    RequiredArgumentException: if stage-bucket is owned by another project.
    BadFileException: if the source doesn't exist or isn't a directory.
  """
  gcs_client = storage_api.StorageClient()

  if stage_bucket is None:
    used_default_bucket_name = True
    gcs_source_staging_dir = staging_bucket_util.DefaultGCSStagingDir(
        deployment_short_name, location
    )
  else:
    used_default_bucket_name = False
    gcs_source_staging_dir = '{0}{1}/{2}/{3}'.format(
        stage_bucket,
        staging_bucket_util.STAGING_DIR,
        location,
        deployment_short_name,
    )

  # By calling REGISTRY.Parse on "gs://my-bucket/foo", the result's "bucket"
  # property will be "my-bucket" and the "object" property will be "foo".
  gcs_source_staging_dir_ref = resources.REGISTRY.Parse(
      gcs_source_staging_dir, collection='storage.objects'
  )

  # Make sure the bucket exists
  try:
    gcs_client.CreateBucketIfNotExists(
        gcs_source_staging_dir_ref.bucket,
        check_ownership=used_default_bucket_name,
    )
  except storage_api.BucketInWrongProjectError:
    raise c_exceptions.RequiredArgumentException(
        'stage-bucket',
        'A bucket with name {} already exists and is owned by '
        'another project. Specify a bucket using '
        '--stage-bucket.'.format(gcs_source_staging_dir_ref.bucket),
    )

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
      object=staged_object,
  )

  if not os.path.exists(source):
    raise c_exceptions.BadFileException(
        'could not find source [{}]'.format(source)
    )

  if not os.path.isdir(source):
    raise c_exceptions.BadFileException(
        'source is not a directory [{}]'.format(source)
    )

  _UploadSourceDirToGCS(gcs_client, source, gcs_source_staging, ignore_file)

  upload_bucket = 'gs://{0}/{1}'.format(
      gcs_source_staging.bucket, gcs_source_staging.object
  )

  return upload_bucket


def UpdateDeploymentDeleteRequestWithForce(unused_ref, unused_args, request):
  """UpdateDeploymentDeleteRequestWithForce adds force flag to delete request."""

  request.force = True
  return request


def DeploymentDeleteCleanupStagedObjects(response, unused_args):
  """DeploymentDeleteCleanupStagedObjects deletes staging gcs objects created as part of deployment apply command."""

  # do not delete staged objects if delete results in error
  if response.error is not None:
    return

  if response.metadata is not None:
    md = encoding.MessageToPyValue(response.metadata)
    deployment_full_name = md['target']
    deployment_id = deployment_full_name.split('/')[5]
    location = deployment_full_name.split('/')[3]
    staging_gcs_directory = staging_bucket_util.DefaultGCSStagingDir(
        deployment_id, location
    )
    gcs_client = storage_api.StorageClient()
    staging_bucket_util.DeleteStagingGCSFolder(
        gcs_client, staging_gcs_directory
    )

  return response


def _CreateTFBlueprint(
    messages,
    deployment_short_name,
    location,
    local_source,
    stage_bucket,
    ignore_file,
    gcs_source,
    git_source_repo,
    git_source_directory,
    git_source_ref,
    input_values,
):
  """Returns the TerraformBlueprint message.

  Args:
    messages: ModuleType, the messages module that lets us form Config API
      messages based on our protos.
    deployment_short_name: short name of the deployment.
    location: location of the deployment.
    local_source: Local storage path where config files are stored.
    stage_bucket: optional string. Destination for storing local config files
      specified by local source flag. e.g. "gs://bucket-name/".
    ignore_file: optional string, a path to a gcloudignore file.
    gcs_source:  URI of an object in Google Cloud Storage. e.g.
      `gs://{bucket}/{object}`
    git_source_repo: Repository URL.
    git_source_directory: Subdirectory inside the git repository.
    git_source_ref: Git branch or tag.
    input_values: Input variable values for the Terraform blueprint. It only
      accepts (key, value) pairs where value is a scalar value.

  Returns:
    A messages.TerraformBlueprint to use with deployment operation.
  """

  terraform_blueprint = messages.TerraformBlueprint(
      inputValues=input_values,
  )

  if gcs_source is not None:
    terraform_blueprint.gcsSource = gcs_source
  elif local_source is not None:
    upload_bucket = _UploadSourceToGCS(
        local_source, stage_bucket, deployment_short_name, location, ignore_file
    )
    terraform_blueprint.gcsSource = upload_bucket
  else:
    terraform_blueprint.gitSource = messages.GitSource(
        repo=git_source_repo,
        directory=git_source_directory,
        ref=git_source_ref,
    )

  return terraform_blueprint


def Apply(
    messages,
    async_,
    deployment_full_name,
    service_account,
    local_source=None,
    stage_bucket=None,
    ignore_file=None,
    import_existing_resources=False,
    artifacts_gcs_bucket=None,
    worker_pool=None,
    gcs_source=None,
    git_source_repo=None,
    git_source_directory=None,
    git_source_ref=None,
    input_values=None,
    inputs_file=None,
    labels=None,
):
  """Updates the deployment if one exists, otherwise creates a deployment.

  Args:
    messages: ModuleType, the messages module that lets us form blueprints API
      messages based on our protos.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    service_account: User-specified Service Account (SA) to be used as
      credential to manage resources. e.g.
      `projects/{projectID}/serviceAccounts/{serviceAccount}` The default Cloud
      Build SA will be used initially if this field is not set.
    local_source: Local storage path where config files are stored.
    stage_bucket: optional string. Destination for storing local config files
      specified by local source flag. e.g. "gs://bucket-name/".
    ignore_file: optional string, a path to a gcloudignore file.
    import_existing_resources: By default, Infrastructure Manager will return a
      failure when Terraform encounters a 409 code (resource conflict error)
      during actuation. If this flag is set to true, Infrastructure Manager will
      instead attempt to automatically import the resource into the Terraform
      state (for supported resource types) and continue actuation.
    artifacts_gcs_bucket: User-defined location of Cloud Build logs, artifacts,
      and Terraform state files in Google Cloud Storage. e.g.
      `gs://{bucket}/{folder}` A default bucket will be bootstrapped if the
      field is not set or empty
    worker_pool: The User-specified Worker Pool resource in which the Cloud
      Build job will execute. If this field is unspecified, the default Cloud
      Build worker pool will be used. e.g.
      projects/{project}/locations/{location}/workerPools/{workerPoolId}
    gcs_source:  URI of an object in Google Cloud Storage. e.g.
      `gs://{bucket}/{object}`
    git_source_repo: Repository URL.
    git_source_directory: Subdirectory inside the git repository.
    git_source_ref: Git branch or tag.
    input_values: Input variable values for the Terraform blueprint. It only
      accepts (key, value) pairs where value is a scalar value.
    inputs_file: Accepts .tfvars file.
    labels: User-defined metadata for the deployment.

  Returns:
    The resulting Deployment resource or, in the case that async_ is True, a
      long-running operation.

  Raises:
    InvalidArgumentException: If an invalid set of flags is provided (e.g.
      trying to run with --target-git-subdir but without --target-git).
  """

  labels_message = {}
  # Whichever labels the user provides will become the full set of labels in the
  # resulting deployment.
  if labels is not None:
    labels_message = messages.Deployment.LabelsValue(
        additionalProperties=[
            messages.Deployment.LabelsValue.AdditionalProperty(
                key=key, value=value
            )
            for key, value in six.iteritems(labels)
        ]
    )

  additional_properties = []
  if input_values is not None:
    for key, value in six.iteritems(input_values):
      additional_properties.append(
          messages.TerraformBlueprint.InputValuesValue.AdditionalProperty(
              key=key,
              value=messages.TerraformVariable(
                  inputValue=encoding.PyValueToMessage(
                      extra_types.JsonValue, value
                  )
              ),
          )
      )
  elif inputs_file is not None:
    if sys.version_info < (3, 6):
      raise errors.InvalidDataError(
          '--inputs-file flag is only supported for python version 3.6 and'
          ' above.'
      )
    tfvar_values = tfvars_parser.ParseTFvarFile(inputs_file)
    for key, value in six.iteritems(tfvar_values):
      additional_properties.append(
          messages.TerraformBlueprint.InputValuesValue.AdditionalProperty(
              key=key,
              value=messages.TerraformVariable(
                  inputValue=encoding.PyValueToMessage(
                      extra_types.JsonValue, value
                  )
              ),
          )
      )

  tf_input_values = messages.TerraformBlueprint.InputValuesValue(
      additionalProperties=additional_properties
  )

  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments'
  )
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  location = deployment_ref.Parent().Name()

  # Check if a deployment with the given name already exists. If it does, we'll
  # update that deployment. If not, we'll create it.
  try:
    existing_deployment = configmanager_util.GetDeployment(deployment_full_name)
  except apitools_exceptions.HttpNotFoundError:
    existing_deployment = None

  if existing_deployment is not None:
    # cleanup objects before uploading any new staging object
    _CleanupGCSStagingObjectsNotInUse(
        location, deployment_full_name, deployment_id
    )

  tf_blueprint = _CreateTFBlueprint(
      messages,
      deployment_id,
      location,
      local_source,
      stage_bucket,
      ignore_file,
      gcs_source,
      git_source_repo,
      git_source_directory,
      git_source_ref,
      tf_input_values,
  )

  deployment = messages.Deployment(
      name=deployment_full_name,
      serviceAccount=service_account,
      importExistingResources=import_existing_resources,
      workerPool=worker_pool,
      terraformBlueprint=tf_blueprint,
      labels=labels_message,
  )

  if artifacts_gcs_bucket is not None:
    deployment.artifactsGcsBucket = artifacts_gcs_bucket

  is_creating_deployment = existing_deployment is None
  op = None

  if is_creating_deployment:
    op = _CreateDeploymentOp(deployment, deployment_full_name)
  else:
    op = _UpdateDeploymentOp(
        deployment, existing_deployment, deployment_full_name, labels
    )

  log.debug('LRO: %s', op.name)

  # If the user chose to run asynchronously, then we'll match the output that
  # the automatically-generated Delete command issues and return immediately.
  if async_:
    log.status.Print(
        '{0} request issued for: [{1}]'.format(
            'Create' if is_creating_deployment else 'Update', deployment_id
        )
    )

    log.status.Print('Check operation [{}] for status.'.format(op.name))

    return op

  progress_message = '{} the deployment'.format(
      'Creating' if is_creating_deployment else 'Updating'
  )

  applied_deployment = configmanager_util.WaitForApplyDeploymentOperation(
      op, progress_message
  )

  if (
      applied_deployment.state
      == messages.Deployment.StateValueValuesEnum.FAILED
  ):
    raise errors.OperationFailedError(applied_deployment.stateDetail)

  return applied_deployment


def _CreateDeploymentOp(
    deployment,
    deployment_full_name,
):
  """Initiates and returns a CreateDeployment operation.

  Args:
    deployment: A partially filled messages.Deployment. The deployment will be
      filled with other details before the operation is initiated.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".

  Returns:
    The CreateDeployment operation.
  """
  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments'
  )
  location_ref = deployment_ref.Parent()
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  log.info('Creating the deployment')
  return configmanager_util.CreateDeployment(
      deployment, deployment_id, location_ref.RelativeName()
  )


def _UpdateDeploymentOp(
    deployment,
    existing_deployment,
    deployment_full_name,
    labels,
):
  """Initiates and returns an UpdateDeployment operation.

  Args:
    deployment: A partially filled messages.Deployment. The deployment will be
      filled with its target (e.g. configController, gitTarget, etc.) before the
      operation is initiated.
    existing_deployment: A messages.Deployment. The existing deployment to
      update.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    labels: dictionary of string → string, labels to be associated with the
      deployment.

  Returns:
    The UpdateDeployment operation.
  """

  log.info('Updating the existing deployment')

  # If the user didn't specify labels here, then we don't want to overwrite
  # the existing labels on the deployment, so we provide them back to the
  # underlying API.
  if labels is None:
    deployment.labels = existing_deployment.labels

  return configmanager_util.UpdateDeployment(deployment, deployment_full_name)


def ImportStateFile(messages, deployment_full_name, lock_id):
  """Creates a signed uri to upload the state file.

  Args:
    messages: ModuleType, the messages module that lets us form Infra Manager
      API messages based on our protos.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    lock_id: Lock ID of the lock file to verify person importing owns lock.

  Returns:
    A messages.StateFile which contains signed uri to be used to upload a state
    file.
  """

  import_state_file_request = messages.ImportStatefileRequest(
      lockId=int(lock_id),
  )

  log.status.Print('Creating signed uri for ImportStatefile request...')

  state_file = configmanager_util.ImportStateFile(
      import_state_file_request, deployment_full_name
  )

  return state_file


def ExportDeploymentStateFile(messages, deployment_full_name, draft=False):
  """Creates a signed uri to download the state file.

  Args:
    messages: ModuleType, the messages module that lets us form Infra Manager
      API messages based on our protos.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    draft: Lock ID of the lock file to verify person importing owns lock.

  Returns:
    A messages.StateFile which contains signed uri to be used to upload a state
    file.
  """

  export_deployment_state_file_request = (
      messages.ExportDeploymentStatefileRequest(
          draft=draft,
      )
  )

  log.status.Print('Initiating export state file request...')

  state_file = configmanager_util.ExportDeploymentStateFile(
      export_deployment_state_file_request, deployment_full_name
  )

  return state_file


def ExportRevisionStateFile(messages, deployment_full_name):
  """Creates a signed uri to download the state file.

  Args:
    messages: ModuleType, the messages module that lets us form Infra Manager
      API messages based on our protos.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".

  Returns:
    A messages.StateFile which contains signed uri to be used to upload a state
    file.
  """

  export_revision_state_file_request = messages.ExportRevisionStatefileRequest()

  log.status.Print('Initiating export state file request...')

  state_file = configmanager_util.ExportRevisionStateFile(
      export_revision_state_file_request, deployment_full_name
  )

  return state_file


def ExportLock(deployment_full_name):
  """Exports lock info of the deployment.

  Args:
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".

  Returns:
    A lock info response.
  """

  log.status.Print('Initiating export lock request...')

  lock_info = configmanager_util.ExportLock(
      deployment_full_name,
  )

  return lock_info


def LockDeployment(messages, async_, deployment_full_name):
  """Locks the deployment.

  Args:
    messages: ModuleType, the messages module that lets us form Infra Manager
      API messages based on our protos.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".

  Returns:
    A lock info resource or, in case async_ is True, a
      long-running operation.
  """

  lock_deployment_request = messages.LockDeploymentRequest()

  op = configmanager_util.LockDeployment(
      lock_deployment_request, deployment_full_name
  )

  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments'
  )
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  log.debug('LRO: %s', op.name)

  if async_:
    log.status.Print(
        'Lock deployment request issued for: [{0}]'.format(deployment_id)
    )

    log.status.Print('Check operation [{}] for status.'.format(op.name))
    return op

  progress_message = 'Locking the deployment'

  lock_response = configmanager_util.WaitForApplyDeploymentOperation(
      op, progress_message
  )

  if (
      lock_response.lockState
      == messages.Deployment.LockStateValueValuesEnum.LOCK_FAILED
  ):
    raise errors.OperationFailedError('Lock deployment operation failed.')

  return ExportLock(deployment_full_name)


def UnlockDeployment(
    messages,
    async_,
    deployment_full_name,
    lock_id,
):
  """Unlocks the deployment.

  Args:
    messages: ModuleType, the messages module that lets us form Infra Manager
      API messages based on our protos.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    lock_id: Lock ID of the deployment to be unlocked.

  Returns:
    A deployment resource or, in case async_ is True, a
      long-running operation.
  """

  unlock_deployment_request = messages.UnlockDeploymentRequest(
      lockId=int(lock_id),
  )

  deployment_ref = resources.REGISTRY.Parse(
      deployment_full_name, collection='config.projects.locations.deployments'
  )
  # Get just the ID from the fully qualified name.
  deployment_id = deployment_ref.Name()

  op = configmanager_util.UnlockDeployment(
      unlock_deployment_request, deployment_full_name
  )

  log.debug('LRO: %s', op.name)

  if async_:
    log.status.Print(
        'Unlock deployment request issued for: [{0}]'.format(deployment_id)
    )

    log.status.Print('Check operation [{}] for status.'.format(op.name))

    return op

  progress_message = 'Unlocking the deployment'

  unlock_response = configmanager_util.WaitForApplyDeploymentOperation(
      op, progress_message
  )

  if (
      unlock_response.lockState
      == messages.Deployment.LockStateValueValuesEnum.UNLOCK_FAILED
  ):
    raise errors.OperationFailedError('Unlock deployment operation failed.')

  return unlock_response


def _CleanupGCSStagingObjectsNotInUse(
    location, deployment_full_name, deployment_id
):
  """Deletes staging object for all revisions except for last successful revision.

  Args:
    location: The location of deployment.
    deployment_full_name: string, the fully qualified name of the deployment,
      e.g. "projects/p/locations/l/deployments/d".
    deployment_id: the short name of the deployment.

  Raises:
    NotFoundError: If the bucket or folder does not exist.
  """

  gcs_client = storage_api.StorageClient()
  gcs_staging_dir = staging_bucket_util.DefaultGCSStagingDir(
      deployment_id, location
  )
  gcs_staging_dir_ref = resources.REGISTRY.Parse(
      gcs_staging_dir, collection='storage.objects'
  )
  bucket_ref = storage_util.BucketReference(gcs_staging_dir_ref.bucket)

  items = []
  try:
    items = gcs_client.ListBucket(bucket_ref, gcs_staging_dir_ref.object)
  except storage_api.BucketNotFoundError:
    # if staging bucket does not exist, do nothing
    pass

  staged_objects = set()
  items_found = False
  for item in items:
    items_found = True
    item_dir = '/'.join(item.name.split('/')[:4])
    staged_objects.add(
        'gs://{0}/{1}'.format(gcs_staging_dir_ref.bucket, item_dir)
    )
  if not items_found:
    return
  op = configmanager_util.ListRevisions(deployment_full_name)
  revisions = sorted(
      op.revisions, key=lambda x: GetRevisionNumber(x.name), reverse=True
  )

  # discard gcsSource in latest revision from being deleted
  lastest_revision = revisions[0]
  if lastest_revision.terraformBlueprint is not None:
    staged_objects.discard(lastest_revision.terraformBlueprint.gcsSource)

  # discard staged object for last successful revision from being deleted
  for revision in revisions:
    if str(revision.state) == 'APPLIED':
      if revision.terraformBlueprint is not None:
        staged_objects.discard(revision.terraformBlueprint.gcsSource)
      break

  for obj in staged_objects:
    staging_bucket_util.DeleteStagingGCSFolder(gcs_client, obj)


def GetRevisionNumber(revision_full_name):
  """Returns the revision number from the revision name.

     e.g. - returns 12 for
     projects/p1/locations/l1/deployments/d1/revisions/r-12.

  Args:
    revision_full_name: string, the fully qualified name of the revision, e.g.
      "projects/p/locations/l/deployments/d/revisions/r-12".

  Returns:
    a revision number.
  """
  revision_ref = resources.REGISTRY.Parse(
      revision_full_name,
      collection='config.projects.locations.deployments.revisions',
  )
  revision_short_name = revision_ref.Name()
  return int(revision_short_name[2:])
