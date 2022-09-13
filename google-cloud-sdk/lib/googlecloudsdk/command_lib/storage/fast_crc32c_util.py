# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utilities that augment the core CRC32C functionality for storage commands.

The core CRC32C utility provides a hashlib-like functionality for CRC32C
calculation but will at times fall back to a slow, all-Python implementation.
This utility provides several mitigation strategies to avoid relying on the slow
implementation of CRC32C, including adding a "deferred" strategy that uses the
component gcloud-crc32c on files after they are downloaded.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import struct

from googlecloudsdk.command_lib import info_holder
from googlecloudsdk.command_lib.util import crc32c
# TODO(b/243537215) Should be loaded from a more generic location
from googlecloudsdk.command_lib.util.anthos import binary_operations
from googlecloudsdk.core import properties


BINARY_NAME = 'gcloud-crc32c'


class GcloudCrc32cOperation(binary_operations.BinaryBackedOperation):
  """Operation for hashing a file using gcloud-crc32c."""

  def __init__(self, **kwargs):
    super(GcloudCrc32cOperation, self).__init__(binary=BINARY_NAME, **kwargs)

  def _ParseArgsForCommand(self, file_path, offset=0, length=0, **kwargs):
    return ['-o', str(offset), '-l', str(length), file_path]


class DeferredCrc32c(object):
  """Hashlib-like helper for deferring hash calculations to gcloud-crc32c.

  NOTE: Given this class relies on analyzing data on disk, it is not appropriate
  for hashing streaming downloads and will fail to work as expected.
  """

  def __init__(self, crc=0):
    """Sets up the internal checksum variable and allows an initial value.

    Args:
      crc (int): The initial checksum to be stored.
    """
    self._crc = crc

  def copy(self):
    return DeferredCrc32c(crc=self._crc)

  def update(self, data):
    # Does nothing so hash calculation can be deferred to sum_file.
    del data  # Unused.
    return

  def sum_file(self, file_path, offset, length):
    """Calculates checksum on a provided file path.

    Args:
      file_path (str): A string representing a path to a file.
      offset (int): The number of bytes to offset from the beginning of the
        file. Defaults to 0.
      length (int): The number of bytes to read into the file. If not specified
        will calculate until the end of file is encountered.
    """
    crc32c_operation = GcloudCrc32cOperation()
    result = crc32c_operation(file_path=file_path, offset=offset, length=length)
    self._crc = 0 if result.failed else int(result.stdout)

  def digest(self):
    """Returns the checksum in big-endian order, per RFC 4960.

    See: https://cloud.google.com/storage/docs/json_api/v1/objects#crc32c

    Returns:
      An eight-byte digest string.
    """
    return struct.pack('>L', self._crc)

  def hexdigest(self):
    """Returns a checksum like `digest` except as a bytestring of double length.

    Returns:
      A sixteen byte digest string, containing only hex digits.
    """
    return '{:08x}'.format(self._crc).encode('ascii')


def _is_gcloud_crc32c_installed():
  """Returns True if gcloud-crc32c is installed, otherwise tries to install."""
  is_preferred = properties.VALUES.storage.use_gcloud_crc32c.GetBool()
  no_preference = is_preferred is None
  install_if_missing = is_preferred or no_preference
  try:
    return BINARY_NAME in binary_operations.CheckForInstalledBinary(
        BINARY_NAME, install_if_missing=install_if_missing)
  except binary_operations.MissingExecutableException:
    # If install_if_missing is True, either the user has access to gcloud
    # components but opted not to install or the user doesn't have access to the
    # gcloud components manager.
    if install_if_missing:
      # This will prevent automatic installation in the future, but it won't
      # prevent gcloud-crc32c from being used if later installed separately.
      properties.VALUES.storage.use_gcloud_crc32c.Set(False)
  except:  # pylint: disable=bare-except
    # Other errors that happen during installation checks aren't fatal.
    pass
  return False


def is_fast_crc32c_available():
  return crc32c.IS_FAST_GOOGLE_CRC32C_AVAILABLE or _is_gcloud_crc32c_installed()


def _should_use_gcloud_crc32c(is_installed, is_crc32c_slow, is_preferred):
  """Returns True if gcloud-crc32c should be used and installs if needed.

  Args:
    is_installed (bool): Whether gcloud-crc32c is installed.
    is_crc32c_slow (bool): Whether google-crc32c is missing.
    is_preferred (bool): Whether gcloud-crc32c is preferred.

  Returns:
    True if the Go binary gcloud-crc32c should be used.
  """
  no_preference = is_preferred is None
  if is_installed:
    if is_crc32c_slow:
      return True
    else:
      return False if no_preference else is_preferred
  return False


def get_crc32c(initial_data=b''):
  """Wraps the crc32c.get_crc32c() method to allow fallback to gcloud-crc32c.

  DO NOT USE for streaming downloads, as this relies in file-based hashing and
  does not take whether or not streaming is enabled into account.

  Args:
    initial_data (bytes): The CRC32C object will be initialized with the
      checksum of the data.

  Returns:
    A DeferredCrc32c instance if hashing can be deferred. Otherwise it returns a
    google_crc32c.Checksum instance if google-crc32c
    (https://github.com/googleapis/python-crc32c) is available and a
    predefined.Crc instance from crcmod library if not.
  """
  should_defer = _should_use_gcloud_crc32c(
      is_installed=_is_gcloud_crc32c_installed(),
      is_crc32c_slow=not crc32c.IS_FAST_GOOGLE_CRC32C_AVAILABLE,
      is_preferred=properties.VALUES.storage.use_gcloud_crc32c.GetBool())
  return DeferredCrc32c() if should_defer else crc32c.get_crc32c(initial_data)


def get_google_crc32c_install_command():
  """Returns the command to install google-crc32c library.

  This will typically only be called if gcloud-crc32c is missing and can't be
  installed for some reason. It requires user intervention which is why it's
  not a preferred option.
  """
  sdk_info = info_holder.InfoHolder()
  sdk_root = sdk_info.installation.sdk_root
  if sdk_root:
    third_party_path = os.path.join(sdk_root, 'lib', 'third_party')
    return '{} -m pip install google-crc32c --upgrade --target {}'.format(
        sdk_info.basic.python_location, third_party_path)
  return None
