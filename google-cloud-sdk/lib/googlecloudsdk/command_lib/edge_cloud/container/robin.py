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
"""Utils for Robin CNS related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.edge_cloud.container import util
from googlecloudsdk.command_lib.run import flags
from googlecloudsdk.core.console import console_io


def PromptToEnableRobinCNSConfirmation():
  """Displays warning and prompts user for confirmation."""
  message = """WARNING:
Enabling Robin CNS is irreversible. Once enabled, it cannot be disabled.
Enabling Robin CNS will take over all unused local Persistent Volumes (PVs)
in the cluster. Any data on these PVs will be permanently lost."""

  console_io.PromptContinue(message=message, default=False, cancel_on_no=True)


def EnableRobinCNSInRequest(req, args):
  """Set Robin CNS config in the cluster request message."""
  release_track = args.calliope_command.ReleaseTrack()
  messages = util.GetMessagesModule(release_track)
  if req.cluster is None:
    req.cluster = messages.Cluster()

  if req.cluster.systemAddonsConfig is None:
    req.cluster.systemAddonsConfig = messages.SystemAddonsConfig()
  if req.cluster.systemAddonsConfig.robinCloudNativeStorage is None:
    req.cluster.systemAddonsConfig.robinCloudNativeStorage = (
        messages.RobinCloudNativeStorage()
    )
  req.cluster.systemAddonsConfig.robinCloudNativeStorage.enable = True


def HandleEnableRobinCNSUpdate(ref, args, request):
  """Handles the --enable-robin-cns flag for UPDATE requests."""

  del ref

  if not flags.FlagIsExplicitlySet(args, "enable_robin_cns"):
    return request

  PromptToEnableRobinCNSConfirmation()
  EnableRobinCNSInRequest(request, args)

  _AddFieldToUpdateMask(
      "system_addons_config.robin_cloud_native_storage.enable", request
  )
  return request


def _AddFieldToUpdateMask(field, request):
  if not request.updateMask:
    request.updateMask = field
    return request

  if field not in request.updateMask:
    request.updateMask = request.updateMask + "," + field
  return request
