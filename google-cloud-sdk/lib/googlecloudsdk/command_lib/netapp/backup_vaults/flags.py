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
"""Flags and helpers for the Cloud NetApp Backup Vaults commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.netapp import flags
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


BACKUP_VAULTS_LIST_FORMAT = """\
    table(
        name.basename():label=BACKUP_VAULT_NAME:sort=1,
        name.segment(3):label=LOCATION,
        state
    )"""


def GetBackupVaultTypeEnumFromArg(choice, messages):
  """Returns the Choice Enum for Backup Vault Type.

  Args:
    choice: The choice for backup vault type as string
    messages: The messages module.

  Returns:
    the backup vault type enum.
  """
  return arg_utils.ChoiceToEnum(
      choice=choice,
      enum_type=messages.BackupVault.BackupVaultTypeValueValuesEnum,
  )


def AddBackupVaultTypeArg(parser):
  help_text = """\
  String indicating the type of backup vault.
  The supported values are: 'IN_REGION','CROSS_REGION'
  """

  parser.add_argument(
      '--backup-vault-type',
      type=str,
      help=help_text,
      required=False,
  )


def AddBackupVaultBackupLocationArg(parser):
  """Adds the Backup Vault Backup Location arg to the arg parser."""
  parser.add_argument(
      '--backup-region',
      type=str,
      help="""String indicating backup location for the Backup Vault""",
  )
## Helper functions to combine Backup Vaults args / flags for gcloud commands ##


def AddBackupVaultCreateArgs(parser, release_track):
  """Add args for creating a Backup Vault."""
  concept_parsers.ConceptParser(
      [flags.GetBackupVaultPresentationSpec('The Backup Vault to create')]
  ).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Backup Vault')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddCreateLabelsFlags(parser)
  AddBackupRetentionPolicyArg(parser)
  AddKmsConfigArg(parser)
  if (release_track == base.ReleaseTrack.BETA):
    AddBackupVaultTypeArg(parser)
    AddBackupVaultBackupLocationArg(parser)


def AddBackupVaultDeleteArgs(parser):
  """Add args for deleting a Backup Vault."""
  concept_parsers.ConceptParser(
      [flags.GetBackupVaultPresentationSpec('The Backup Vault to delete')]
  ).AddToParser(parser)
  flags.AddResourceAsyncFlag(parser)


def AddBackupVaultUpdateArgs(parser):
  """Add args for updating a Backup Vault."""
  concept_parsers.ConceptParser(
      [flags.GetBackupVaultPresentationSpec('The Backup Vault to update')]
  ).AddToParser(parser)
  flags.AddResourceDescriptionArg(parser, 'Backup Vault')
  flags.AddResourceAsyncFlag(parser)
  labels_util.AddUpdateLabelsFlags(parser)
  AddBackupRetentionPolicyArg(parser)


def AddBackupRetentionPolicyArg(parser):
  """Adds the Backup Retention Policy arg to the arg parser."""
  backup_retention_policy_arg_spec = {
      'backup-minimum-enforced-retention-days': int,
      'daily-backup-immutable': bool,
      'weekly-backup-immutable': bool,
      'monthly-backup-immutable': bool,
      'manual-backup-immutable': bool
  }
  backup_retention_policy_help = textwrap.dedent("""\
    Backup Retention Policy of the Backup Vault.

    Backup Retention Policy allows you to configure the retention policy for
    backups created within this vault. It consists of several fields that govern
    how long backups are kept and what type of backups are immutable.
    """)
  parser.add_argument(
      '--backup-retention-policy',
      type=arg_parsers.ArgDict(spec=backup_retention_policy_arg_spec),
      required=False,
      help=backup_retention_policy_help,
      )


def AddKmsConfigArg(parser, hidden=False):
  """Adds the --kms-config flag to the parser."""
  help_text = """\
  The resource name of the KMS Config to use for encrypting backups within this backup vault.
  Format: projects/{project_id}/locations/{location}/kmsConfigs/{kms_config_id}
  """
  kms_config_presentation_spec = presentation_specs.ResourcePresentationSpec(
      '--kms-config',
      flags.GetKmsConfigResourceSpec(),
      help_text,
      required=False,
      hidden=hidden,
      flag_name_overrides={'location': ''},
  )
  concept_parsers.ConceptParser([kms_config_presentation_spec]).AddToParser(
      parser
  )
