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
"""Functions to add flags in rollout commands."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.api_lib.container.fleet import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.container.fleet import resources as fleet_resources
from googlecloudsdk.core import resources
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as fleet_messages


class RolloutFlags:
  """Add flags to the fleet rollout command surface."""

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
      release_track: base.ReleaseTrack = base.ReleaseTrack.ALPHA,
  ):
    self._parser = parser
    self._release_track = release_track

  @property
  def parser(self):
    return self._parser

  @property
  def release_track(self):
    return self._release_track

  def AddAsync(self):
    base.ASYNC_FLAG.AddToParser(self.parser)

  def AddDisplayName(self):
    self.parser.add_argument(
        '--display-name',
        type=str,
        help=textwrap.dedent("""\
            Display name of the rollout to be created (optional). 4-30
            characters, alphanumeric and [ \'"!-] only.
        """),
    )

  def AddRolloutResourceArg(self):
    fleet_resources.AddRolloutResourceArg(
        parser=self.parser,
        api_version=util.VERSION_MAP[self.release_track],
    )


class RolloutFlagParser:
  """Parse flags during fleet rollout command runtime."""

  def __init__(
      self, args: parser_extensions.Namespace, release_track: base.ReleaseTrack
  ):
    self.args = args
    self.release_track = release_track
    self.messages = util.GetMessagesModule(release_track)

  def Rollout(self) -> fleet_messages.Rollout:
    rollout = fleet_messages.Rollout()
    rollout.name = util.RolloutName(self.args)
    rollout.displayName = self._DisplayName()

    return rollout

  def _DisplayName(self) -> str:
    return self.args.display_name

  def OperationRef(self) -> resources.Resource:
    """Parses resource argument operation."""
    return self.args.CONCEPTS.operation.Parse()

  def Project(self) -> str:
    return self.args.project

  def Location(self) -> str:
    return self.args.location

  def Async(self) -> bool:
    """Parses --async flag.

    The internal representation of --async is set to args.async_, defined in
    calliope/base.py file.

    Returns:
      bool, True if specified, False if unspecified.
    """
    return self.args.async_
