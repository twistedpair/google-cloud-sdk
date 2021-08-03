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
"""Hashing utilities for storage commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import enum
import os

from googlecloudsdk.command_lib import info_holder
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.util import crc32c
from googlecloudsdk.core.updater import installers
from googlecloudsdk.core.util import hashing


class HashAlgorithm(enum.Enum):
  """Algorithms available for hashing data."""

  MD5 = 'md5'
  CRC32C = 'crc32c'


def get_base64_hash_digest_string(hash_object):
  """Takes hashlib object and returns base64-encoded digest as string."""
  return base64.b64encode(hash_object.digest()).decode(encoding='utf-8')


def get_hash_from_file_stream(file_stream,
                              hash_algorithm,
                              start=None,
                              stop=None):
  """Reads file and returns its hash object.

  core.util.files.Checksum does similar things but is different enough to merit
  this function. The primary differences are that this function:
  -Uses a FIPS-safe MD5 object.
  -Resets stream after consuming.
  -Supports start and end index to set byte range for hashing.

  Args:
    file_stream (stream): File to read.
    hash_algorithm (HashAlgorithm): Algorithm to hash file with.
    start (int): Byte index to start hashing at.
    stop (int): Stop hashing at this byte index.

  Returns:
    String of base64-encoded hash digest for file.
  """
  if hash_algorithm == HashAlgorithm.MD5:
    hash_object = hashing.get_md5()
  elif hash_algorithm == HashAlgorithm.CRC32C:
    hash_object = crc32c.get_crc32c()
  else:
    return

  if start:
    file_stream.seek(start)
  while True:
    if stop and file_stream.tell() >= stop:
      break

    # Avoids holding all of file in memory at once.
    if stop is None or file_stream.tell() + installers.WRITE_BUFFER_SIZE < stop:
      bytes_to_read = installers.WRITE_BUFFER_SIZE
    else:
      bytes_to_read = stop - file_stream.tell()

    data = file_stream.read(bytes_to_read)
    if not data:
      break

    if isinstance(data, str):
      # read() can return strings or bytes. Hash objects need bytes.
      data = data.encode('utf-8')
    # Compresses each piece of added data.
    hash_object.update(data)

  # Hashing the file consumes the stream, so reset to avoid giving the
  # caller of this function any confusing bugs.
  file_stream.seek(0)

  return hash_object


def validate_object_hashes_match(object_path, source_hash, destination_hash):
  """Confirms hashes match for copied objects.

  Args:
    object_path (str): URL of object being validated.
    source_hash (str): Hash of source object.
    destination_hash (str): Hash of destination object.

  Raises:
    HashMismatchError: Hashes are not equal.
  """
  if source_hash != destination_hash:
    raise errors.HashMismatchError(
        'Source hash {} does not match destination hash {}'
        ' for object {}.'.format(source_hash, destination_hash, object_path))


def update_digesters(digesters, data):
  """Updates every hash object with new data in a dict of digesters."""
  for hash_object in digesters.values():
    hash_object.update(data)


def copy_digesters(digesters):
  """Returns copy of provided digesters since deepcopying doesn't work."""
  result = {}
  for hash_algorithm in digesters:
    result[hash_algorithm] = digesters[hash_algorithm].copy()
  return result


def reset_digesters(digesters):
  """Clears the data from every hash object in a dict of digesters."""
  for hash_algorithm in digesters:
    if hash_algorithm is HashAlgorithm.MD5:
      digesters[hash_algorithm] = hashing.get_md5()
    elif hash_algorithm is HashAlgorithm.CRC32C:
      digesters[hash_algorithm] = crc32c.get_crc32c()
    else:
      raise ValueError('Unknown hash algorithm found in digesters: {}'.format(
          hash_algorithm))


def get_google_crc32c_install_command():
  """Returns the command to install google-crc32c library."""
  sdk_info = info_holder.InfoHolder()
  sdk_root = sdk_info.installation.sdk_root
  if sdk_root:
    third_party_path = os.path.join(sdk_root, 'lib', 'third_party')
    return '{} -m pip install google-crc32c --target {}'.format(
        sdk_info.basic.python_location, third_party_path)
