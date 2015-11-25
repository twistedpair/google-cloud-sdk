
# Copyright 2015 Google Inc. All Rights Reserved.

"""Utility methods used by the deploy_app command."""

import json
import os
import shutil

from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files as file_utils
from googlecloudsdk.core.util import retry


def CopyFilesToCodeBucket(modules, bucket):
  """Examines modules and copies files to a Google Cloud Storage bucket.

  Args:
    modules: [(str, ModuleYamlInfo)] List of pairs of module name, and parsed
      module information.
    bucket: str A URL to the Google Cloud Storage bucket where the files will be
      uploaded.
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
                                        bucket,
                                        excluded_files_regex)
      manifests[module] = manifest

    if any(manifest for manifest in manifests.itervalues()):
      log.status.Print('Copying files to Google Cloud Storage...')
      log.status.Print('Synchronizing files to [{b}].'.format(b=bucket))
      try:
        log.SetUserOutputEnabled(False)

        def _StatusUpdate(result, unused_retry_state):
          log.info('Error synchronizing files. Return code: {0}. '
                   'Retrying.'.format(result))

        retryer = retry.Retryer(max_retrials=3,
                                status_update_func=_StatusUpdate)
        def _ShouldRetry(return_code, unused_retry_state):
          return return_code != 0

        try:
          retryer.RetryOnResult(
              cloud_storage.Rsync,
              (staging_directory, bucket),
              should_retry_if=_ShouldRetry)
        except retry.RetryException as e:
          raise exceptions.ToolException(
              ('Could not synchronize files. The gsutil command exited with '
               'status [{s}]. Command output is available in [{l}].').format(
                   s=e.last_result, l=log.GetLogFilePath()))
      finally:
        # Reset to the standard log level.
        log.SetUserOutputEnabled(None)

  return manifests


def _BuildStagingDirectory(source_dir, staging_dir, bucket, excluded_regexes):
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
    bucket: A URL to the Google Cloud Storage bucket where the files will be
      uploaded.
    excluded_regexes: List of file patterns to skip while building the staging
      directory.
  Returns:
    A dictionary which represents the file manifest.
  """
  manifest = {}

  bucket_url = cloud_storage.GsutilReferenceToApiReference(bucket)

  for relative_path in util.FileIterator(source_dir, excluded_regexes,
                                         runtime=None):
    local_path = os.path.join(source_dir, relative_path)
    file_ext = os.path.splitext(local_path)[1]
    sha1_hash = file_utils.Checksum().AddFileContents(local_path).HexDigest()

    target_filename = sha1_hash + file_ext
    target_path = os.path.join(staging_dir, target_filename)
    if not os.path.exists(target_path):
      _CopyOrSymlink(local_path, target_path)

    dest_path = '/'.join([bucket_url.rstrip('/'), target_filename])
    manifest[relative_path] = {
        'sourceUrl': dest_path,
        'sha1Sum': sha1_hash,
    }

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

