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
"""POSIX utilities for storage commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import datetime
import os
import stat

from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.command_lib.storage.tasks import task_util
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms

SETTING_INVALID_POSIX_ERROR = ValueError(
    'Setting preserved POSIX data will result in invalid file metadata.')

_MISSING_UID_FORMAT = (
    "UID in {} metadata doesn't exist on current system. UID: {}")
_MISSING_GID_FORMAT = (
    "GID in {} metadata doesn't exist on current system. GID: {}")
_INSUFFICIENT_USER_READ_ACCESS_FORMAT = (
    'Insufficient access to local destination to copy {}. User {} owns'
    ' file, but owner does not have read permission in mode {}.')
_INSUFFICIENT_GROUP_READ_ACCESS_FORMAT = (
    'Insufficient access to local destination to copy {}. Group {}'
    ' would own file, but group does not have read permission in mode {}.')
_INSUFFICIENT_OTHER_READ_ACCESS_FORMAT = (
    'Insufficient access to local destination to copy {}. UID {} is not'
    ' owner of file, and user is not in a group that owns the file. Users in'
    ' "other" category do not have read permission in mode {}.')

# For transporting POSIX info through an object's custom metadata.
_ATIME_METADATA_KEY = 'goog-reserved-file-atime'
_GID_METADATA_KEY = 'goog-reserved-posix-gid'
_MODE_METADATA_KEY = 'goog-reserved-posix-mode'
_MTIME_METADATA_KEY = 'goog-reserved-file-mtime'
_UID_METADATA_KEY = 'goog-reserved-posix-uid'


def convert_base_ten_to_base_eight_str(base_ten_int):
  """Takes base ten integer, converts to octal, and removes extra chars."""
  # Example: 73 -> '0o111' -> '111'.
  # Remove leading '0o'.
  oct_string = oct(base_ten_int)[2:]
  # Take trailing three digits. For example, '0' -> '0' or '123' -> '11123'.
  permission_bytes = oct_string[-3:]
  # Add leading zero padding. For example, '1' -> '001'.
  return '0' * (3 - len(permission_bytes)) + permission_bytes


def convert_base_eight_str_to_base_ten_int(base_eight_str):
  """Takes string representing integer in octal and converts to base ten int."""
  # Example: '111' -> 73.
  return int(base_eight_str, 8)


class PosixMode:
  """Stores POSIX mode in all useful formats."""

  def __init__(self, base_ten_int, base_eight_str):
    """Initializes class. Prefer the 'from' constructors below."""
    self.base_ten_int = base_ten_int
    self.base_eight_str = base_eight_str

  @classmethod
  def from_base_ten_int(cls, base_ten_int):
    """Initializes class from base ten int. E.g. 73."""
    base_eight_str = convert_base_ten_to_base_eight_str(base_ten_int)
    # Not using original base_ten_int because str version removes unwanted bits.
    return PosixMode(
        convert_base_eight_str_to_base_ten_int(base_eight_str), base_eight_str)

  @classmethod
  def from_base_eight_str(cls, base_eight_str):
    """Initializes class from base eight (octal) string. E.g. '111'."""
    return PosixMode(
        convert_base_eight_str_to_base_ten_int(base_eight_str), base_eight_str)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    return (self.base_ten_int == other.base_ten_int and
            self.base_eight_str == other.base_eight_str)

  def __repr__(self):
    return '(base-ten int: {}, base-eight str: {})'.format(
        self.base_ten_int, self.base_eight_str)


# Holds system-wide POSIX information.
#
# Attributes:
#   default_mode (PosixMode): The default permissions assigned to files.
#   user_groups (set): The set of Unix groups the user belongs to. Should
#     include one primary group and a variable number of secondary groups.
SystemPosixData = collections.namedtuple('SystemPosixData',
                                         ['default_mode', 'user_groups'])


def _get_default_mode():
  """Gets default permissions files are created with as PosixMode object."""
  # umask returns the permissions that should not be granted, so they must be
  # subtracted from the maximum set of permissions.
  max_permissions = 0o777
  # This call temporarily sets the process's umask to 177 while fetching the
  # the default umask. Not thread-safe. Run only in places where concurrent
  # file operations are not possible like a command surface.
  current_umask = os.umask(0o177)
  # Reset to the default umask.
  os.umask(current_umask)
  mode = max_permissions - current_umask
  # Files are not given execute privileges by default. Therefore we need to
  # subtract one from every odd permissions value. This is done via a bitmask.
  mode_without_execution = mode & 0o666
  return PosixMode.from_base_ten_int(mode_without_execution)


def _get_user_groups():
  """Gets set of POSIX groups the user is part of."""
  # POSIX modules and os.getuid not available on Windows.
  # pylint:disable=g-import-not-at-top
  import grp
  import pwd
  # pylint:enable=g-import-not-at-top
  user_id = os.getuid()
  user_name = pwd.getpwuid(user_id).pw_name
  return set(
      # Primary group.
      [pwd.getpwuid(user_id).pw_gid] +
      # Secondary groups.
      [g.gr_gid for g in grp.getgrall() if user_name in g.gr_mem])


def get_system_posix_data():
  """Gets POSIX info that should only be fetched once."""
  if platforms.OperatingSystem.IsWindows():
    return SystemPosixData(None, None)

  default_mode = _get_default_mode()
  user_groups = _get_user_groups()
  return SystemPosixData(default_mode, user_groups)


def are_file_permissions_valid(url_string,
                               system_posix_data,
                               posix_attributes=None):
  """Checks if setting permissions on a file results in a valid accessible file.

  Logs explanatory error if copy will result in invalid file.

  Args:
    url_string (str): URL of source object being considered for copy.
    system_posix_data (SystemPosixData): Relevant default system settings.
    posix_attributes (PosixAttributes|None): POSIX metadata being considered to
      set on file.

  Returns:
    bool: True if copy will result in a valid file.
  """
  uid = getattr(posix_attributes, 'uid', None)
  gid = getattr(posix_attributes, 'gid', None)
  mode = getattr(posix_attributes, 'mode', None)
  if (uid is gid is mode is None) or platforms.OperatingSystem.IsWindows():
    # If the user isn't setting anything, the system's new file defaults
    # are used, which we assume are valid.
    # Windows doesn't use POSIX for file permissions, so files will validate.
    return True

  # POSIX modules, os.geteuid, and os.getuid not available on Windows.
  if os.geteuid() == 0:
    # The root user can access files regardless of their permissions.
    return True

  # pylint:disable=g-import-not-at-top
  import grp
  import pwd
  # pylint:enable=g-import-not-at-top

  if uid is not None:
    try:
      pwd.getpwuid(uid)
    except KeyError:
      log.error(_MISSING_UID_FORMAT.format(url_string, uid))
      return False
  if gid is not None:
    try:
      grp.getgrgid(gid)
    except (KeyError, OverflowError):
      log.error(_MISSING_GID_FORMAT.format(url_string, gid))
      return False

  if mode is None:
    mode_to_set = system_posix_data.default_mode
  else:
    mode_to_set = mode

  uid_to_set = uid or os.getuid()
  if uid is None or uid == os.getuid():
    # No UID causes system to default to current user as owner.
    # Owner permissions take priority over group and "other".
    if mode_to_set.base_ten_int & stat.S_IRUSR:
      return True
    log.error(
        _INSUFFICIENT_USER_READ_ACCESS_FORMAT.format(
            url_string, uid_to_set, mode_to_set.base_eight_str))
    return False

  if gid is None or gid in system_posix_data.user_groups:
    # No GID causes system to create file owned by user's primary group.
    # Group permissions take priority over "other" if user is member of group.
    if mode_to_set.base_ten_int & stat.S_IRGRP:
      return True

    log.error(
        _INSUFFICIENT_GROUP_READ_ACCESS_FORMAT.format(
            url_string, '[user primary group]' if gid is None else gid,
            mode_to_set.base_eight_str))
    return False

  if mode_to_set.base_ten_int & stat.S_IROTH:
    # User is not owner and not in relevant group. User is "other".
    return True
  log.error(
      _INSUFFICIENT_OTHER_READ_ACCESS_FORMAT.format(url_string, uid_to_set,
                                                    mode_to_set.base_eight_str))
  return False


# Holds custom POSIX information we may extract or apply to a file.
#
# "None" values typically mean using the system default.
#
# Attributes:
#   atime (int|None): File's access time in seconds since epoch.
#   mtime (int|None): File's modification time in seconds since epoch.
#   uid (int|None): The user ID marked as owning the file.
#   gid (int|None): The group ID marked as owning the file.
#   mode (PosixMode|None): Access permissions for the file.
PosixAttributes = collections.namedtuple(
    'PosixAttributes', ['atime', 'mtime', 'uid', 'gid', 'mode'])


def get_posix_attributes_from_file(file_path):
  """Takes file path and returns PosixAttributes object."""
  mode, _, _, _, uid, gid, _, atime, mtime, _ = os.stat(file_path)
  return PosixAttributes(atime, mtime, uid, gid,
                         PosixMode.from_base_ten_int(mode))


def _set_posix_attributes_on_file(file_path, custom_posix_attributes):
  """Sets custom POSIX attributes on file.

  Call "after are_file_permissions_valid" function before running this.
  Raised errors may signify invalid metadata or missing permissions.

  Args:
    file_path (str): File to set custom POSIX attributes on.
    custom_posix_attributes (PosixAttributes): Metadata to set on file if valid.

  Raises:
    PermissionError: Custom metadata called for file ownership change that user
      did not have permission to perform. Other permission errors while calling
      OS functions are also possible.
  """
  existing_posix_attributes = get_posix_attributes_from_file(file_path)
  if custom_posix_attributes.atime is None or custom_posix_attributes.atime < 0:
    # Set only valid times on a file.
    atime = existing_posix_attributes.atime
  else:
    atime = custom_posix_attributes.atime
  if custom_posix_attributes.mtime is None or custom_posix_attributes.mtime < 0:
    mtime = existing_posix_attributes.mtime
  else:
    mtime = custom_posix_attributes.mtime

  os.utime(file_path, (atime, mtime))

  if platforms.OperatingSystem.IsWindows():
    # Windows does not use the remaining POSIX attributes.
    return

  if custom_posix_attributes.uid is None or custom_posix_attributes.uid < 0:
    # Allow only valid UIDs.
    uid = existing_posix_attributes.uid
  else:
    uid = custom_posix_attributes.uid

    if uid != existing_posix_attributes.uid and os.geteuid() != 0:
      # Custom may equal existing if user is uploading and downloading on the
      # same machine and account.
      raise PermissionError(
          'Root permissions required to set UID {}.'.format(uid))

  if custom_posix_attributes.gid is None or custom_posix_attributes.gid < 0:
    gid = existing_posix_attributes.gid
  else:
    gid = custom_posix_attributes.gid

  # Note: chown doesn't do anything for negative numbers like _INVALID_ID.
  os.chown(file_path, uid, gid)

  mode = custom_posix_attributes.mode or existing_posix_attributes.mode
  os.chmod(file_path, mode.base_ten_int)


def set_posix_attributes_on_file_if_valid(user_request_args, task_messages,
                                          source_resource,
                                          destination_resource):
  """Sets custom POSIX attributes on file if the final metadata will be valid.

  Args:
    user_request_args (user_request_args_factory._UserRequestArgs): Determines
      if user intended to preserve file POSIX data and get system-wide POSIX.
    task_messages (List[task.Message]): May carry preserved POSIX data to set
      from cloud object.
    source_resource (resource_reference.ObjectResource): Copy source.
    destination_resource (resource_reference.FileObjectResource): Copy
      destination.

  Raises:
    PermissionError: See _set_posix_attribute_on_file docstring.
    ValueError: From SETTING_INVALID_POSIX_ERROR, predetermined from metadata
      that preserving POSIX will result in corrupt file permissions.
  """
  if not (user_request_args and user_request_args.system_posix_data):
    # Check if user typed "--preserve-posix" flag.
    return
  posix_attributes = task_util.get_first_matching_message_payload(
      task_messages, task.Topic.API_DOWNLOAD_RESULT).posix_attributes
  destination_path = destination_resource.storage_url.object_name

  if not are_file_permissions_valid(source_resource.storage_url.url_string,
                                    user_request_args.system_posix_data,
                                    posix_attributes):
    os.remove(destination_path)
    raise SETTING_INVALID_POSIX_ERROR

  _set_posix_attributes_on_file(destination_path, posix_attributes)


def _extract_time_from_custom_metadata(url_string, key, metadata_dict):
  """Finds, validates, and returns a POSIX time value."""
  if key not in metadata_dict:
    return None
  try:
    timestamp = int(metadata_dict[key])
  except ValueError:
    log.warning('{} metadata did not contain a numeric value for {}: {}'.format(
        url_string, key, metadata_dict[key]))
    return None
  if timestamp < 0:
    log.warning('Found negative time value in {} metadata {}: {}'.format(
        url_string, key, metadata_dict[key]))
    return None
  if timestamp > datetime.datetime.now(datetime.timezone.utc).timestamp():
    log.warning('Found future time value in {} metadata {}: {}'.format(
        url_string, key, metadata_dict[key]))
    return None
  return timestamp


def _extract_id_from_custom_metadata(url_string, key, metadata_dict):
  """Finds, validates, and returns a POSIX ID value."""
  if key not in metadata_dict:
    return None
  try:
    posix_id = int(metadata_dict[key])
  except ValueError:
    log.warning('{} metadata did not contain a numeric value for {}: {}'.format(
        url_string, key, metadata_dict[key]))
    return None
  if posix_id < 0:
    log.warning('Found negative ID value in {} metadata {}: {}'.format(
        url_string, key, metadata_dict[key]))
    return None
  return posix_id


def _extract_mode_from_custom_metadata(url_string, metadata_dict):
  """Finds, validates, and returns a POSIX mode value."""
  if _MODE_METADATA_KEY not in metadata_dict:
    return None
  try:
    return PosixMode.from_base_eight_str(metadata_dict[_MODE_METADATA_KEY])
  except ValueError:
    log.warning('{} metadata did not contain a valid permissions octal string'
                ' for {}: {}'.format(url_string, _MODE_METADATA_KEY,
                                     metadata_dict[_MODE_METADATA_KEY]))
  return None


def get_posix_attributes_from_custom_metadata_dict(url_string, metadata_dict):
  """Parses metadata_dict and returns PosixAttributes.

  GCS Apitools custom metadata can be converted to a metadata_dict with
  "encoding_helper.MessageToDict(object_metadata.metadata)". S3 already
  stores its object custom metadata as a dict.

  Note: This is the dict of an object's *custom* metadata with user-set fields,
  not all object metadata with provider-set fields.

  Args:
    url_string (str): File or object path for logging warning.
    metadata_dict (dict): Contains user-set fields where POSIX info may be.

  Returns:
    PosixAttributes object populated from metadata_dict.
  """
  atime = _extract_time_from_custom_metadata(url_string, _ATIME_METADATA_KEY,
                                             metadata_dict)
  mtime = _extract_time_from_custom_metadata(url_string, _MTIME_METADATA_KEY,
                                             metadata_dict)
  uid = _extract_id_from_custom_metadata(url_string, _UID_METADATA_KEY,
                                         metadata_dict)
  gid = _extract_id_from_custom_metadata(url_string, _GID_METADATA_KEY,
                                         metadata_dict)
  mode = _extract_mode_from_custom_metadata(url_string, metadata_dict)
  return PosixAttributes(atime, mtime, uid, gid, mode)


def update_custom_metadata_dict_with_posix_attributes(metadata_dict,
                                                      posix_attributes):
  """Updates custom metadata_dict with PosixAttributes data."""
  if posix_attributes.atime is not None:
    metadata_dict[_ATIME_METADATA_KEY] = str(posix_attributes.atime)
  if posix_attributes.mtime is not None:
    metadata_dict[_MTIME_METADATA_KEY] = str(posix_attributes.mtime)
  if posix_attributes.uid is not None:
    metadata_dict[_UID_METADATA_KEY] = str(posix_attributes.uid)
  if posix_attributes.gid is not None:
    metadata_dict[_GID_METADATA_KEY] = str(posix_attributes.gid)
  if posix_attributes.mode is not None:
    metadata_dict[_MODE_METADATA_KEY] = posix_attributes.mode.base_eight_str


def raise_if_source_and_destination_not_valid_for_preserve_posix(
    source_url, destination_url, user_request_args=None):
  """Logs errors and returns bool indicating if transfer is valid for POSIX."""
  if not (user_request_args and user_request_args.system_posix_data):
    return

  if isinstance(source_url, storage_url.FileUrl) and source_url.is_stream:
    raise ValueError(
        'Cannot preserve POSIX data from pipe: {}'.format(source_url))
  if isinstance(destination_url,
                storage_url.FileUrl) and destination_url.is_stream:
    raise ValueError(
        'Cannot write POSIX data to pipe: {}'.format(destination_url))
  if isinstance(source_url, storage_url.CloudUrl) and isinstance(
      destination_url, storage_url.CloudUrl):
    raise ValueError('Cannot preserve POSIX data for cloud-to-cloud copies')
