
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
import os
import shutil

from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.source import context_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import retry


def _GetSha1(input_path):
  return file_utils.Checksum().AddFileContents(input_path).HexDigest()


def _BuildDeploymentManifest(info, bucket_ref, source_contexts,
                             context_dir):
  """Builds a deployment manifest for use with the App Engine Admin API.

  Args:
    info: An instance of yaml_parsing.ModuleInfo.
    bucket_ref: The reference to the bucket files will be placed in.
    source_contexts: A list of source context files.
    context_dir: A temp directory to place the source context files in.
  Returns:
    A deployment manifest (dict) for use with the Admin API.
  """
  source_dir = os.path.dirname(info.file)
  excluded_files_regex = info.parsed.skip_files.regex
  manifest = {}
  bucket_url = 'https://storage.googleapis.com/{0}'.format(bucket_ref.bucket)

  # Normal application files.
  for rel_path in util.FileIterator(source_dir, excluded_files_regex):
    full_path = os.path.join(source_dir, rel_path)
    sha1_hash = _GetSha1(full_path)
    manifest_path = '/'.join([bucket_url, sha1_hash])
    manifest[rel_path] = {
        'sourceUrl': manifest_path,
        'sha1Sum': sha1_hash
    }

  # Source context files.
  context_files = context_util.CreateContextFiles(
      context_dir, source_contexts, overwrite=True, source_dir=source_dir)
  for context_file in context_files:
    rel_path = os.path.basename(context_file)
    if rel_path in manifest:
      # The source context file was explicitly provided by the user.
      log.debug('Source context already exists. Skipping creation.')
      continue
    else:
      sha1_hash = _GetSha1(context_file)
      manifest_path = '/'.join([bucket_url, rel_path])
      manifest[rel_path] = {
          'sourceUrl': manifest_path,
          'sha1Sum': sha1_hash
      }
  return manifest


def _BuildFileUploadMap(manifest, source_dir, bucket_ref, storage_client):
  """Builds a map of files to upload, indexed by their hash.

  This skips already-uploaded files.

  Args:
    manifest: A dict containing the deployment manifest for a single module.
    source_dir: The relative source directory of the module.
    bucket_ref: The GCS bucket reference to upload files into.
    storage_client: A storage_v1 client object.

  Returns:
    A dict mapping hashes to file paths that should be uploaded.
  """
  files_to_upload = {}
  existing_items = set(cloud_storage.ListBucket(bucket_ref, storage_client))
  for rel_path in manifest:
    full_path = os.path.join(source_dir, rel_path)
    sha1_hash = manifest[rel_path]['sha1Sum']
    if sha1_hash in existing_items:
      log.debug('Skipping upload of [{f}]'.format(f=rel_path))
    else:
      files_to_upload[sha1_hash] = full_path
  return files_to_upload


def _UploadFiles(files_to_upload, bucket_ref, storage_client):
  for sha1_hash, path in sorted(files_to_upload.iteritems()):
    log.debug('Uploading [{f}] to [{gcs}]'.format(f=path, gcs=sha1_hash))
    retryer = retry.Retryer(max_retrials=3)
    retryer.RetryOnException(
        cloud_storage.CopyFileToGCS,
        args=(bucket_ref, path, sha1_hash, storage_client)
    )


def CopyFilesToCodeBucketNoGsUtil(
    modules, bucket_ref, source_contexts, storage_client):
  """Copies application files to the code bucket without calling gsutil.

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
    modules: Dictionary of user-specified modules.
    bucket_ref: The bucket reference to upload to.
    source_contexts: A list of source_contexts to also upload.
    storage_client: A storage_v1 client object.

  Returns:
    A lookup from module name to a dictionary representing the manifest.
  """
  manifests = {}

  # Collect a list of files to upload, indexed by the SHA so uploads are
  # deduplicated.
  for (module, info) in sorted(modules):
    with file_utils.TemporaryDirectory() as context_dir:
      manifest = _BuildDeploymentManifest(
          info, bucket_ref, source_contexts, context_dir)
      manifests[module] = manifest

      source_dir = os.path.dirname(info.file)
      files_to_upload = _BuildFileUploadMap(
          manifest, source_dir, bucket_ref, storage_client)
      _UploadFiles(files_to_upload, bucket_ref, storage_client)
  log.status.Print('File upload done.')
  log.info('Manifests: [{0}]'.format(manifests))
  return manifests


def CopyFilesToCodeBucket(
    modules, bucket_ref, source_contexts, unused_storage_client):
  """Examines modules and copies files to a Google Cloud Storage bucket.

  Args:
    modules: [(str, ModuleYamlInfo)] List of pairs of module name, and parsed
      module information.
    bucket_ref: str A reference to a GCS bucket where the files will be
      uploaded.
    source_contexts: [dict] List of json-serializable source contexts
      associated with the modules.
    unused_storage_client: Unused, there to satisfy the same interface as
      CopyFilesToCodeBucketNoGsutil
  Returns:
    A lookup from module name to a dictionary representing the manifest. See
    _BuildStagingDirectory.
  """
  manifests = {}
  with file_utils.TemporaryDirectory() as staging_directory:
    for (module, info) in modules:
      source_directory = os.path.dirname(info.file)
      excluded_files_regex = info.parsed.skip_files.regex

      manifest = _BuildStagingDirectory(source_directory,
                                        staging_directory,
                                        bucket_ref,
                                        excluded_files_regex,
                                        source_contexts)
      manifests[module] = manifest

    if any(manifest for manifest in manifests.itervalues()):
      log.status.Print('Copying files to Google Cloud Storage...')
      log.status.Print('Synchronizing files to [{b}].'.format(b=bucket_ref))
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
              cloud_storage.Rsync,
              (staging_directory, dest_dir),
              should_retry_if=_ShouldRetry)
        except retry.RetryException as e:
          raise exceptions.ToolException(
              ('Could not synchronize files. The gsutil command exited with '
               'status [{s}]. Command output is available in [{l}].').format(
                   s=e.last_result, l=log.GetLogFilePath()))
      finally:
        # Reset to the standard log level.
        log.SetUserOutputEnabled(None)
      log.status.Print('File upload done.')

  return manifests


def _BuildStagingDirectory(source_dir, staging_dir, bucket_ref,
                           excluded_regexes, source_contexts):
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
    source_contexts: A list of source contexts indicating the source code's
      origin.
  Returns:
    A dictionary which represents the file manifest.
  """
  manifest = {}
  bucket_url = bucket_ref.ToAppEngineApiReference()

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
    target_path = AddFileToManifest(relative_path, local_path)
    # target_path should not be None because FileIterator should never visit the
    # same file twice and if it did, the file would be identical and we'd get a
    # non-None return.
    if not target_path:
      raise exceptions.InternalError(
          'Attempted multiple uploads of {0} with varying contents.'.format(
              local_path))
    if not os.path.exists(target_path):
      _CopyOrSymlink(local_path, target_path)

  context_files = context_util.CreateContextFiles(
      staging_dir, source_contexts, overwrite=True, source_dir=source_dir)
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
