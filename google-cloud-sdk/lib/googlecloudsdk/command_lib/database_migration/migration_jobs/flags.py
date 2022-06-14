# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the migration jobs related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum


@enum.unique
class ApiType(enum.Enum):
  """This API type is used to differentiate between the classification types of Create requests and Update requests."""
  CREATE = 'create'
  UPDATE = 'update'


def AddNoAsyncFlag(parser):
  """Adds a --no-async flag to the given parser."""
  help_text = ('Waits for the operation in progress to complete before '
               'returning.')
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddDisplayNameFlag(parser):
  """Adds a --display-name flag to the given parser."""
  help_text = """
    A user-friendly name for the migration job. The display name can include
    letters, numbers, spaces, and hyphens, and must start with a letter.
    """
  parser.add_argument('--display-name', help=help_text)


def AddTypeFlag(parser, required=False):
  """Adds --type flag to the given parser."""
  help_text = 'Type of the migration job.'
  choices = ['ONE_TIME', 'CONTINUOUS']
  parser.add_argument(
      '--type', help=help_text, choices=choices, required=required)


def AddDumpPathFlag(parser):
  """Adds a --dump-path flag to the given parser."""
  help_text = """\
    Path to the dump file in Google Cloud Storage, in the format:
    `gs://[BUCKET_NAME]/[OBJECT_NAME]`.
    """
  parser.add_argument('--dump-path', help=help_text)


def AddConnectivityGroupFlag(parser, api_type, required=False):
  """Adds connectivity flag group to the given parser."""
  if api_type == ApiType.CREATE:
    connectivity_group = parser.add_group(
        'The connectivity method used by the migration job. If a connectivity method isn\'t specified, then it isn\'t added to the migration job.',
        mutex=True)
  elif api_type == ApiType.UPDATE:
    connectivity_group = parser.add_group(
        'The connectivity method used by the migration job. If a connectivity method isn\'t specified, then it isn\'t updated for the migration job.',
        mutex=True)
  connectivity_group.add_argument(
      '--static-ip',
      action='store_true',
      help='Use the default IP allowlist method. This method creates a public IP that will be used with the destination Cloud SQL database. The method works by configuring the source database server to accept connections from the outgoing IP of the Cloud SQL instance.'
  )
  connectivity_group.add_argument(
      '--peer-vpc',
      help='Name of the VPC network to peer with the Cloud SQL private network.'
  )
  reverse_ssh_group = connectivity_group.add_group(
      'Parameters for the reverse-SSH tunnel connectivity method.')
  reverse_ssh_group.add_argument(
      '--vm-ip', help='Bastion Virtual Machine IP.', required=required)
  reverse_ssh_group.add_argument(
      '--vm-port',
      help='Forwarding port for the SSH tunnel.',
      type=int,
      required=required)
  reverse_ssh_group.add_argument(
      '--vm', help='Name of VM that will host the SSH tunnel bastion.')
  reverse_ssh_group.add_argument(
      '--vpc',
      help='Name of the VPC network where the VM is hosted.',
      required=required)
