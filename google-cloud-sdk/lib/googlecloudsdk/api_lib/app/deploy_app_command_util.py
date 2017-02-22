
# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utility methods used by the deploy_app command."""

import json
import multiprocessing
import os
import platform
import shutil

import enum

from googlecloudsdk.api_lib.app import exceptions
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.command_lib.storage import storage_parallel
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import parallel
from googlecloudsdk.core.util import platforms
from googlecloudsdk.core.util import retry
from googlecloudsdk.third_party.appengine.tools import context_util


# Max App Engine file size; see https://cloud.google.com/appengine/docs/quotas
_MAX_FILE_SIZE = 32 * 1024 * 1024


_DEFAULT_NUM_THREADS = 8


class LargeFileError(core_exceptions.Error):

  def __init__(self, path, size, max_size):
    super(LargeFileError, self).__init__(
        ('Cannot upload file [{path}], which has size [{size}] (greater than '
         'maximum allowed size of [{max_size}]). Please delete the file or add '
         'to the skip_files entry in your application .yaml file and try '
         'again.'.format(path=path, size=size, max_size=max_size)))


class MultiError(core_exceptions.Error):

  def __init__(self, operation_description, errors):
    if len(errors) > 1:
      msg = 'Multiple errors occurred {0}\n'.format(operation_description)
    else:
      msg = 'An error occurred {0}\n'.format(operation_description)
    errors_string = '\n\n'.join(map(str, errors))
    super(core_exceptions.Error, self).__init__(msg + errors_string)
    self.errors = errors


def _BuildDeploymentManifest(info, source_dir, bucket_ref, tmp_dir):
  """Builds a deployment manifest for use with the App Engine Admin API.

  Args:
    info: An instance of yaml_parsing.ServiceInfo.
    source_dir: str, path to the service's source directory
    bucket_ref: The reference to the bucket files will be placed in.
    tmp_dir: A temp directory for storing generated files (currently just source
        context files).
  Returns:
    A deployment manifest (dict) for use with the Admin API.
  """
  excluded_files_regex = info.parsed.skip_files.regex
  manifest = {}
  bucket_url = 'https://storage.googleapis.com/{0}'.format(bucket_ref.bucket)

  # Normal application files.
  for rel_path in util.FileIterator(source_dir, excluded_files_regex):
    full_path = os.path.join(source_dir, rel_path)
    sha1_hash = file_utils.Checksum.HashSingleFile(full_path)
    manifest_path = '/'.join([bucket_url, sha1_hash])
    manifest[rel_path] = {
        'sourceUrl': manifest_path,
        'sha1Sum': sha1_hash
    }

  # Source context files. These are temporary files which indicate the current
  # state of the source repository (git, cloud repo, etc.)
  context_files = context_util.CreateContextFiles(
      tmp_dir, None, source_dir=source_dir)
  for context_file in context_files:
    rel_path = os.path.basename(context_file)
    if rel_path in manifest:
      # The source context file was explicitly provided by the user.
      log.debug('Source context already exists. Using the existing file.')
      continue
    else:
      sha1_hash = file_utils.Checksum.HashSingleFile(context_file)
      manifest_path = '/'.join([bucket_url, sha1_hash])
      manifest[rel_path] = {
          'sourceUrl': manifest_path,
          'sha1Sum': sha1_hash,
      }
  return manifest


def _BuildFileUploadMap(manifest, source_dir, bucket_ref, tmp_dir):
  """Builds a map of files to upload, indexed by their hash.

  This skips already-uploaded files.

  Args:
    manifest: A dict containing the deployment manifest for a single service.
    source_dir: The relative source directory of the service.
    bucket_ref: The GCS bucket reference to upload files into.
    tmp_dir: The path to a temporary directory where generated files may be
      stored. If a file in the manifest is not found in the source directory,
      it will be retrieved from this directory instead.

  Raises:
    LargeFileError: if one of the files to upload exceeds the maximum App Engine
    file size.

  Returns:
    A dict mapping hashes to file paths that should be uploaded.
  """
  files_to_upload = {}
  storage_client = storage_api.StorageClient()
  existing_items = storage_client.ListBucket(bucket_ref)
  for rel_path in manifest:
    full_path = os.path.join(source_dir, rel_path)
    # For generated files, the relative path is based on the tmp_dir rather
    # than source_dir. If the file is not in the source directory, look in
    # tmp_dir instead.
    if not os.path.exists(full_path):
      full_path = os.path.join(tmp_dir, rel_path)
    # Perform this check when creating the upload map, so we catch too-large
    # files that have already been uploaded
    size = os.path.getsize(full_path)
    if size > _MAX_FILE_SIZE:
      raise LargeFileError(full_path, size, _MAX_FILE_SIZE)

    sha1_hash = manifest[rel_path]['sha1Sum']
    if sha1_hash in existing_items:
      log.debug('Skipping upload of [{f}]'.format(f=rel_path))
    else:
      files_to_upload[sha1_hash] = full_path
  return files_to_upload


class FileUploadTask(object):

  def __init__(self, sha1_hash, path, bucket_url):
    self.sha1_hash = sha1_hash
    self.path = path
    self.bucket_url = bucket_url


def _UploadFile(file_upload_task):
  """Uploads a single file to Google Cloud Storage.

  Args:
    file_upload_task: FileUploadTask describing the file to upload

  Returns:
    None if the file was uploaded successfully or a stringified Exception if one
    was raised
  """
  storage_client = storage_api.StorageClient()
  bucket_ref = storage_util.BucketReference.FromBucketUrl(
      file_upload_task.bucket_url)
  retryer = retry.Retryer(max_retrials=3)

  path = file_upload_task.path
  sha1_hash = file_upload_task.sha1_hash
  log.debug('Uploading [{f}] to [{gcs}]'.format(f=path, gcs=sha1_hash))
  try:
    retryer.RetryOnException(
        storage_client.CopyFileToGCS,
        args=(bucket_ref, path, sha1_hash)
    )
  except Exception as err:  # pylint: disable=broad-except
    # pass all errors through as strings (not all exceptions can be serialized)
    return str(err)
  return None


class UploadStrategy(enum.Enum):
  """The file upload parallelism strategy to use.

  The old method of parallelism involved `num_file_upload_processes` (from the
  App Engine properties) processes, with a special case for OS X Sierra.

  The new method of parallelism involves `num_file_upload_threads` threads. It's
  being tested in beta right now. Eventually, it will be become the default. It
  should lead to fewer upload-related issues.

  The old old method of parallelism involved shelling out to gsutil.
  """
  PROCESSES = 1
  THREADS = 2
  GSUTIL = 3


def _UploadFilesThreads(files_to_upload, bucket_ref):
  """Uploads files to App Engine Cloud Storage bucket using threads.

  Args:
    files_to_upload: dict {str: str}, map of checksum to local path
    bucket_ref: storage_api.BucketReference, the reference to the bucket files
      will be placed in.

  Raises:
    MultiError: if one or more errors occurred during file upload.
  """
  num_threads = (properties.VALUES.app.num_file_upload_threads.GetInt() or
                 storage_parallel.DEFAULT_NUM_THREADS)
  tasks = []
  # Have to sort files because the test framework requires a known order for
  # mocked API calls.
  for sha1_hash, path in sorted(files_to_upload.iteritems()):
    task = storage_parallel.FileUploadTask(path, bucket_ref.ToBucketUrl(),
                                           sha1_hash)
    tasks.append(task)
  storage_parallel.UploadFiles(tasks, num_threads=num_threads)


def _UploadFilesProcesses(files_to_upload, bucket_ref):
  """Uploads files to App Engine Cloud Storage bucket using processes.

  Args:
    files_to_upload: dict {str: str}, map of checksum to local path
    bucket_ref: storage_api.BucketReference, the reference to the bucket files
      will be placed in.

  Raises:
    MultiError: if one or more errors occurred during file upload.
  """
  tasks = []
  # Have to sort files because the test framework requires a known order for
  # mocked API calls.
  for sha1_hash, path in sorted(files_to_upload.iteritems()):
    tasks.append(FileUploadTask(sha1_hash, path, bucket_ref.ToBucketUrl()))

  num_procs = properties.VALUES.app.num_file_upload_processes.GetInt()
  threads_per_proc = properties.VALUES.app.num_file_upload_threads.GetInt()
  if (platforms.OperatingSystem.Current() is platforms.OperatingSystem.MACOSX
      and platform.mac_ver()[0].startswith('10.12')):  # Sierra is version 10.12
    # OS X Sierra has issues with spawning processes in this manner
    if num_procs == 1:
      # num_procs set explicitly to 1 indicates that a user tried to turn off
      # parallelism, so we respect that.
      threads_per_proc = 1
    # Note: OS X (especially Sierra) has issues with multi-process file upload
    # as we had it implemented, so we just *ignore* the number of processes
    # requested and just use threads.
    # This is slightly confusing, but when we resolve the TODO in the below
    # branch of the if statement, this should get fixed.
    threads_per_proc = threads_per_proc or _DEFAULT_NUM_THREADS
    with parallel.GetPool(threads_per_proc) as pool:
      results = pool.Map(_UploadFile, tasks)
  elif num_procs > 1:
    pool = multiprocessing.Pool(num_procs)
    results = pool.map(_UploadFile, tasks)
    errors = filter(bool, results)
    pool.close()
    pool.join()
    if errors:
      raise MultiError('during file upload', errors)
  else:
    for task in tasks:
      error = _UploadFile(task)
      if error:
        raise MultiError('during file upload', [error])


def CopyFilesToCodeBucket(service, source_dir, bucket_ref,
                          upload_strategy):
  """Copies application files to the Google Cloud Storage code bucket.

  Uses either gsutil, the Cloud Storage API using processes, or the Cloud
  Storage API using threads.

  Consider the following original structure:
    app/
      main.py
      tools/
        foo.py

   Assume main.py has SHA1 hash 123 and foo.py has SHA1 hash 456. The resultant
   GCS bucket will look like this:
     gs://$BUCKET/
       123
       456

   The resulting App Engine API manifest will be:
     {
       "app/main.py": {
         "sourceUrl": "https://storage.googleapis.com/staging-bucket/123",
         "sha1Sum": "123"
       },
       "app/tools/foo.py": {
         "sourceUrl": "https://storage.googleapis.com/staging-bucket/456",
         "sha1Sum": "456"
       }
     }

    A 'list' call of the bucket is made at the start, and files that hash to
    values already present in the bucket will not be uploaded again.

  Args:
    service: ServiceYamlInfo, The service being deployed.
    source_dir: str, path to the service's source directory
    bucket_ref: The reference to the bucket files will be placed in.
    upload_strategy: The UploadStrategy to use

  Returns:
    A dictionary representing the manifest.

  Raises:
    ValueError: if an invalid upload strategy or None is given
  """
  if upload_strategy is UploadStrategy.GSUTIL:
    manifest = CopyFilesToCodeBucketGsutil(service, source_dir, bucket_ref)
    metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)
  else:
    # Collect a list of files to upload, indexed by the SHA so uploads are
    # deduplicated.
    with file_utils.TemporaryDirectory() as tmp_dir:
      manifest = _BuildDeploymentManifest(service, source_dir, bucket_ref,
                                          tmp_dir)
      files_to_upload = _BuildFileUploadMap(
          manifest, source_dir, bucket_ref, tmp_dir)
      if upload_strategy is UploadStrategy.THREADS:
        _UploadFilesThreads(files_to_upload, bucket_ref)
      elif upload_strategy is UploadStrategy.PROCESSES:
        _UploadFilesProcesses(files_to_upload, bucket_ref)
      else:
        raise ValueError('Invalid upload strategy ' + str(upload_strategy))
    log.status.Print('File upload done.')
    log.info('Manifest: [{0}]'.format(manifest))
    metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)
  return manifest


def CopyFilesToCodeBucketGsutil(service, source_dir, bucket_ref):
  """Examines services and copies files to a Google Cloud Storage bucket.

  Args:
    service: ServiceYamlInfo, The parsed service information.
    source_dir: str, path to the service's source directory
    bucket_ref: str A reference to a GCS bucket where the files will be
      uploaded.

  Returns:
    A dictionary representing the manifest. See _BuildStagingDirectory.
  """
  with file_utils.TemporaryDirectory() as staging_directory:
    excluded_files_regex = service.parsed.skip_files.regex
    manifest = _BuildStagingDirectory(source_dir,
                                      staging_directory,
                                      bucket_ref,
                                      excluded_files_regex)
    if manifest:
      log.status.Print('Copying files to Google Cloud Storage...')
      log.status.Print('Synchronizing files to [{b}].'
                       .format(b=bucket_ref.bucket))
      try:
        log.SetUserOutputEnabled(False)

        def _StatusUpdate(result, unused_retry_state):
          log.info('Error synchronizing files. Return code: {0}. '
                   'Retrying.'.format(result))

        retryer = retry.Retryer(max_retrials=3,
                                status_update_func=_StatusUpdate)
        def _ShouldRetry(return_code, unused_retry_state):
          return return_code != 0

        # gsutil expects a trailing /
        dest_dir = bucket_ref.ToBucketUrl()
        try:
          retryer.RetryOnResult(
              storage_api.Rsync,
              (staging_directory, dest_dir),
              should_retry_if=_ShouldRetry)
        except retry.RetryException as e:
          raise exceptions.StorageError(
              ('Could not synchronize files. The gsutil command exited with '
               'status [{s}]. Command output is available in [{l}].').format(
                   s=e.last_result, l=log.GetLogFilePath()))
      finally:
        # Reset to the standard log level.
        log.SetUserOutputEnabled(None)
      log.status.Print('File upload done.')

  return manifest


def _BuildStagingDirectory(source_dir, staging_dir, bucket_ref,
                           excluded_regexes):
  """Creates a staging directory to be uploaded to Google Cloud Storage.

  The staging directory will contain a symlink for each file in the original
  directory. The source is a file whose name is the sha1 hash of the original
  file and points to the original file.

  Consider the following original structure:
    app/
      main.py
      tools/
        foo.py
   Assume main.py has SHA1 hash 123 and foo.py has SHA1 hash 456. The resultant
   staging directory will look like:
     /tmp/staging/
       123 -> app/main.py
       456 -> app/tools/foo.py
   (Note: "->" denotes a symlink)

   If the staging directory is then copied to a GCS bucket at
   gs://staging-bucket/ then the resulting manifest will be:
     {
       "app/main.py": {
         "sourceUrl": "https://storage.googleapis.com/staging-bucket/123",
         "sha1Sum": "123"
       },
       "app/tools/foo.py": {
         "sourceUrl": "https://storage.googleapis.com/staging-bucket/456",
         "sha1Sum": "456"
       }
     }

  Args:
    source_dir: The original directory containing the application's source
      code.
    staging_dir: The directory where the staged files will be created.
    bucket_ref: A reference to the GCS bucket where the files will be uploaded.
    excluded_regexes: List of file patterns to skip while building the staging
      directory.

  Raises:
    LargeFileError: if one of the files to upload exceeds the maximum App Engine
    file size.

  Returns:
    A dictionary which represents the file manifest.
  """
  manifest = {}
  bucket_url = bucket_ref.GetPublicUrl()

  def AddFileToManifest(manifest_path, input_path):
    """Adds the given file to the current manifest.

    Args:
      manifest_path: The path to the file as it will be stored in the manifest.
      input_path: The location of the file to be added to the manifest.
    Returns:
      If the target was already in the manifest with different contexts,
      returns None. In all other cases, returns a target location to which the
      caller must copy, move, or link the file.
    """
    file_ext = os.path.splitext(input_path)[1]
    sha1_hash = file_utils.Checksum().AddFileContents(input_path).HexDigest()

    target_filename = sha1_hash + file_ext
    target_path = os.path.join(staging_dir, target_filename)

    dest_path = '/'.join([bucket_url, target_filename])
    old_url = manifest.get(manifest_path, {}).get('sourceUrl', '')
    if old_url and old_url != dest_path:
      return None
    manifest[manifest_path] = {
        'sourceUrl': dest_path,
        'sha1Sum': sha1_hash,
    }
    return target_path

  for relative_path in util.FileIterator(source_dir, excluded_regexes):
    local_path = os.path.join(source_dir, relative_path)
    size = os.path.getsize(local_path)
    if size > _MAX_FILE_SIZE:
      raise LargeFileError(local_path, size, _MAX_FILE_SIZE)
    target_path = AddFileToManifest(relative_path, local_path)
    if not os.path.exists(target_path):
      _CopyOrSymlink(local_path, target_path)

  context_files = context_util.CreateContextFiles(
      staging_dir, None, overwrite=True, source_dir=source_dir)
  for context_file in context_files:
    manifest_path = os.path.basename(context_file)
    target_path = AddFileToManifest(manifest_path, context_file)
    if not target_path:
      log.status.Print('Not generating {0} because a user-generated '
                       'file with the same name exists.'.format(manifest_path))
    if not target_path or os.path.exists(target_path):
      # If we get here, it probably means that the user already generated the
      # context file manually and put it either in the top directory or in some
      # subdirectory. The new context file is useless and may confuse later
      # stages of the upload (it is in the staging directory with a
      # nonconformant name), so delete it. The entry in the manifest will point
      # at the existing file.
      os.remove(context_file)
    else:
      # Rename the source-context*.json file (which is in the staging directory)
      # to the hash-based name in the same directory.
      os.rename(context_file, target_path)

  log.debug('Generated deployment manifest: "{0}"'.format(
      json.dumps(manifest, indent=2, sort_keys=True)))
  return manifest


def _CopyOrSymlink(source, target):
  try:
    # If possible, create a symlink to save time and space.
    os.symlink(source, target)
  except AttributeError:
    # The system does not support symlinks. Do a file copy instead.
    shutil.copyfile(source, target)
