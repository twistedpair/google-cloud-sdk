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
"""Support library to handle the build submit."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os.path
import uuid

from googlecloudsdk.api_lib.cloudbuild import snapshot
from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.command_lib.deploy import release_util as util
from googlecloudsdk.command_lib.deploy import staging_bucket_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_transform
from googlecloudsdk.core.util import times

_ALLOWED_SOURCE_EXT = ['.zip', '.tgz', '.gz']
_SKAFFOLD_CONFIG_PATH = 'gs://{}/source'
_MANIFEST_BUCKET = 'gs://{}/render'


def _SetSource(release_config,
               source,
               gcs_source_staging_dir,
               gcs_render_dir,
               ignore_file,
               hide_logs=False):
  """Set the source for the release config."""
  safe_project_id = staging_bucket_util.GetSafeProject()
  default_gcs_source = False
  default_bucket_name = staging_bucket_util.GetDefaultStagingBucket(
      safe_project_id)
  if gcs_source_staging_dir is None:
    default_gcs_source = True
    gcs_source_staging_dir = _SKAFFOLD_CONFIG_PATH.format(default_bucket_name)

  if not gcs_source_staging_dir.startswith('gs://'):
    raise c_exceptions.InvalidArgumentException('--gcs-source-staging-dir',
                                                'must be a GCS bucket')

  if gcs_render_dir is None:
    gcs_render_dir = _MANIFEST_BUCKET.format(default_bucket_name)
  if not gcs_render_dir.startswith('gs://'):
    raise c_exceptions.InvalidArgumentException('--gcs-render-dir',
                                                'must be a GCS bucket')
  release_config.manifestBucket = gcs_render_dir

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
      gcs_source_staging_dir, collection='storage.objects')

  try:
    gcs_client.CreateBucketIfNotExists(
        gcs_source_staging_dir.bucket, check_ownership=default_gcs_source)
  except storage_api.BucketInWrongProjectError:
    # If we're using the default bucket but it already exists in a different
    # project, then it could belong to a malicious attacker (b/33046325).
    raise c_exceptions.RequiredArgumentException(
        'gcs-source-staging-dir',
        'A bucket with name {} already exists and is owned by '
        'another project. Specify a bucket using '
        '--gcs-source-staging-dir.'.format(default_bucket_name))

  if gcs_source_staging_dir.object:
    staged_object = gcs_source_staging_dir.object + '/' + staged_object
  gcs_source_staging = resources.REGISTRY.Create(
      collection='storage.objects',
      bucket=gcs_source_staging_dir.bucket,
      object=staged_object)
  if source.startswith('gs://'):
    gcs_source = resources.REGISTRY.Parse(source, collection='storage.objects')
    staged_source_obj = gcs_client.Rewrite(gcs_source, gcs_source_staging)
    release_config.skaffoldConfigPath = 'gs://{bucket}/{object}'.format(
        bucket=staged_source_obj.bucket, object=staged_source_obj.name)
  else:
    if not os.path.exists(source):
      raise c_exceptions.BadFileException(
          'could not find source [{src}]'.format(src=source))
    if os.path.isdir(source):
      source_snapshot = snapshot.Snapshot(source, ignore_file=ignore_file)
      size_str = resource_transform.TransformSize(
          source_snapshot.uncompressed_size)
      if not hide_logs:
        log.status.Print(
            'Creating temporary tarball archive of {num_files} file(s)'
            ' totalling {size} before compression.'.format(
                num_files=len(source_snapshot.files), size=size_str))
      staged_source_obj = source_snapshot.CopyTarballToGCS(
          gcs_client,
          gcs_source_staging,
          ignore_file=ignore_file,
          hide_logs=hide_logs)
      release_config.skaffoldConfigPath = 'gs://{bucket}/{object}'.format(
          bucket=staged_source_obj.bucket, object=staged_source_obj.name)
    elif os.path.isfile(source):
      _, ext = os.path.splitext(source)
      if ext not in _ALLOWED_SOURCE_EXT:
        raise c_exceptions.BadFileException('local file [{src}] is none of ' +
                                            ', '.join(_ALLOWED_SOURCE_EXT))
      if not hide_logs:
        log.status.Print('Uploading local file [{src}] to '
                         '[gs://{bucket}/{object}].'.format(
                             src=source,
                             bucket=gcs_source_staging.bucket,
                             object=gcs_source_staging.object,
                         ))
      staged_source_obj = gcs_client.CopyFileToGCS(source, gcs_source_staging)
      release_config.skaffoldConfigPath = 'gs://{bucket}/{object}'.format(
          bucket=staged_source_obj.bucket, object=staged_source_obj.name)
  return release_config


def _SetImages(messages, release_config, images, build_artifacts):
  """Set the image substitutions for the release config."""
  if build_artifacts:
    images = util.LoadBuildArtifactFile(build_artifacts)

  return util.SetBuildArtifacts(images, messages, release_config)


class ReleaseClient(object):
  """Client for release service in the Cloud Deploy API."""

  def __init__(self, client=None, messages=None):
    """Initialize a release.ReleaseClient.

    Args:
      client: base_api.BaseApiClient, the client class for Cloud Deploy.
      messages: module containing the definitions of messages for Cloud Deploy.
    """
    self.client = client or client_util.GetClientInstance()
    self.messages = messages or client_util.GetMessagesModule(client)
    self._service = self.client.projects_locations_deliveryPipelines_releases

  def CreateReleaseConfig(self, source, gcs_source_staging_dir, ignore_file,
                          gcs_render_dir, images, build_artifacts):
    """Returns a build config."""
    release_config = self.messages.Release()
    release_config = _SetSource(release_config, source, gcs_source_staging_dir,
                                gcs_render_dir, ignore_file)
    release_config = _SetImages(self.messages, release_config, images,
                                build_artifacts)

    return release_config

  def Create(self, release_ref, release_config):
    """Create the release resource.

    Args:
      release_ref: release resource object.
      release_config: release message.

    Returns:
      The operation message.
    """
    log.debug('creating release: ' + repr(release_config))

    return self._service.Create(
        self.messages
        .ClouddeployProjectsLocationsDeliveryPipelinesReleasesCreateRequest(
            parent=release_ref.Parent().RelativeName(),
            release=release_config,
            releaseId=release_ref.Name()))

  def Promote(self, release_ref, to_target):
    """Promotes the release to the first target in the promote sequence.

    Args:
      release_ref: release resource object.
      to_target: the destination target to promote into.

    Returns:
      The operation message.
    """
    log.debug('promoting release to target{}.'.format(to_target))

    return self._service.Promote(
        self.messages
        .ClouddeployProjectsLocationsDeliveryPipelinesReleasesPromoteRequest(
            toTarget=to_target, name=release_ref.RelativeName()))
