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
"""Common flags for workload identity pools commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddGcpWorkloadSourceFlags(parser):
  parser.add_argument(
      '--resources',
      type=arg_parsers.ArgList(),
      help='A list of allowed resources for the workload source.',
      metavar='RESOURCE',
  )
  parser.add_argument(
      '--attached-service-accounts',
      type=arg_parsers.ArgList(),
      help=(
          'A list of allowed attached_service_accounts for the workload source.'
      ),
      metavar='SERVICE_ACCOUNT',
  )


def AddFederatedWorkloadSourceFlags(parser):
  parser.add_argument(
      '--external-condition',
      help=(
          'A CEL expression that defines the allowed conditions for the '
          'workload source.'
      ),
  )


def AddUpdateWorkloadSourceFlags(parser):
  """Adds the flags for update workload source command."""
  parser.add_argument(
      '--add-resources',
      type=arg_parsers.ArgList(),
      help='A list of allowed resources to add to the workload source.',
      metavar='RESOURCE',
  )
  parser.add_argument(
      '--add-attached-service-accounts',
      type=arg_parsers.ArgList(),
      help=(
          'A list of allowed attached_service_accounts to add to the workload'
          ' source.'
      ),
      metavar='SERVICE_ACCOUNT',
  )
  parser.add_argument(
      '--remove-resources',
      type=arg_parsers.ArgList(),
      help='A list of allowed resources to remove from the workload source.',
      metavar='RESOURCE',
  )
  parser.add_argument(
      '--remove-attached-service-accounts',
      type=arg_parsers.ArgList(),
      help=(
          'A list of allowed attached_service_accounts to remove from the'
          ' workload source.'
      ),
      metavar='SERVICE_ACCOUNT',
  )
  parser.add_argument(
      '--clear-resources',
      help='Remove all the allowed resources for the workload source.',
      action='store_true',
  )
  parser.add_argument(
      '--clear-attached-service-accounts',
      help=(
          'Remove all the allowed attached_service_accounts for the workload'
          ' source.'
      ),
      action='store_true',
  )
