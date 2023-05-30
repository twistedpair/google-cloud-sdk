# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the firestore related commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope import arg_parsers


def AddCollectionIdsFlag(parser):
  """Adds flag for collection ids to the given parser."""
  parser.add_argument(
      '--collection-ids',
      metavar='COLLECTION_IDS',
      type=arg_parsers.ArgList(),
      help="""
      List specifying which collections will be included in the operation.
      When omitted, all collections are included.

      For example, to operate on only the `customers` and `orders`
      collections:

        $ {command} --collection-ids='customers','orders'
      """)


def AddDatabaseIdFlag(parser, required=False, hidden=False):
  """Adds flag for database id to the given parser."""
  parser.add_argument(
      '--database',
      metavar='DATABASE',
      type=str,
      default='(default)' if not required else None,
      hidden=hidden,
      required=required,
      help="""
      The database to operate on. The default value is `(default)`.

      For example, to operate on database `foo`:

        $ {command} --database='foo'
      """)


def AddNamespaceIdsFlag(parser):
  """Adds flag for namespace ids to the given parser."""
  parser.add_argument(
      '--namespace-ids',
      metavar='NAMESPACE_IDS',
      type=arg_parsers.ArgList(),
      help="""
      List specifying which namespaces will be included in the operation.
      When omitted, all namespaces are included.

      This is only supported for Datastore Mode databases.

      For example, to operate on only the `customers` and `orders` namespaces:

        $ {command} --namespaces-ids='customers','orders'
      """)


def AddLocationFlag(parser, required=False):
  """Adds flag for location to the given parser."""
  parser.add_argument(
      '--location',
      metavar='LOCATION',
      required=required,
      hidden=True,
      type=str,
      help="""
      The location to operate on.

      For example, to operate on location `us-east1`:

        $ {command} --location='us-east1'
      """,
  )


def AddBackupFlag(parser):
  """Adds flag for backup to the given parser."""
  parser.add_argument(
      '--backup',
      metavar='BACKUP',
      required=True,
      hidden=True,
      type=str,
      help="""
      The backup to operate on.

      For example, to operate on backup `cf9f748a-7980-4703-b1a1-d1ffff591db0`:

        $ {command} --backup='cf9f748a-7980-4703-b1a1-d1ffff591db0'
      """,
  )


def AddBackupScheduleFlag(parser):
  """Adds flag for backup schedule id to the given parser."""
  parser.add_argument(
      '--backup-schedule',
      metavar='BACKUP_SCHEDULE',
      required=True,
      hidden=True,
      type=str,
      help="""
      The backup schedule to operate on.

      For example, to operate on backup schedule `091a49a0-223f-4c98-8c69-a284abbdb26b`:

        $ {command} --backup-schedule='091a49a0-223f-4c98-8c69-a284abbdb26b'
      """)


def AddRetentionFlag(parser, required=False):
  """Adds flag for retention to the given parser."""
  parser.add_argument(
      '--retention',
      metavar='RETENTION',
      hidden=True,
      required=required,
      type=arg_parsers.Duration(),
      help=textwrap.dedent("""\
          The rention of the backup. At what relative time in the future,
          compared to the creation time of the backup should the backup be
          deleted, i.e. keep backups for 7 days.

          For example, to set retention as 7 days.

          $ {command} --retention=7d
          """),
  )


def AddRecurrenceFlag(parser):
  """Adds flag for recurrence to the given parser."""
  parser.add_argument(
      '--recurrence',
      metavar='RECURRENCE',
      hidden=True,
      required=True,
      type=str,
      help="""
      The recurrence of the backup. recurrence represents how frequent the backups will be taken.

      The available values are: `daily` and `weekly`.

      For example, to set retention as 7 days.

        $ {command} --recurrence=daily
      """,
  )
