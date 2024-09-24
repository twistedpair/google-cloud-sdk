# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utils for cluster maintenance window and maintenance exclusion window commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.edge_cloud.container import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.run import flags


def UpdateKmsKey(ref, args, request):
  """Updates the cluster.control_plane_encryption if --control-plane-kms-key flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "control_plane_kms_key"):
    return request

  release_track = args.calliope_command.ReleaseTrack()

  if request.cluster is None:
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  if request.cluster.controlPlaneEncryption is None:
    messages = util.GetMessagesModule(release_track)
    request.cluster.controlPlaneEncryption = messages.ControlPlaneEncryption()

  request.cluster.controlPlaneEncryption.kmsKey = args.control_plane_kms_key

  _AddFieldToUpdateMask("controlPlaneEncryption", request)
  return request


def UseGoogleManagedKey(ref, args, request):
  """Clears cluster.control_plane_encryption in the request if --use-google-managed-key flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "use_google_managed_key"):
    return request

  if not args.use_google_managed_key:
    raise exceptions.BadArgumentException(
        "--no-use-google-managed-key", "The flag is not supported"
    )
  # TODO(b/364915328): Will complete test this after flag is enabled in GA.
  if request.cluster is None:
    release_track = args.calliope_command.ReleaseTrack()
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  request.cluster.controlPlaneEncryption = None

  _AddFieldToUpdateMask("controlPlaneEncryption", request)
  return request


def UpdateZoneKmsKey(ref, args, request):
  """Updates the cluster.zone_storage_encryption if --zone-storage-kms-key flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "zone_storage_kms_key"):
    return request

  release_track = args.calliope_command.ReleaseTrack()

  if request.cluster is None:
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  if request.cluster.zoneStorageEncryption is None:
    messages = util.GetMessagesModule(release_track)
    request.cluster.zoneStorageEncryption = messages.ZoneStorageEncryption()

  request.cluster.zoneStorageEncryption.kmsKey = args.zone_storage_kms_key

  _AddFieldToUpdateMask("zoneStorageEncryption", request)
  return request


def UseGoogleManagedZoneKey(ref, args, request):
  """Clears cluster.zone_storage_encryption in the request if --use-google-managed-zone-key flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "use_google_managed_zone_key"):
    return request

  if not args.use_google_managed_zone_key:
    raise exceptions.BadArgumentException(
        "--no-use-google-managed-zone-key", "The flag is not supported"
    )

  if request.cluster is None:
    release_track = args.calliope_command.ReleaseTrack()
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  request.cluster.zoneStorageEncryption = None

  _AddFieldToUpdateMask("zoneStorageEncryption", request)
  return request


def _AddFieldToUpdateMask(field, request):
  if not request.updateMask:
    request.updateMask = field
    return request

  if field not in request.updateMask:
    request.updateMask = request.updateMask + "," + field
  return request
