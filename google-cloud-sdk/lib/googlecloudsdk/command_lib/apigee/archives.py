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

from googlecloudsdk.core import log
from googlecloudsdk.core import requests
from googlecloudsdk.core.util import archive
from googlecloudsdk.core.util import files
from six.moves import urllib


class LocalDirectoryArchive(object):
  """Manages a local zip archive."""

  # The archive file name to save to.
  _ARCHIVE_FILE_NAME = 'apigee_archive_deployment.zip'

  def __init__(self, src_dir):
    self._src_dir = src_dir if src_dir is not None else files.GetCWD()
    self._tmp_dir = files.TemporaryDirectory()

  def Zip(self):
    """Creates a zip archive of the specified directory."""
    dst_file = os.path.join(self._tmp_dir.path, self._ARCHIVE_FILE_NAME)
    archive.MakeZipFromDir(dst_file, self._src_dir)
    return dst_file

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
