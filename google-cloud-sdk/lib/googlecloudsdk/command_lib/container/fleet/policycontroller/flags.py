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
"""Functions to add standardized flags in PoCo commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.command_lib.container.fleet import resources


class Flags:
  """Handle common flags for Poco Commands."""

  def __init__(
      self,
      parser: parser_arguments.ArgumentInterceptor,
      command: str,
  ):
    self._parser = parser
    self._display_name = command

  @property
  def parser(self):  # pylint: disable=invalid-name
    return self._parser

  @property
  def display_name(self):
    return self._display_name

  def AddMemberships(self):
    """Adds handling for single, multiple or all memberships."""
    group = self.parser.add_argument_group('Membership flags.', mutex=True)
    resources.AddMembershipResourceArg(
        group,
        plural=True,
        membership_help=(
            'The membership names to {}, separated by commas if multiple '
            'are supplied. Ignored if --all-memberships is supplied; if '
            'neither is supplied, a prompt will appear with all available '
            'memberships.'.format(self.display_name)
        ),
    )

    group.add_argument(
        '--all-memberships',
        action='store_true',
        help=(
            'If supplied, {} all Policy Controllers memberships in the fleet.'
            .format(self.display_name)
        ),
        default=False,
    )
