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

import os
import uuid

from googlecloudsdk.api_lib.blueprints import blueprints_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.blueprints import deterministic_snapshot
from googlecloudsdk.command_lib.blueprints import error_handling
from googlecloudsdk.command_lib.blueprints import git_blueprint_util
from googlecloudsdk.command_lib.blueprints import staging_bucket_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import times
import six


def _UploadSourceDirToGCS(
    gcs_client,
    source,
    gcs_source_staging,
    ignore_file):
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

  size_str = resource_transform.TransformSize(
      source_snapshot.uncompressed_size)
  log.status.Print(
      'Uploading {num_files} file(s)'
      ' totalling {size}.'.format(
          num_files=len(source_snapshot.files), size=size_str))

  for file_metadata in source_snapshot.GetSortedFiles():
    full_local_path = os.path.join(file_metadata.root, file_metadata.path)

    target_obj_ref = 'gs://{0}/{1}/{2}'.format(
        gcs_source_staging.bucket,
        gcs_source_staging.object,
        file_metadata.path)
    target_obj_ref = resources.REGISTRY.Parse(
        target_obj_ref, collection='storage.objects')

    gcs_client.CopyFileToGCS(full_local_path, target_obj_ref)


def _UploadSourceToGCS(
    source,
    stage_bucket,
    ignore_file):
  """Uploads local content to GCS.

  This will ensure that the source and destination exist before triggering the
  upload.

  Args:
    source: string, a local path.
    stage_bucket: optional string. When not provided, the default staging
      bucket will be used (see GetDefaultStagingBucket). This string is of the
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
    gcs_source_staging_dir = 'gs://{0}/{1}'.format(
        gcs_source_bucket_name,
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
        'stage-bucket',
        'A bucket with name {} already exists and is owned by '
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

  upload_bucket = 'gs://{0}/{1}'.format(
      gcs_source_staging.bucket,
      gcs_source_staging.object)

  return upload_bucket


def Apply(
    source,
    deployment_full_name,
    stage_bucket,
    labels,
    messages,
    location,
    ignore_file,
    async_,
    source_git_subdir='.'):
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
    location: string, a region like "us-central1".
    ignore_file: optional string, a path to a gcloudignore file.
    async_: bool, if True, gcloud will return immediately, otherwise it will
      wait on the long-running operation.
    source_git_subdir: optional string. If "source" represents a Git repo, then
      this argument represents the directory within that Git repo to use.

  Returns:
    The resulting Deployment resource or, in the case that async_ is True, a
      long-running operation.
  """
  parent_resource = resources.REGISTRY.Create(
      collection='config.projects.locations',
      projectsId=properties.VALUES.core.project.GetOrFail(),
      locationsId=location)

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

  labels_message = {}
  # Whichever labels the user provides will become the full set of labels in the
  # resulting deployment.
  if labels is not None:
    labels_message = messages.Deployment.LabelsValue(
        additionalProperties=[
            messages.Deployment.LabelsValue
            .AdditionalProperty(key=key, value=value)
            for key, value in six.iteritems(labels)
        ])

  deployment = messages.Deployment(
      blueprint=blueprint,
      labels=labels_message,
  )

  # Check if a deployment with the given name already exists. If it does, we'll
  # update that deployment. If not, we'll create it.
  existing_deployment = blueprints_util.GetDeployment(deployment_full_name)
  is_creating_deployment = existing_deployment is None
  op = None

  # Get just the ID from the fully qualified name.
  deployment_id = resources.REGISTRY.Parse(
      deployment_full_name,
      collection='config.projects.locations.deployments').Name()

  if is_creating_deployment:
    log.info('Creating the deployment')

    op = blueprints_util.CreateDeployment(
        deployment,
        deployment_id,
        parent_resource.RelativeName())
  else:
    log.info('Updating the existing deployment')

    # If the user didn't specify labels here, then we don't want to overwrite
    # the existing labels on the deployment, so we provide them back to the
    # underlying API.
    if labels is None:
      deployment.labels = existing_deployment.labels

    op = blueprints_util.UpdateDeployment(
        deployment,
        deployment_full_name)

  log.debug('LRO: %s', op.name)

  # If the user chose to run asynchronously, then we'll match the output that
  # the automatically-generated Delete command issues and return immediately.
  if async_:
    log.status.Print('{0} request issued for: [{1}]'.format(
        'Create' if is_creating_deployment else 'Update',
        deployment_id))

    log.status.Print('Check operation [{}] for status.'.format(op.name))

    return op

  progress_message = '{} the deployment'.format(
      'Creating' if is_creating_deployment else 'Updating')

  applied_deployment = blueprints_util.WaitForDeploymentOperation(
      op, progress_message)

  if applied_deployment.state == messages.Deployment.StateValueValuesEnum.FAILED:
    error_handling.DeploymentFailed(applied_deployment)

  return applied_deployment
