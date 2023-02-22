# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utils for the rsync command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import posix_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import resource_reference

import six


def get_csv_line_from_resource(resource):
  """Builds a line for files listing the contents of the source and destination.

  Args:
    resource (FileObjectResource|ObjectResource): Contains item URL and
      metadata, which can be generated from the local file in the case of
      FileObjectResource.

  Returns:
    String formatted as "URL,size,atime,mtime,uid,gid,mode,crc32c,md5".
      A missing field is represented as an empty string.
      "mtime" means "modification time", a Unix timestamp in UTC.
      "mode" is in base-eight (octal) form, e.g. "440".
  """
  url = resource.storage_url.url_string
  if isinstance(resource, resource_reference.FileObjectResource):
    size = atime = mtime = uid = gid = mode_base_eight = crc32c = md5 = None
  else:
    size = resource.size
    atime, mtime, uid, gid, mode = (
        posix_util.get_posix_attributes_from_resource(resource)
    )
    mode_base_eight = mode.base_eight_str if mode else None
    crc32c = resource.crc32c_hash
    md5 = resource.md5_hash
  line_values = [
      url,
      size,
      atime,
      mtime,
      uid,
      gid,
      mode_base_eight,
      crc32c,
      md5,
  ]
  return ','.join(['' if x is None else six.text_type(x) for x in line_values])


def parse_csv_line_to_resource(line):
  """Parses a line from files listing of rsync source and destination.

  Args:
    line (str): CSV line. See `get_csv_line_from_resource` docstring.

  Returns:
    FileObjectResource or ObjectResource containing data needed for rsync.
  """
  (
      url_string,
      size_string,
      atime_string,
      mtime_string,
      uid_string,
      gid_string,
      mode_base_eight_string,
      crc32c_string,
      md5_string,
  ) = line.split(',')
  url_object = storage_url.storage_url_from_string(url_string)
  if isinstance(url_object, storage_url.FileUrl):
    return resource_reference.FileObjectResource(url_object)
  cloud_object = resource_reference.ObjectResource(
      url_object,
      size=int(size_string),
      crc32c_hash=crc32c_string,
      md5_hash=md5_string,
      custom_fields={},
  )
  posix_util.update_custom_metadata_dict_with_posix_attributes(
      cloud_object.custom_fields,
      posix_util.PosixAttributes(
          atime=int(atime_string),
          mtime=int(mtime_string),
          uid=int(uid_string),
          gid=int(gid_string),
          mode=posix_util.PosixMode.from_base_eight_str(mode_base_eight_string),
      ),
  )
  return cloud_object
