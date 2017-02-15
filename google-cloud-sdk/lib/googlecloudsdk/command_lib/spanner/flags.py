# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Provides common arguments for the Spanner command surface."""

import itertools

from googlecloudsdk.calliope import base


def Database(positional=True,
             required=True,
             text='Cloud Spanner database name.'):
  resource = 'spanner.projects.instances.databases'
  if positional:
    return base.Argument(
        'database',
        completion_resource=resource,
        help=text)
  else:
    return base.Argument(
        '--database',
        required=required,
        completion_resource=resource,
        help=text)


def Ddl(required=False, help_text=''):
  return base.Argument(
      '--ddl',
      action='append',
      required=required,
      help=help_text)


def FixDdl(ddl):
  """Break DDL statements on semicolon to support multiple in one argument."""
  return list(itertools.chain.from_iterable(x.split(';') for x in ddl))


def Description(required=True):
  return base.Argument(
      '--description',
      required=required,
      help='Description of the instance.')


def Instance(positional=True, text='Cloud Spanner instance ID.'):
  resource = 'spanner.projects.instances'
  if positional:
    return base.Argument(
        'instance',
        completion_resource=resource,
        help=text)
  else:
    return base.Argument(
        '--instance',
        required=True,
        completion_resource=resource,
        help=text)


def Nodes(required=True):
  return base.Argument(
      '--nodes',
      required=required,
      type=int,
      help='Number of nodes for the instance.')


def OperationId(database=False):
  return base.Argument(
      'operation',
      metavar='OPERATION-ID',
      completion_resource='spanner.projects.instances.databases.operations'
      if database else 'spanner.projects.instances.operations',
      help='ID of the operation')
