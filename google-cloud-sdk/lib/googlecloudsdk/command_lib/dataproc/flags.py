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
