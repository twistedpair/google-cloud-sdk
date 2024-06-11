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
"""Utils for cluster maintenance window commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.edge_cloud.container import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.run import flags


def ClearMaxUnavailable(ref, args, request):
  """Clears max_unavailable_worker_nodes in the request.

  If --clear-max-unavailable-worker-nodes flag is specified,
  cluster.upgrade_settings.max_unavailable_worker_nodes is cleared.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued.

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "clear_max_unavailable_worker_nodes"):
    return request

  if not args.clear_max_unavailable_worker_nodes:
    raise exceptions.BadArgumentException(
        "--no-clear-max-unavailable-worker-nodes", "The flag is not supported"
    )

  if request.cluster is None:
    release_track = args.calliope_command.ReleaseTrack()
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  if request.cluster.upgradeSettings is not None:
    request.cluster.upgradeSettings = None

  _AddFieldToUpdateMask(
      "upgrade_settings.max_unavailable_worker_nodes", request
  )
  return request


def _AddFieldToUpdateMask(field, request):
  if not request.updateMask:
    request.updateMask = field
    return request

  if field not in request.updateMask:
    request.updateMask = request.updateMask + "," + field
  return request
