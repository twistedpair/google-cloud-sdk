# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Flags for workflow templates related commands."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import properties


def AddZoneFlag(parser):
  parser.add_argument(
      '--zone',
      '-z',
      help="""
          The compute zone (e.g. us-central1-a) for the cluster. If empty,
          and --region is set to a value other than 'global', the server will
          pick a zone in the region.
          """,
      action=actions.StoreProperty(properties.VALUES.compute.zone))


def AddVersionFlag(parser):
  parser.add_argument(
      '--version', type=int, help='The version of the workflow template.')


def AddTemplateFlag(parser, action):
  parser.add_argument(
      'template', help='The ID of the workflow template to {0}.'.format(action))


def AddJobFlag(parser, action):
  parser.add_argument(
      'job', help='The ID of the job to {0}.'.format(action))


def AddOperationFlag(parser, action):
  parser.add_argument(
      'operation', help='The ID of the operation to {0}.'.format(action))


def AddTimeoutFlag(parser, default='10m'):
  # This may be made visible or passed to the server in future.
  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      default=default,
      help=('Client side timeout on how long to wait for Datproc operations. '
            'See $ gcloud topic datetimes for information on duration '
            'formats.'),
      hidden=True)


def AddMinCpuPlatformArgs(parser, track):
  """Add mininum CPU platform flags for both master and worker instances."""
  help_text = """\
      When specified, the VM will be scheduled on host with specified CPU
      architecture or a newer one. To list available CPU platforms in given
      zone, run:

          $ gcloud {}compute zones describe ZONE

      CPU platform selection is available only in selected zones; zones that
      allow CPU platform selection will have an `availableCpuPlatforms` field
      that contains the list of available CPU platforms for that zone.

      You can find more information online:
      https://cloud.google.com/compute/docs/instances/specify-min-cpu-platform
      """.format(track.prefix + ' ' if track.prefix else '')
  parser.add_argument(
      '--master-min-cpu-platform',
      metavar='PLATFORM',
      required=False,
      help=help_text)
  parser.add_argument(
      '--worker-min-cpu-platform',
      metavar='PLATFORM',
      required=False,
      help=help_text)
