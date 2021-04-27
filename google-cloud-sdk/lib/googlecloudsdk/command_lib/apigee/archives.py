# -*- coding: utf-8 -*- # Lint as: python3
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
"""Helper functions for working with Apigee archive deployments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import zipfile

from googlecloudsdk.command_lib.apigee import errors
from googlecloudsdk.core import log
from googlecloudsdk.core import requests
from googlecloudsdk.core.util import archive
from googlecloudsdk.core.util import files
from six.moves import urllib


class LocalDirectoryArchive(object):
  """Manages a local zip archive."""

  # The archive file name to save to.
  _ARCHIVE_FILE_NAME = 'apigee_archive_deployment.zip'
  _APIGEE_ARCHIVE_FILE_EXTENSIONS = [
      '.jar',
      '.java',
      '.js',
      '.jsc',
      '.json',
      '.properties',
      '.py',
      '.wsdl',
      '.xml',
      '.xsd',
  ]
  _ARCHIVE_ROOT = os.path.join('src', 'main', 'apigee')

  def __init__(self, src_dir):
    self._CheckIfPathExists(src_dir)
    # Check if the path resolves to a directory.
    if src_dir and not os.path.isdir(src_dir):
      raise errors.SourcePathIsNotDirectoryError(src_dir)
    self._src_dir = src_dir if src_dir is not None else files.GetCWD()
    self._tmp_dir = files.TemporaryDirectory()

  def _CheckIfPathExists(self, path):
    """Checks that the given file path exists."""
    if path and not os.path.exists(path):
      raise files.MissingFileError(
          'Path to archive deployment does not exist: {}'.format(path))

  def _ZipFileFilter(self, file_name):
    """Filter all files in the archive directory to only allow Apigee files."""
    if not file_name.startswith(self._ARCHIVE_ROOT):
      return False
    _, ext = os.path.splitext(file_name)
    full_path = os.path.join(self._src_dir, file_name)
    # Skip hidden unix directories. Assume hidden directories and the files
    # within them are not intended to be included. This check needs to happen
    # first so MakeZipFromDir does not continue to process the files within the
    # hidden directory which can contain the same file types that Apigee
    # supports.
    if os.path.basename(full_path).startswith('.'):
      return False
    # MakeZipFromDir will only process files in a directory if the containing
    # directory first evaluates to True, so all directories are approved here.
    if os.path.isdir(full_path):
      return True
    # Only include Apigee supported file extensions.
    if (os.path.isfile(full_path) and
        ext.lower() in self._APIGEE_ARCHIVE_FILE_EXTENSIONS):
      return True
    return False

  def Zip(self):
    """Creates a zip archive of the specified directory."""
    dst_file = os.path.join(self._tmp_dir.path, self._ARCHIVE_FILE_NAME)
    archive.MakeZipFromDir(dst_file, self._src_dir, self._ZipFileFilter)
    return dst_file

  def ValidateZipFilePath(self, zip_path):
    """Checks that the zip file path exists and the file is a zip archvie."""
    self._CheckIfPathExists(zip_path)
    if not zipfile.is_zipfile(zip_path):
      raise errors.BundleFileNotValidError(zip_path)

  def Close(self):
    """Deletes the local temporary directory."""
    return self._tmp_dir.Close()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, val, tb):
    try:
      self.Close()
    except:  # pylint: disable=bare-except
      log.warning('Temporary directory was not successfully deleted.')
      return True


def GetUploadFileId(upload_url):
  """Helper function to extract the upload file id from the signed URL.

  Archive deployments must be uploaded to a provided signed URL in the form of:
  https://storage.googleapis.com/<bucket id>/<file id>.zip?<additional headers>
  This function extracts the file id from the URL (e.g., <file id>.zip).

  Args:
    upload_url: A string of the signed URL.

  Returns:
    A string of the file id.
  """
  url = urllib.parse.urlparse(upload_url)
  split_path = url.path.split('/')
  return split_path[-1]


def UploadArchive(upload_url, zip_file):
  """Uploads the specified zip file with a PUT request to the provided URL.

  Args:
    upload_url: A string of the URL to send the PUT request to. Required to be a
      signed URL from GCS.
    zip_file: A string of the file path to the zip file to upload.

  Returns:
    A requests.Response object.
  """
  sess = requests.GetSession()
  # Required headers for the Apigee generated signed URL.
  headers = {
      'content-type': 'application/zip',
      'x-goog-content-length-range': '0,1073741824'
  }
  with files.BinaryFileReader(zip_file) as data:
    response = sess.put(upload_url, data=data, headers=headers)
  return response
