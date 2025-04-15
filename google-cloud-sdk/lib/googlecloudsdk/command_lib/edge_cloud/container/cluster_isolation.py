# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utils for cluster isolation commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.edge_cloud.container import util
from googlecloudsdk.command_lib.run import flags


def UpdateClusterIsolation(ref, args, request):
  """Updates the Cluster Isolation mode.

  If --enable-cluster-isolation flag is specified, it will be used to
  update the Cluster Isolation mode.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued.

  Returns:
    modified request
  """

  del ref  # unused argument

  if not flags.FlagIsExplicitlySet(args, "enable_cluster_isolation"):
    return request

  release_track = args.calliope_command.ReleaseTrack()

  if request.cluster is None:
    request.cluster = util.GetMessagesModule(release_track).Cluster()

  if args.enable_cluster_isolation.upper() == "TRUE":
    request.cluster.enableClusterIsolation = True
  elif args.enable_cluster_isolation.upper() == "FALSE":
    request.cluster.enableClusterIsolation = False
  else:
    raise ValueError(
        "Invalid value for --enable-cluster-isolation: %s"
        % args.enable_cluster_isolation
    )

  _AddFieldToUpdateMask("enableClusterIsolation", request)
  return request


def _AddFieldToUpdateMask(field, request):
  if not request.updateMask:
    request.updateMask = field
    return request

  if field not in request.updateMask:
    request.updateMask = request.updateMask + "," + field
  return request
