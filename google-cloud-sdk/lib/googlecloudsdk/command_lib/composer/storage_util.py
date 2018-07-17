# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Common utility functions for Composer environment storage commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os.path
import posixpath

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import transfer

from googlecloudsdk.api_lib.composer import environments_util as environments_api_util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.composer import util as command_util
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core import log
import six


BUCKET_MISSING_MSG = 'Could not retrieve Cloud Storage bucket for environment.'


def List(env_ref, gcs_subdir, release_track=base.ReleaseTrack.GA):
  """Lists all resources in one folder of bucket.

  Args:
    env_ref: googlecloudsdk.core.resources.Resource, Resource representing
        the Environment whose corresponding bucket to list.
    gcs_subdir: str, subdir of the Cloud Storage bucket which to list
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.

  Returns:
    list of Objects inside subdirectory of Cloud Storage bucket for environment

  Raises:
    command_util.Error: if the storage bucket could not be retrieved
  """
  bucket_ref = _GetStorageBucket(env_ref, release_track=release_track)
  storage_client = storage_api.StorageClient()
  return storage_client.ListBucket(bucket_ref, prefix=gcs_subdir + '/')


def Import(env_ref, sources, destination, release_track=base.ReleaseTrack.GA):
  """Imports files and directories into a bucket.

  Args:
    env_ref: googlecloudsdk.core.resources.Resource, Resource representing
        the Environment whose bucket into which to import.
    sources: [str], a list of paths from which to import files into the
        environment's bucket. Directory sources are imported recursively; the
        directory itself will be present in the destination bucket.
        Must contain at least one non-empty value.
    destination: str, subdir of the Cloud Storage bucket into which to import
        `sources`. Must have a single trailing slash but no leading slash. For
        example, 'data/foo/bar/'.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.

  Returns:
    None

  Raises:
    command_util.Error: if the storage bucket could not be retrieved
    command_util.GsutilError: the gsutil command failed
  """
  gcs_bucket = _GetStorageBucket(env_ref, release_track=release_track)
  destination_ref = storage_util.ObjectReference(gcs_bucket, destination)

  try:
    retval = storage_util.RunGsutilCommand(
        'cp',
        command_args=(['-r'] + sources + [destination_ref.ToUrl()]),
        run_concurrent=True,
        out_func=log.out.write,
        err_func=log.err.write)
  except (execution_utils.PermissionError,
          execution_utils.InvalidCommandError) as e:
    raise command_util.GsutilError(six.text_type(e))
  if retval:
    raise command_util.GsutilError('gsutil returned non-zero status code.')


def Export(env_ref, sources, destination, release_track=base.ReleaseTrack.GA):
  """Exports files and directories from an environment's Cloud Storage bucket.

  Args:
    env_ref: googlecloudsdk.core.resources.Resource, Resource representing
        the Environment whose bucket from which to export.
    sources: [str], a list of bucket-relative paths from which to export files.
        Directory sources are imported recursively; the directory itself will
        be present in the destination bucket. Can also include wildcards.
    destination: str, existing local directory or path to a Cloud Storage
        bucket or directory object to which to export.
        Must have a single trailing slash but no leading slash. For
        example, 'dir/foo/bar/'.
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.

  Returns:
    None

  Raises:
    command_util.Error: if the storage bucket could not be retrieved or a
      non-Cloud Storage destination that is not a local directory was provided.
    command_util.GsutilError: the gsutil command failed
  """
  gcs_bucket = _GetStorageBucket(env_ref, release_track=release_track)
  source_refs = [
      storage_util.ObjectReference(gcs_bucket, source)
      for source in sources
  ]
  if destination.startswith('gs://'):
    destination = posixpath.join(destination.strip(posixpath.sep), '')
  elif not os.path.isdir(destination):
    raise command_util.Error('Destination for export must be a directory.')

  try:
    retval = storage_util.RunGsutilCommand(
        'cp',
        command_args=(['-r']
                      + [s.ToUrl() for s in source_refs]
                      + [destination]),
        run_concurrent=True,
        out_func=log.out.write,
        err_func=log.err.write)
  except (execution_utils.PermissionError,
          execution_utils.InvalidCommandError) as e:
    raise command_util.GsutilError(six.text_type(e))
  if retval:
    raise command_util.GsutilError('gsutil returned non-zero status code.')


def Delete(env_ref, target, gcs_subdir, release_track=base.ReleaseTrack.GA):
  """Deletes objects in a folder of an environment's bucket.

  gsutil deletes directory marker objects even when told to delete just the
  directory's contents, so we need to check that it exists and create it if it
  doesn't.

  A better alternative will be to use the storage API to list
  objects by prefix and implement deletion ourselves

  Args:
    env_ref: googlecloudsdk.core.resources.Resource, Resource representing
        the Environment in whose corresponding bucket to delete objects.
    target: str, the path within the gcs_subdir directory in the bucket
        to delete.
    gcs_subdir: str, subdir of the Cloud Storage bucket in which to delete.
        Should not contain slashes, for example "dags".
    release_track: base.ReleaseTrack, the release track of command. Will dictate
        which Composer client library will be used.
  """
  gcs_bucket = _GetStorageBucket(env_ref, release_track=release_track)
  target_ref = storage_util.ObjectReference(gcs_bucket,
                                            posixpath.join(gcs_subdir, target))
  try:
    retval = storage_util.RunGsutilCommand(
        'rm',
        command_args=(['-r', target_ref.ToUrl()]),
        run_concurrent=True,
        out_func=log.out.write,
        err_func=log.err.write)
  except (execution_utils.PermissionError,
          execution_utils.InvalidCommandError) as e:
    raise command_util.GsutilError(six.text_type(e))
  if retval:
    raise command_util.GsutilError('gsutil returned non-zero status code.')
  _EnsureSubdirExists(gcs_bucket, gcs_subdir)


def _EnsureSubdirExists(bucket_ref, subdir):
  """Checks that a directory marker object exists in the bucket or creates one.

  The directory marker object is needed for subdir listing to not crash
  if the directory is empty.

  Args:
    bucket_ref: googlecloudsk.api_lib.storage.storage_util.BucketReference,
        a reference to the environment's bucket
    subdir: str, the subdirectory to check or recreate. Should not contain
        slashes.
  """
  subdir_name = '{}/'.format(subdir)
  subdir_ref = storage_util.ObjectReference(bucket_ref, subdir_name)
  storage_client = storage_api.StorageClient()
  try:
    storage_client.GetObject(subdir_ref)
  except apitools_exceptions.HttpNotFoundError:
    # Insert an empty object into the bucket named subdir_name, which will
    # serve as an empty directory marker.
    insert_req = storage_client.messages.StorageObjectsInsertRequest(
        bucket=bucket_ref.bucket,
        name=subdir_name)
    upload = transfer.Upload.FromStream(
        io.BytesIO(), 'application/octet-stream')
    try:
      storage_client.client.objects.Insert(insert_req, upload=upload)
    except apitools_exceptions.HttpError:
      raise command_util.Error(
          'Error re-creating empty {}/ directory. List calls may'.format(subdir)
          + 'fail, but importing will restore the directory.')


def _GetStorageBucket(env_ref, release_track=base.ReleaseTrack.GA):
  env = environments_api_util.Get(env_ref, release_track=release_track)
  if not env.config.dagGcsPrefix:
    raise command_util.Error(BUCKET_MISSING_MSG)
  try:
    gcs_dag_dir = storage_util.ObjectReference.FromUrl(env.config.dagGcsPrefix)
  except (storage_util.InvalidObjectNameError, ValueError):
    raise command_util.Error(BUCKET_MISSING_MSG)
  return gcs_dag_dir.bucket_ref
