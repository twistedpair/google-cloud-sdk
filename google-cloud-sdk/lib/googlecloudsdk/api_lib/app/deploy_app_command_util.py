
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

import hashlib
import json
import os
import shutil

from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.command_lib.storage import storage_parallel
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files as file_utils
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
    sha1_hash = file_utils.Checksum.HashSingleFile(full_path,
                                                   algorithm=hashlib.sha1)
    manifest_path = '/'.join([bucket_url, sha1_hash])
    manifest[_FormatForManifest(rel_path)] = {
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
      sha1_hash = file_utils.Checksum.HashSingleFile(context_file,
                                                     algorithm=hashlib.sha1)
      manifest_path = '/'.join([bucket_url, sha1_hash])
      manifest[_FormatForManifest(rel_path)] = {
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
  storage_parallel.UploadFiles(tasks, num_threads=num_threads,
                               show_progress_bar=True)


def CopyFilesToCodeBucket(service, source_dir, bucket_ref):
  """Copies application files to the Google Cloud Storage code bucket.

  Use the Cloud Storage API using threads.

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

  Returns:
    A dictionary representing the manifest.
  """
  metrics.CustomTimedEvent(metric_names.COPY_APP_FILES_START)
  # Collect a list of files to upload, indexed by the SHA so uploads are
  # deduplicated.
  with file_utils.TemporaryDirectory() as tmp_dir:
    manifest = _BuildDeploymentManifest(service, source_dir, bucket_ref,
                                        tmp_dir)
    files_to_upload = _BuildFileUploadMap(
        manifest, source_dir, bucket_ref, tmp_dir)
    _UploadFilesThreads(files_to_upload, bucket_ref)
  log.status.Print('File upload done.')
  log.info('Manifest: [{0}]'.format(manifest))
  metrics.CustomTimedEvent(metric_names.COPY_APP_FILES)
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
    sha1_hash = (file_utils.Checksum(algorithm=hashlib.sha1)
                 .AddFileContents(input_path).HexDigest())

    target_filename = sha1_hash + file_ext
    target_path = os.path.join(staging_dir, target_filename)

    dest_path = '/'.join([bucket_url, target_filename])
    old_url = manifest.get(manifest_path, {}).get('sourceUrl', '')
    if old_url and old_url != dest_path:
      return None
    manifest[_FormatForManifest(manifest_path)] = {
        'sourceUrl': dest_path,
        'sha1Sum': sha1_hash,
    }
    return target_path

  for relative_path in util.FileIterator(source_dir, excluded_regexes):
    local_path = os.path.join(source_dir, relative_path)
    size = os.path.getsize(local_path)
    if size > _MAX_FILE_SIZE:
      raise LargeFileError(local_path, size, _MAX_FILE_SIZE)
    target_path = AddFileToManifest(_FormatForManifest(relative_path),
                                    local_path)
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


def _FormatForManifest(filename):
  """Reformat a filename for the deployment manifest if it is Windows format."""
  if os.path.sep == '\\':
    return filename.replace('\\', '/')
  return filename
