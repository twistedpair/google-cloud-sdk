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
"""Flags and helpers for the compute packet mirroring commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.compute import completers as compute_completers
from googlecloudsdk.command_lib.compute import flags as compute_flags


class PacketMirroringCompleter(compute_completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(PacketMirroringCompleter, self).__init__(
        collection='compute.packetMirrorings',
        list_command='alpha compute packet-mirrorings list --uri',
        **kwargs)


def PacketMirroringArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='packet mirroring',
      completer=PacketMirroringCompleter,
      plural=plural,
      custom_plural='packet mirrorings',
      required=required,
      regional_collection='compute.packetMirrorings')
