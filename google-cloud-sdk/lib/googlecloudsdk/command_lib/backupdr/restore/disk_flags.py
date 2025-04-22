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
"""Flags for backup-dr restore disk commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def AddNameArg(parser, required=True):
  parser.add_argument(
      '--name',
      type=str,
      required=required,
      help='Name of the restored Disk.',
  )


def AddTargetZoneArg(parser, required=False):
  parser.add_argument(
      '--target-zone',
      type=str,
      required=required,
      help=(
          'Zone where the target disk is restored. This flag is mutually'
          ' exclusive with --target-region.'
      ),
  )


def AddTargetRegionArg(parser, required=False):
  parser.add_argument(
      '--target-region',
      type=str,
      required=required,
      help=(
          'Region where the target disk is restored. This flag is mutually'
          ' exclusive with --target-zone.'
      ),
  )


def AddTargetProjectArg(parser, required=True):
  parser.add_argument(
      '--target-project',
      type=str,
      required=required,
      help='Project where the restore should happen.',
  )
