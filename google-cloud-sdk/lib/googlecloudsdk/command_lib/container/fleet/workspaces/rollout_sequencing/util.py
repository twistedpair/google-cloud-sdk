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
"""Utils for Fleet Scopes Cluster Upgrade Feature command preparations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.container.fleet.workspaces.rollout_sequencing import base


def DescribeClusterUpgrade(response, args):
  """Adds Cluster Upgrade Feature information to describe Scope request.

  This is a modify_request_hook for gcloud declarative YAML.

  Args:
    response: Scope message.
    args: command line arguments.

  Returns:
    response with optional Cluster Upgrade Feature information
  """
  cmd = base.DescribeCommand(args)
  if cmd.IsClusterUpgradeRequest():
    feature = cmd.GetFeature()
    return cmd.GetScopeWithClusterUpgradeInfo(response, feature)
  return response
