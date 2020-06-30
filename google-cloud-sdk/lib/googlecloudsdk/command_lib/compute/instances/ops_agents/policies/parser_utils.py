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
"""Utility functions for GCE Ops Agents Policy commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddArgs(parser):
  """Add shared arguments for Create/Update commands.

  Args:
    parser: A given parser
  """
  parser.add_argument(
      'POLICY_ID',
      type=str,
      help="""\
      Name of the policy to create.

      This name must contain only lowercase letters, numbers, and hyphens,
      start with a letter, end with a number or a letter, be between 1-63
      characters, and be unique within the project.
      """,
  )
  parser.add_argument(
      '--description',
      type=str,
      help='Description of the policy.',
  )
  parser.add_argument(
      '--agents',
      metavar='KEY=VALUE',
      action='store',
      required=True,
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(
              spec={
                  'type': str,
                  'version': str,
                  'package-state': str,
                  'enable-autoupgrade': arg_parsers.ArgBoolean(),
              }),
      ),
      help="""\
      Agents to be installed.

      This contains fields of type(required) - sample:{logging, metrics}, version(default: latest) - sample:{6.0.0-1, 1.6.35-1, 1.x.x, 6.x.x}, package-state(default: installed) - sample:{installed, removed}, enable-autoupgrade(default: false) - sample:{true, false}.
      """,
  )
  parser.add_argument(
      '--os-types',
      metavar='KEY=VALUE',
      action='store',
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(spec={
              'architecture': str,
              'short-name': str,
              'version': str,
          }),
      ),
      help="""\
      OS Types matcher for instances on which to create the policy.

      This contains fields of architecture(default: None) - sample: x86_64, short_name(required) - sample:{centos, debian, rhel}, version(required) - sample:{6, 7.8}.
      """,
  )
  parser.add_argument(
      '--group-labels',
      metavar='KEY=VALUE',
      action='store',
      type=arg_parsers.ArgList(
          custom_delim_char=';',
          element_type=arg_parsers.ArgDict(),
      ),
      help="""\
      Group Labels matcher for instances on which to create the policy.

      This contains a list of key value pairs for the instances labels.
      """,
  )
  parser.add_argument(
      '--instances',
      metavar='INSTANCES',
      type=arg_parsers.ArgList(),
      help="""\
      Specifies on which instances to create the policy.

      This contains a list of instances, example: zones/us-central1-a/instances/test-instance-1
      """,
  )
  parser.add_argument(
      '--zones',
      metavar='ZONES',
      type=arg_parsers.ArgList(),
      help="""\
      Zones matcher for instance on which to create the policy.

      This contains a list of zones, example: us-central1-a.
      """,
  )
