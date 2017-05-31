# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flags for commands that deal with the Org Policies API."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


def AddIdArgToParser(parser):
  base.Argument(
      'id',
      metavar='ORG_POLICY_ID',
      help='The Org Policy constraint name.').AddToParser(parser)


def AddResourceFlagsToParser(parser):
  base.Argument(
      '--organization',
      metavar='ORGANIZATION_ID',
      help='Organization ID for Org Policies.').AddToParser(parser)


def CheckResourceFlags(args):
  if args.project and args.organization:
    raise exceptions.ConflictingArgumentsException('--organization',
                                                   '--project')
  if not args.project and not args.organization:
    raise exceptions.ToolException(
        'Neither --project nor --organization provided, exactly one required')
