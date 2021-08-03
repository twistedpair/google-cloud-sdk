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
"""Utility functions for performing download operation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import os
import shutil

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import tracker_file_util
from googlecloudsdk.core.util import files


def decompress_gzip_if_necessary(source_resource,
                                 gzipped_path,
                                 destination_path,
                                 do_not_decompress_flag=False):
  """Checks if file is elligible for decompression and decompresses if true.

  Args:
    source_resource (ObjectResource): May contain encoding metadata.
    gzipped_path (str): File path to unzip.
    destination_path (str): File path to write unzipped file to.
    do_not_decompress_flag (bool): User flag that blocks decompression.

  Returns:
    (bool) True if file was successfully decompressed, else False.
  """
  content_encoding = getattr(source_resource.metadata, 'contentEncoding', '')
  if (do_not_decompress_flag or content_encoding is None or
      'gzip' not in content_encoding.split(',')):
    return False

  try:
    with gzip.open(gzipped_path, 'rb') as gzipped_file:
      with files.BinaryFileWriter(
          destination_path, create_path=True) as ungzipped_file:
        shutil.copyfileobj(gzipped_file, ungzipped_file)
    return True
  except OSError:
    # May indicate trying to decompress non-gzipped file. Clean up.
    os.remove(destination_path)

  return False


def validate_download_hash_and_delete_corrupt_files(download_path, source_hash,
                                                    destination_hash):
  """Confirms hashes match for copied objects.

  Args:
    download_path (str): URL of object being validated.
    source_hash (str): Hash of source object.
    destination_hash (str): Hash of downloaded object.

  Raises:
    HashMismatchError: Hashes are not equal.
  """
  try:
    hash_util.validate_object_hashes_match(download_path, source_hash,
                                           destination_hash)
  except errors.HashMismatchError:
    os.remove(download_path)
    tracker_file_util.delete_download_tracker_files(
        storage_url.storage_url_from_string(download_path))
    raise
