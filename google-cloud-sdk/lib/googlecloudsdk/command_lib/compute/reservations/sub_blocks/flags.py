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
"""Flags and helpers for the compute reservation sub block commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


def AddDescribeFlags(parser):
  """Adds flags to the parser for the describe command."""
  parser.add_argument(
      '--block-name',
      metavar='BLOCK_NAME',
      type=str,
      required=True,
      help='The name of the reservation block.')
  parser.add_argument(
      '--sub-block-name',
      metavar='SUB_BLOCK_NAME',
      type=str,
      required=True,
      help='The name of the reservation sub block.')


def AddListFlags(parser):
  """Adds flags to the parser for the describe command."""
  parser.add_argument(
      '--block-name',
      metavar='BLOCK_NAME',
      type=str,
      required=True,
      help='The name of the reservation block.')


def AddFullViewFlag(parser):
  help_text = """\
  The view type for the reservation sub-block.
  """
  parser.add_argument(
      '--full-view',
      metavar='FULL_VIEW',
      choices={
          'SUB_BLOCK_VIEW_FULL': (
              'Full detailed view of the reservation sub-block.'
          ),
          'SUB_BLOCK_VIEW_BASIC': (
              'Basic default view of the reservation sub-block.'
          ),
      },
      default='SUB_BLOCK_VIEW_UNSPECIFIED',
      help=help_text,
      required=False,
  )


def GetDisruptionScheduleFlag():
  """Gets the --disruption-schedule flag."""
  return base.Argument(
      '--disruption-schedule',
      choices={
          'IMMEDIATE': 'All VMs are immediately disrupted.',
      },
      help='The disruption schedule for the sub-block.',
      required=True)


def GetFaultReasonsFlag():
  """Gets the --fault-reasons flag."""
  return base.Argument(
      '--fault-reasons',
      type=arg_parsers.ArgDict(
          spec={'behavior': str, 'description': str},
      ),
      action='append',
      help=(
          'The reasons for reporting the sub-block as faulty. You can repeat'
          ' this flag. Each flag must specify a "behavior" attribute and can'
          ' optionally include a "description" attribute. The possible values'
          ' for "behavior" are: PERFORMANCE, SWITCH_FAILURE, GPU_ERROR.'
      ),
      required=True,
  )


def GetFailureComponentFlag():
  """Gets the --failure-component flag."""
  return base.Argument(
      '--failure-component',
      choices={
          'NVLINK_SWITCH': 'The NVLink switch experienced the fault.',
          'MULTIPLE_FAULTY_HOSTS': 'Multiple hosts experienced the fault.',
      },
      help='The component that experienced the fault.',
      required=True)
