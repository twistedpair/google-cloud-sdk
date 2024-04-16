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


def RequestWithNewMaintenanceExclusion(req, messages, args):
  """Returns an update request with a new maintenance exclusion window with id, start time, and end time specified from args.

  Args:
    req: API request to be issued.
    messages: message module of edgecontainer cluster.
    args: command line arguments.

  Returns:
    modified request
  """
  if req.cluster.maintenancePolicy is None:
    req.cluster.maintenancePolicy = messages.MaintenancePolicy()
  if req.cluster.maintenancePolicy.maintenanceExclusions is None:
    req.cluster.maintenancePolicy.maintenanceExclusions = []

  req.cluster.maintenancePolicy.maintenanceExclusions.append(
      messages.MaintenanceExclusionWindow(
          id=args.add_maintenance_exclusion_name,
          window=messages.TimeWindow(
              startTime=args.add_maintenance_exclusion_start,
              endTime=args.add_maintenance_exclusion_end,
          ),
      )
  )
  return req


def AddMaintenanceExclusionWindow(ref, args, request):
  """Adds a maintenance exclusion window to the cluster if relevant flags are set.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """
  del ref  # unused argument
  # If none are set, pass through original request.
  if (
      not flags.FlagIsExplicitlySet(args, "add_maintenance_exclusion_name")
      and not flags.FlagIsExplicitlySet(args, "add_maintenance_exclusion_start")
      and not flags.FlagIsExplicitlySet(args, "add_maintenance_exclusion_end")
  ):
    return request

  # If at least one of them is set, ensure all flags exist.
  _CheckAddMaintenanceExclusionFlags(args)

  release_track = args.calliope_command.ReleaseTrack()
  if request.cluster is None:
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  # Ensure the MEW name doesn't already exist
  if request.cluster.maintenancePolicy:
    for mew in request.cluster.maintenancePolicy.maintenanceExclusions:
      if args.add_maintenance_exclusion_name == mew.id:
        raise exceptions.BadArgumentException(
            "--add-maintenance-exclusion-name",
            "Maintenance exclusion name " + mew.id + " already exists.",
        )

  request = RequestWithNewMaintenanceExclusion(
      request, util.GetMessagesModule(release_track), args
  )
  _AddFieldToUpdateMask("maintenancePolicy", request)
  return request


def _CheckAddMaintenanceExclusionFlags(args):
  """Confirms all necessary flags for adding an exclusion window is set.

  Args:
    args: arguments passed through gcloud command

  Raises:
    BadArgumentException specifying missing flag
  """
  if not args.add_maintenance_exclusion_name:
    raise exceptions.BadArgumentException(
        "--add-maintenance-exclusion-name",
        "Every maintenance exclusion window must have a name.",
    )
  if not args.add_maintenance_exclusion_start:
    raise exceptions.BadArgumentException(
        "--add-maintenance-exclusion-start",
        "Every maintenance exclusion window must have a start time.",
    )
  if not args.add_maintenance_exclusion_end:
    raise exceptions.BadArgumentException(
        "--add-maintenance-exclusion-end",
        "Every maintenance exclusion window must have an end time.",
    )


def RemoveMaintenanceExclusionWindow(ref, args, request):
  """Removes the cluster.maintenance_policy.maintenance_exclusion_window if --remove-maintenance-exclusion-window flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "remove_maintenance_exclusion_window"):
    return request

  if request.cluster is None:
    release_track = args.calliope_command.ReleaseTrack()
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  if request.cluster.maintenancePolicy is None:
    _AddFieldToUpdateMask("maintenancePolicy", request)
    return request

  for idx, mew in enumerate(
      request.cluster.maintenancePolicy.maintenanceExclusions
  ):
    if mew.id == args.remove_maintenance_exclusion_window:
      i = idx
      break
  else:
    raise exceptions.BadArgumentException(
        "--remove-maintenance-exclusion-window",
        "Cannot remove a maintenance exclusion window that doesn't exist.",
    )

  del request.cluster.maintenancePolicy.maintenanceExclusions[i]

  _AddFieldToUpdateMask("maintenancePolicy", request)
  return request


def ClearMaintenanceWindow(ref, args, request):
  """Clears cluster.maintenance_policy.window in the request if --clear-maintenance-window flag is specified.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "clear_maintenance_window"):
    return request

  if not args.clear_maintenance_window:
    raise exceptions.BadArgumentException(
        "--no-clear-maintenance-window", "The flag is not supported"
    )
  if request.cluster is None:
    release_track = args.calliope_command.ReleaseTrack()
    request.cluster = util.GetMessagesModule(release_track).Cluster()
  if request.cluster.maintenancePolicy:
    if request.cluster.maintenancePolicy.maintenanceExclusions:
      raise exceptions.BadArgumentException(
          "--clear-maintenance-window",
          "Cannot clear a maintenance window if there are maintenance"
          " exclusions.",
      )
  request.cluster.maintenancePolicy = None

  _AddFieldToUpdateMask("maintenancePolicy", request)
  return request


def _AddFieldToUpdateMask(field, request):
  if not request.updateMask:
    request.updateMask = field
    return request

  if field not in request.updateMask:
    request.updateMask = request.updateMask + "," + field
  return request
