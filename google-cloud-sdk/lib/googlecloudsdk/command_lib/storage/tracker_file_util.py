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
"""Utilities for tracker files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
import hashlib
import json
import os
import re

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files

# The maximum length of a file name can vary wildly between operating
# systems, so always ensure that tracker files are less than 100 characters.
_MAX_TRACKER_FILE_NAME_LENGTH = 100
_TRAILING_FILE_NAME_CHARACTERS_FOR_DISPLAY = 16
_RE_DELIMITER_PATTERN = r'[/\\]'


class TrackerFileType(enum.Enum):
  UPLOAD = 'upload'
  DOWNLOAD = 'download'
  DOWNLOAD_COMPONENT = 'download_component'
  PARALLEL_UPLOAD = 'parallel_upload'
  SLICED_DOWNLOAD = 'sliced_download'
  REWRITE = 'rewrite'


def _create_tracker_directory_if_needed():
  """Looks up or creates the gcloud storage tracker file directory.

  Resumable transfer tracker files will be kept here.

  Returns:
    The path string to the tracker directory.
  """
  tracker_directory = properties.VALUES.storage.tracker_files_directory.Get()
  # Thread-safe method to prevent parallel processing errors.
  files.MakeDir(tracker_directory)
  return tracker_directory


def _get_hashed_file_name(file_name):
  """Applies a hash function (SHA1) to shorten the passed file name.

  The spec for the hashed file name is as follows:
      TRACKER_<hash>_<trailing>
  'hash' is a SHA1 hash on the original file name, and 'trailing' is
  the last chars of the original file name. Max file name lengths
  vary by operating system, so the goal of this function is to ensure
  the hashed version takes fewer than _MAX_TRACKER_FILE_NAME_LENGTH characters.

  Args:
    file_name (str): File name to be hashed. May be unicode or bytes.

  Returns:
    String of shorter, hashed file_name.
  """
  name_hash_object = hashlib.sha1(file_name.encode('utf-8'))
  return 'TRACKER_{}.{}'.format(
      name_hash_object.hexdigest(),
      file_name[-1 * _TRAILING_FILE_NAME_CHARACTERS_FOR_DISPLAY:])


def _get_hashed_path(tracker_file_name, tracker_file_type,
                     resumable_tracker_directory):
  """Hashes and returns a tracker file path.

  Args:
    tracker_file_name (str): The tracker file name prior to it being hashed.
    tracker_file_type (TrackerFileType): The TrackerFileType of
      res_tracker_file_name.
    resumable_tracker_directory (str): Path to directory of tracker files.

  Returns:
    Final (hashed) tracker file path.

  Raises:
    Error: Hashed file path is too long.
  """
  hashed_tracker_file_name = _get_hashed_file_name(tracker_file_name)
  tracker_file_name_with_type = '{}_{}'.format(tracker_file_type.value.lower(),
                                               hashed_tracker_file_name)
  if len(tracker_file_name_with_type) > _MAX_TRACKER_FILE_NAME_LENGTH:
    raise errors.Error(
        'Tracker file name hash is over max character limit of {}: {}'.format(
            _MAX_TRACKER_FILE_NAME_LENGTH, tracker_file_name_with_type))

  tracker_file_path = (
      resumable_tracker_directory + os.sep + tracker_file_name_with_type)
  return tracker_file_path


def get_tracker_file_path(destination_url,
                          tracker_file_type,
                          source_url=None,
                          component_number=None):
  """Retrieves path string to tracker file.

  Args:
    destination_url (storage_url.StorageUrl): Describes the destination file.
    tracker_file_type (TrackerFileType): Type of tracker file to retrieve.
    source_url (storage_url.StorageUrl): Describes the source file.
    component_number (int): The number of the component is being tracked for a
      sliced download.

  Returns:
    String file path to tracker file.
  """
  if tracker_file_type == TrackerFileType.UPLOAD:
    # Encode the destination bucket and object name into the tracker file name.
    raw_result_tracker_file_name = 'resumable_upload__{}__{}__{}.url'.format(
        destination_url.bucket_name, destination_url.object_name,
        destination_url.scheme.value)
  elif tracker_file_type == TrackerFileType.DOWNLOAD:
    # Encode the fully-qualified destination file into the tracker file name.
    raw_result_tracker_file_name = 'resumable_download__{}__{}.etag'.format(
        os.path.realpath(destination_url.object_name),
        destination_url.scheme.value)
  elif tracker_file_type == TrackerFileType.DOWNLOAD_COMPONENT:
    # Encode the fully-qualified destination file name and the component number
    # into the tracker file name.
    raw_result_tracker_file_name = 'resumable_download__{}__{}__{}.etag'.format(
        os.path.realpath(destination_url.object_name),
        destination_url.scheme.value, component_number)
  elif tracker_file_type == TrackerFileType.PARALLEL_UPLOAD:
    # Encode the destination bucket and object names as well as the source file
    # into the tracker file name.
    raw_result_tracker_file_name = 'parallel_upload__{}__{}__{}__{}.url'.format(
        destination_url.bucket_name, destination_url.object_name, source_url,
        destination_url.scheme.value)
  elif tracker_file_type == TrackerFileType.SLICED_DOWNLOAD:
    # Encode the fully-qualified destination file into the tracker file name.
    raw_result_tracker_file_name = 'sliced_download__{}__{}.etag'.format(
        os.path.realpath(destination_url.object_name),
        destination_url.scheme.value)
  elif tracker_file_type == TrackerFileType.REWRITE:
    raw_result_tracker_file_name = 'rewrite__{}__{}__{}__{}__{}.token'.format(
        source_url.bucket_name, source_url.object_name,
        destination_url.bucket_name, destination_url.object_name,
        destination_url.scheme.value)

  result_tracker_file_name = re.sub(_RE_DELIMITER_PATTERN, '_',
                                    raw_result_tracker_file_name)
  resumable_tracker_directory = _create_tracker_directory_if_needed()
  return _get_hashed_path(result_tracker_file_name, tracker_file_type,
                          resumable_tracker_directory)


def get_sliced_download_tracker_file_paths(destination_url):
  """Gets a list of tracker file paths for each slice of a sliced download.

  The returned list consists of the parent tracker file path in index 0
  followed by component tracker files.

  Args:
    destination_url: Destination URL for tracker file.

  Returns:
    List of string file paths to tracker files.
  """
  parallel_tracker_file_path = get_tracker_file_path(
      destination_url, TrackerFileType.SLICED_DOWNLOAD)
  tracker_file_paths = [parallel_tracker_file_path]
  number_components = 0

  tracker_file = None
  try:
    tracker_file = files.FileReader(parallel_tracker_file_path)
    number_components = json.load(tracker_file)['number_components']
  except (FileNotFoundError, ValueError):
    return tracker_file_paths
  finally:
    if tracker_file:
      tracker_file.close()

  for i in range(number_components):
    tracker_file_paths.append(
        get_tracker_file_path(
            destination_url,
            TrackerFileType.DOWNLOAD_COMPONENT,
            component_number=i))

  return tracker_file_paths


def delete_tracker_file(tracker_file_path):
  """Deletes tracker file if it exists."""
  if tracker_file_path and os.path.exists(tracker_file_path):
    os.remove(tracker_file_path)


def delete_download_tracker_files(destination_url):
  """Deletes all tracker files for an object download.

  Args:
    destination_url (storage_url.StorageUrl): Describes the destination file.
  """
  # Delete non-sliced download tracker file.
  delete_tracker_file(
      get_tracker_file_path(destination_url, TrackerFileType.DOWNLOAD))

  # Delete all sliced download tracker files.
  tracker_files = get_sliced_download_tracker_file_paths(destination_url)
  for tracker_file in tracker_files:
    delete_tracker_file(tracker_file)


def get_download_start_byte():
  # TODO (http://b/176977838): Implement rest of tracker file utils.
  raise NotImplementedError


def read_or_create_download_tracker_file():
  # TODO (http://b/176977838): Implement rest of tracker file utils.
  raise NotImplementedError


def write_download_component_tracker_file():
  # TODO (http://b/176977838): Implement rest of tracker file utils.
  raise NotImplementedError
