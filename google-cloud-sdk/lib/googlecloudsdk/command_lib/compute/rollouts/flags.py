# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the compute rollouts commands."""

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


class RolloutsCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(RolloutsCompleter, self).__init__(
        collection='compute.rollouts',
        list_command='compute rollouts list --uri',
        **kwargs
    )

  def RolloutsArgument(self):
    """Returns an argument for rollouts resource."""
    return compute_flags.ResourceArgument(
        resource_name='rollout',
        name='rollout',
        completer=compute_completers.RolloutsCompleter,
        plural=False,
        global_collection='compute.rollouts',
    )
