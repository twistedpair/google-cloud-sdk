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
"""Helpers for calculating CRC32C checksums."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

import six

# pylint: disable=g-import-not-at-top
try:
  # TODO(b/175725675) Make google_crc32c available with Cloud SDK.
  import google_crc32c
  IS_GOOGLE_CRC32C_AVAILABLE = True
except ImportError:
  import gcloud_crcmod as crcmod
  IS_GOOGLE_CRC32C_AVAILABLE = False
  print('using crcmod')
# pylint: enable=g-import-not-at-top


def get_crc32c():
  """Returns an instance of Hashlib-like helper for CRC32C operations.

  Returns:
    The google_crc32c.Checksum instance
    if google-crc32c (https://github.com/googleapis/python-crc32c) is
    available. If not, returns the predefined.Crc instance from crcmod library.

  Usage:
    # Get the instance.
    crc = get_crc32c()
    # Update the instance with data. If your data is available in chunks,
    # you can update each chunk so that you don't have to keep everything in
    # memory.
    for chunk in chunks:
      crc.update(data)
    # Get the digest.
    crc_digest = crc.digest()

  """
  if IS_GOOGLE_CRC32C_AVAILABLE:
    return google_crc32c.Checksum()
  return crcmod.predefined.Crc('crc-32c')


def get_crc32c_checksum(data):
  """Calculates the CRC32C checksum of the provided data.

  Args:
    data (bytes): The bytes over which the checksum should be calculated.

  Returns:
    An int representing the CRC32C checksum of the provided bytes.
  """
  crc = get_crc32c()
  crc.update(six.ensure_binary(data))
  return int(crc.hexdigest(), 16)


def get_crc32c_hash(data):
  """Calculates the CRC32C hash for the provided data.

  This returns the base64 encoded version of the CRC32C digest, which is handy
  for GCS objects which store the CRC32C Hash in this format.

  Args:
    data (bytes): Bytes over which the hash should be calculated.

  Returns:
    A string represnting the base64 encoded CRC32C hash.
  """
  crc = get_crc32c()
  crc.update(six.ensure_binary(data))
  return base64.b64encode(crc.digest()).decode('ascii')


def does_crc32c_checksum_match(data, data_crc32c_checksum):
  """Checks if checksum for the data matches the supplied checksum.

  Args:
    data (bytes): Bytes over which the checksum should be calculated.
    data_crc32c_checksum (int): Checksum against which data's checksum will be
      compared.

  Returns:
    True iff both checksums match.
  """
  return get_crc32c_checksum(data) == data_crc32c_checksum
