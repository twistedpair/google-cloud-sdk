# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Bigtable backups API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.bigtable import util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.util import times


# General Utils
class NoFieldSpecified(core_exceptions.Error):
  """Error for calling update command with no args that represent fields."""


def ParseExpireTime(expiration_value):
  """Parse flag value into Datetime format for expireTime."""
  # expiration_value could be in Datetime format or Duration format.
  # backend timezone is UTC.
  datetime = times.ParseDuration(expiration_value).GetRelativeDateTime(
      times.Now(times.UTC)
  )
  parsed_datetime = times.FormatDateTime(
      datetime, '%Y-%m-%dT%H:%M:%S.%6f%Ez', tzinfo=times.UTC
  )
  return parsed_datetime


def FormatDatetime(datetime_value: str) -> str:
  """Parse a string datetime value into a formatted string."""
  parsed_time = arg_parsers.Datetime.ParseUtcTime(datetime_value)
  return parsed_time.strftime('%Y-%m-%dT%H:%M:%SZ')


# TODO: b/353357876 - We can replace both of these flags since we can represent
# both formats using gcloud's arg_parser.
def GetExpireTime(args):
  """Parse flags for expire time."""
  if args.expiration_date:
    return args.expiration_date
  elif args.retention_period:
    return ParseExpireTime(args.retention_period)


def GetHotToStandardTime(args):
  """Parse flags for hot to standard time."""
  if not args.hot_to_standard_time:
    return args.hot_to_standard_time

  return FormatDatetime(args.hot_to_standard_time)


# Create Command Utils
def ModifyCreateRequest(backup_ref, args, req):
  """Parse argument and construct create backup request."""
  req.backup.sourceTable = f'projects/{backup_ref.projectsId}/instances/{backup_ref.instancesId}/tables/{args.table}'

  req.backup.expireTime = GetExpireTime(args)
  req.backup.hotToStandardTime = GetHotToStandardTime(args)
  req.backupId = args.backup
  req.parent = backup_ref.Parent().RelativeName()
  return req


# Update Command Utils
def ResetDefaultMaskField(unused_instance_ref, unused_args, req):
  req.updateMask = ''
  return req


def AddFieldToUpdateMask(field, req):
  update_mask = req.updateMask
  if update_mask:
    if update_mask.count(field) == 0:
      req.updateMask = update_mask + ',' + field
  else:
    req.updateMask = field
  return req


def AddBackupFieldsToUpdateMask(unused_backup_ref, args, req):
  """Add backup fields to updateMask in the patch request."""
  expire_time = GetExpireTime(args)
  if expire_time is not None:
    req.backup.expireTime = expire_time
    req = AddFieldToUpdateMask('expire_time', req)

  hot_to_standard_time = GetHotToStandardTime(args)
  if hot_to_standard_time is not None:
    req = AddFieldToUpdateMask('hot_to_standard_time', req)
    # We don't have to explicitly check if `hot_to_standard_time` is an empty
    # string because even though it can also be None, we have already checked
    # that it is not None.
    #
    # `hot_to_standard_time` is a string flag, so this means that we can
    # simply check whether the flag is falsy to determine if it is an empty
    # string.
    #
    # An empty string means that the user wants to clear the
    # `hot_to_standard_time` field.
    if not hot_to_standard_time:
      req.backup.hotToStandardTime = None
    else:
      req.backup.hotToStandardTime = hot_to_standard_time

  return req


def CopyBackup(source_backup_ref, destination_backup_ref, args):
  """Copy a backup."""
  client = util.GetAdminClient()
  msgs = util.GetAdminMessages()
  copy_backup_request = msgs.CopyBackupRequest(
      backupId=destination_backup_ref.Name(),
      sourceBackup=source_backup_ref.RelativeName(),
  )
  copy_backup_request.expireTime = GetExpireTime(args)

  req = msgs.BigtableadminProjectsInstancesClustersBackupsCopyRequest(
      parent=destination_backup_ref.Parent().RelativeName(),
      copyBackupRequest=copy_backup_request,
  )
  return client.projects_instances_clusters_backups.Copy(req)
