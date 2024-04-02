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
"""Flags for backup-dr commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def LocationAttributeConfig(arg_name='location'):
  return concepts.ResourceParameterAttributeConfig(
      name=arg_name, help_text='The location of the {resource}.'
  )


def GetManagementServerResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.managementServers',
      resource_name='Management Server',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def GetBackupPlanResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupPlans',
      resource_name='Backup Plan',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      backupPlansId=concepts.ResourceParameterAttributeConfig(
          name='backup_plan',
          help_text='some help text',
      ),
      disable_auto_completers=False,
  )


def GetBackupPlanAssociationResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupPlanAssociations',
      resource_name='Backup Plan Association',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def AddManagementServerResourceArg(parser, help_text):
  """Adds an argument for management server to parser."""
  name = 'management_server'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetManagementServerResourceSpec(),
      help_text,
      required=True,
  ).AddToParser(parser)


def AddCreateBackupPlanAssociationFlags(parser):
  """Adds flags required to create a backup plan association."""
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'BACKUP_PLAN_ASSOCIATION',
              GetBackupPlanAssociationResourceSpec(),
              'Name of the backup plan association to be created',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--backup-plan',
              GetBackupPlanResourceSpec(),
              'Name of the backup plan to be applied to the specified'
              ' resource.',
              # This hides the location flag for backup plan.
              flag_name_overrides={
                  'location': '',
                  'project': '',
              },
              required=True,
          ),
      ],
      command_level_fallthroughs={
          '--backup-plan.location': ['BACKUP_PLAN_ASSOCIATION.location'],
      },
  ).AddToParser(parser)

  parser.add_argument(
      '--resource',
      required=True,
      type=str,
      help='Resource to which the Backup Plan will be applied.',
  )


def AddNetwork(parser, required=True):
  """Adds a positional network argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --network is required.
  """
  parser.add_argument(
      '--network',
      required=required,
      type=str,
      help=(
          'Name of an existing VPC network with private service access'
          ' configured in the format -'
          ' projects/<project>/global/networks/<network>. This VPC network'
          ' allows the management console to communicate with all'
          ' backup/recovery appliances and requires a minimum IP range of /23.'
          ' This value cannot be changed after you deploy the management'
          " server. If you don't have private service access, configure one."
          ' [Learn more]'
          ' (https://cloud.google.com/vpc/docs/configure-private-services-access)'
      ),
  )


def GetBackupVaultResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupVaults',
      resource_name='Backup Vault',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def AddBackupVaultResourceArg(parser, help_text):
  """Adds an argument for backup vault to parser."""
  name = 'backup_vault'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetBackupVaultResourceSpec(),
      help_text,
      required=True,
  ).AddToParser(parser)


def AddNoAsyncFlag(parser):
  """Adds the --no-async flag to the given parser."""
  help_text = (
      'An optional request ID to identify requests. Set this flag to generate a'
      ' unique request ID so that if you must retry your request, the server'
      ' will know to ignore the request if it has already been completed.'
  )
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddForceDeleteFlag(parser):
  """Adds a --force-delete flag to the given parser."""
  help_text = (
      'If set, the following restrictions against deletion of'
      ' the backup vault instance can be overridden:'
      ' * deletion of a backup vault instance containing no backups,'
      'but still contains empty datasources.'
      ' * deletion of a backup vault instance containing no backups,'
      'but still contains empty datasources.'
  )
  parser.add_argument('--force-delete', action='store_true', help=help_text)


def AddRequestIdFlag(parser):
  """Adds a --request-id flag to the given parser."""
  help_text = (
      'An optional request ID to identify requests. Specify a unique request ID'
      ' so that if you must retry your request, the server will know to ignore'
      ' the request if it has already been completed.'
  )
  parser.add_argument('--request-id', action='store_true', help=help_text)


def AddBackupPlanResourceArg(parser, help_text):
  """Adds an argument for backup plan to parser."""
  name = 'backup_plan'
  backup_plan_spec = concepts.ResourceSpec(
      'backupdr.projects.locations.backupPlans',
      resource_name='Backup Plan',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )
  concept_parsers.ConceptParser.ForResource(
      name,
      backup_plan_spec,
      help_text,
      required=True,
  ).AddToParser(parser)


def AddEnforcedRetention(parser, required=True):
  """Adds a positional enforced-retention argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --enforced-retention is required.
  """
  parser.add_argument(
      '--enforced-retention',
      required=required,
      type=arg_parsers.Duration(
          lower_bound='1d', upper_bound='36159d', parsed_unit='s'
      ),
      help=(
          'If set, enforces the retention period for backups in this backup'
          ' vault. Each backup in the backup vault cannot be deleted before'
          ' it is out of the retention period.'
      ),
  )


def AddDescription(parser):
  """Adds the --description flag to the given parser."""
  help_text = (
      'An optional description for the backup vault (2048 characters or less).'
  )
  parser.add_argument('--description', type=str, help=help_text)


def AddLabels(parser):
  """Adds the --labels flag to the given parser."""
  help_text = (
      'Optional resource labels to represent metadata provided by the user.'
  )
  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help=help_text,
  )


def AddEffectiveTime(parser):
  """Adds the --effective-time flag to the given parser."""
  help_text = (
      'Time after which the backup vault is locked against decrease in'
      ' retention period. It should be specified in the format of'
      ' "YYYY-MM-DD". For a backup vault, this time is fixed at 12 AM UTC. If'
      ' set, enforces the retention period for backups in this backup vault. If'
      ' not set, you can change the retention period at any time.'
  )
  parser.add_argument(
      '--effective-time',
      type=arg_parsers.Day.Parse,
      help=help_text,
  )
