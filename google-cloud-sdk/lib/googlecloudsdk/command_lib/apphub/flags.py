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
"""Apphub Command Lib Flags."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddTopologyUpdateFlags(parser):
  """Adds flags to topology update command.

  Flags include:
    --enable
    --disable

  Args:
    parser: The argparser.
  """

  state_group = parser.add_group(
      mutex=True, help='Manage topology state.'
  )
  state_group.add_argument(
      '--enable',
      action='store_const',
      const=True,
      help='Enable topology.',
  )
  state_group.add_argument(
      '--disable',
      action='store_const',
      const=True,
      help='Disable topology.',
  )


def AddTelemetryUpdateFlags(parser):
  """Adds flags to telemetry update command.

  Flags include:
    --enable-monitoring
    --disable-monitoring

  Args:
    parser: The argparser.
  """

  state_group = parser.add_group(
      mutex=True, help='Manage telemetry monitoring state.'
  )
  state_group.add_argument(
      '--enable-monitoring',
      action='store_const',
      const=True,
      help='Enable telemetry monitoring.',
  )
  state_group.add_argument(
      '--disable-monitoring',
      action='store_const',
      const=True,
      help='Disable telemetry monitoring.',
  )
