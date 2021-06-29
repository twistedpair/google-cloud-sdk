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

"""Utility functions for performing upload operation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import mimetypes
import subprocess

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import hash_util
from googlecloudsdk.command_lib.storage.tasks.rm import delete_object_task
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import platforms
from googlecloudsdk.core.util import scaled_integer


COMMON_EXTENSION_RULES = {
    '.md': 'text/markdown',  # b/169088193
    '.tgz': 'application/gzip',  # b/179176339
}


def get_upload_strategy(api, object_length):
  """Determines if resumbale uplaod should be performed.

  Args:
    api (CloudApi): An api instance to check if it supports resumable upload.
    object_length (int): Length of the data to be uploaded.

  Returns:
    bool: True if resumable upload can be performed.
  """
  resumable_threshold = scaled_integer.ParseInteger(
      properties.VALUES.storage.resumable_threshold.Get())
  if (object_length >= resumable_threshold and
      cloud_api.Capability.RESUMABLE_UPLOAD in api.capabilities):
    return cloud_api.UploadStrategy.RESUMABLE
  else:
    return cloud_api.UploadStrategy.SIMPLE


def get_content_type(file_resource):
  """Gets a file's MIME type.

  Favors returning the result of `file -b --mime ...` if the command is
  available and users have enabled it. Otherwise, it returns a type based on the
  file's extension.

  Args:
    file_resource (resource_reference.FileObjectResource): The file to return a
      type for.

  Returns:
    A MIME type (str).
    If a type cannot be guessed, DEFAULT_CONTENT_TYPE is returned.
  """
  path = file_resource.storage_url.object_name

  # Some common extensions are not recognized by the mimetypes library and
  # "file" command, so we'll hard-code support for them.
  for extension, content_type in COMMON_EXTENSION_RULES.items():
    if path.endswith(extension):
      return content_type

  if (not platforms.OperatingSystem.IsWindows() and
      properties.VALUES.storage.use_magicfile.GetBool()):
    output = subprocess.run(['file', '-b', '--mime', path],
                            check=True,
                            stdout=subprocess.PIPE,
                            universal_newlines=True)
    content_type = output.stdout.strip()
  else:
    content_type, _ = mimetypes.guess_type(path)
  if content_type:
    return content_type
  return request_config_factory.DEFAULT_CONTENT_TYPE


def validate_uploaded_object(digesters, uploaded_resource, task_status_queue):
  """Raises error if hashes for uploaded_resource and digesters do not match."""
  if not digesters:
    return
  calculated_digest = hash_util.get_base64_hash_digest_string(
      digesters[hash_util.HashAlgorithm.MD5])
  try:
    hash_util.validate_object_hashes_match(
        uploaded_resource.storage_url, calculated_digest,
        uploaded_resource.md5_hash)
  except errors.HashMismatchError:
    delete_object_task.DeleteObjectTask(uploaded_resource.storage_url).execute(
        task_status_queue=task_status_queue)
    raise
