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

import string
import textwrap

from googlecloudsdk.calliope import arg_parsers


def AddCollectionIdsFlag(parser):
  """Adds flag for collection ids to the given parser.

  Args:
    parser: The argparse parser.
  """
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
      """,
  )


def AddDatabaseIdFlag(parser, required=False, hidden=False):
  """Adds flag for database id to the given parser.

  Args:
    parser: The argparse parser.
    required: Whether the flag must be set for running the command, a bool.
    hidden: Whether the flag is hidden, a bool.
  """
  if not required:
    helper_text = """\
      The database to operate on. The default value is `(default)`.

      For example, to operate on database `foo`:

        $ {command} --database='foo'
      """
  else:
    helper_text = """\
      The database to operate on.

      For example, to operate on database `foo`:

        $ {command} --database='foo'
      """
  parser.add_argument(
      '--database',
      metavar='DATABASE',
      type=str,
      default='(default)' if not required else None,
      required=required,
      hidden=hidden,
      help=helper_text,
  )


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
      """,
  )


def AddSnapshotTimeFlag(parser):
  """Adds flag for snapshot time to the given parser.

  Args:
    parser: The argparse parser.
  """
  parser.add_argument(
      '--snapshot-time',
      metavar='SNAPSHOT_TIME',
      type=str,
      default=None,
      required=False,
      help="""
      The version of the database to export.

      The timestamp must be in the past, rounded to the minute and not older
      than `earliestVersionTime`. If specified, then the exported documents will
      represent a consistent view of the database at the provided time.
      Otherwise, there are no guarantees about the consistency of the exported
      documents.

      For example, to operate on snapshot time `2023-05-26T10:20:00.00Z`:

        $ {command} --snapshot-time='2023-05-26T10:20:00.00Z'
      """,
  )


def AddLocationFlag(
    parser, required=False, hidden=False, suggestion_aliases=None
):
  """Adds flag for location to the given parser.

  Args:
    parser: The argparse parser.
    required: Whether the flag must be set for running the command, a bool.
    hidden: Whether the flag is hidden in document. a bool.
    suggestion_aliases: A list of flag name aliases. A list of string.
  """
  parser.add_argument(
      '--location',
      metavar='LOCATION',
      required=required,
      hidden=hidden,
      type=str,
      suggestion_aliases=suggestion_aliases,
      help="""
      The location to operate on. Available locations are listed at
      https://cloud.google.com/firestore/docs/locations.

      For example, to operate on location `us-east1`:

        $ {command} --location='us-east1'
      """,
  )


def AddBackupFlag(parser):
  """Adds flag for backup to the given parser.

  Args:
    parser: The argparse parser.
  """
  parser.add_argument(
      '--backup',
      metavar='BACKUP',
      required=True,
      type=str,
      help="""
      The backup to operate on.

      For example, to operate on backup `cf9f748a-7980-4703-b1a1-d1ffff591db0`:

        $ {command} --backup='cf9f748a-7980-4703-b1a1-d1ffff591db0'
      """,
  )


def AddBackupScheduleFlag(parser):
  """Adds flag for backup schedule id to the given parser.

  Args:
    parser: The argparse parser.
  """
  parser.add_argument(
      '--backup-schedule',
      metavar='BACKUP_SCHEDULE',
      required=True,
      type=str,
      help="""
      The backup schedule to operate on.

      For example, to operate on backup schedule `091a49a0-223f-4c98-8c69-a284abbdb26b`:

        $ {command} --backup-schedule='091a49a0-223f-4c98-8c69-a284abbdb26b'
      """,
  )


def AddRetentionFlag(parser, required=False):
  """Adds flag for retention to the given parser.

  Args:
    parser: The argparse parser.
    required: Whether the flag must be set for running the command, a bool.
  """
  parser.add_argument(
      '--retention',
      metavar='RETENTION',
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
  """Adds flag for recurrence to the given parser.

  Args:
    parser: The argparse parser.
  """
  group = parser.add_group(
      help='Recurrence settings of a backup schedule.',
      required=True,
  )
  help_text = """\
      The recurrence settings of a backup schedule.

      Currently only daily and weekly backup schedules are supported.

      When a weekly backup schedule is created, day-of-week is needed.

      For example, to create a weekly backup schedule which creates backups on
      Monday.

        $ {command} --recurrence=weekly --day-of-week=MON
  """
  group.add_argument('--recurrence', type=str, help=help_text, required=True)

  help_text = """\
     The day of week (UTC time zone) of when backups are created.

      The available values are: `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`,`SUN`.
      Values are case insensitive.

      This is required when creating a weekly backup schedule.
  """
  group.add_argument(
      '--day-of-week',
      choices=arg_parsers.DayOfWeek.DAYS,
      type=arg_parsers.DayOfWeek.Parse,
      help=help_text,
      required=False,
  )


def AddEncryptionConfigGroup(parser, source_type):
  """Adds flags for the database's encryption configuration to the given parser.

  Args:
    parser: The argparse parser.
    source_type: "backup" if a restore; "database" if a clone
  """
  encryption_config = parser.add_argument_group(
      required=False,
      help=textwrap.dedent(string.Template("""\
            The encryption configuration of the new database being created from the $source_type.
            If not specified, the same encryption settings as the $source_type will be used.

            To create a CMEK-enabled database:

              $$ {command} --encryption-type=customer-managed-encryption --kms-key-name=projects/PROJECT_ID/locations/LOCATION_ID/keyRings/KEY_RING_ID/cryptoKeys/CRYPTO_KEY_ID

            To create a Google-default-encrypted database:

              $$ {command} --encryption-type=google-default-encryption

            To create a database using the same encryption settings as the $source_type:

              $$ {command} --encryption-type=use-source-encryption
            """).substitute(source_type=source_type)),
  )
  encryption_config.add_argument(
      '--encryption-type',
      metavar='ENCRYPTION_TYPE',
      type=str,
      required=True,
      choices=[
          'use-source-encryption',
          'customer-managed-encryption',
          'google-default-encryption',
      ],
      help=textwrap.dedent("""\
          The encryption type of the destination database.
          """),
  )
  AddKmsKeyNameFlag(
      encryption_config,
      'This flag must only be specified when encryption-type is'
      ' `customer-managed-encryption`.',
  )


def AddKmsKeyNameFlag(parser, additional_help_text=None):
  """Adds flag for KMS Key Name to the given parser.

  Args:
    parser: The argparse parser.
    additional_help_text: Additional help text to be added to the flag.
  """

  help_text = textwrap.dedent("""
      The resource ID of a Cloud KMS key. If set, the database created will be a Customer-Managed Encryption Key (CMEK) database encrypted with this key.
      This feature is allowlist only in initial launch.

      Only a key in the same location as this database is allowed to be used for encryption.
      For Firestore's nam5 multi-region, this corresponds to Cloud KMS location us.
      For Firestore's eur3 multi-region, this corresponds to Cloud KMS location europe.
      See https://cloud.google.com/kms/docs/locations.

      This value should be the KMS key resource ID in the format of `projects/{project_id}/locations/{kms_location}/keyRings/{key_ring}/cryptoKeys/{crypto_key}`.
      How to retrieve this resource ID is listed at https://cloud.google.com/kms/docs/getting-resource-ids#getting_the_id_for_a_key_and_version.
    """)
  if additional_help_text:
    help_text = help_text + '\n\n' + additional_help_text

  parser.add_argument(
      '--kms-key-name',
      metavar='KMS_KEY_NAME',
      type=str,
      required=False,
      default=None,
      help=help_text,
  )


def AddDestinationDatabase(parser, action_name, source_type):
  parser.add_argument(
      '--destination-database',
      metavar='DESTINATION_DATABASE',
      type=str,
      required=True,
      help=textwrap.dedent(f"""\
          Destination database to {action_name} to. Destination database will be created in the same location as the source {source_type}.

          This value should be 4-63 characters. Valid characters are /[a-z][0-9]-/
          with first character a letter and the last a letter or a number. Must
          not be UUID-like /[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}/.

          Using "(default)" database ID is also allowed.

          For example, to {action_name} to database `testdb`:

          $ {{command}} --destination-database=testdb
          """),
  )


def AddTags(parser, resource_type):
  """Adds the --tags flag to the given parser.

  Args:
    parser: The parser to add the flag to.
    resource_type: The resource type to use in the help text (e.g. 'database').
  """
  parser.add_argument(
      '--tags',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      default=None,
      help=textwrap.dedent(f"""\
          Tags to attach to the destination {resource_type}. Example: --tags=key1=value1,key2=value2

          For example, to attach tags to a {resource_type}:

          $ --tags=key1=value1,key2=value2
          """),
  )


def AddUserCredsIdArg(parser):
  """Adds positional arg for user creds id to the given parser.

  Args:
    parser: The argparse parser.
  """
  parser.add_argument(
      'user_creds',
      metavar='USER_CREDS',
      type=str,
      help="""
      The user creds to operate on.

      For example, to operate on user creds `creds-name-1`:

        $ {command} creds-name-1
      """,
  )
