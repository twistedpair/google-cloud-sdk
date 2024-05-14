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
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.backupdr import util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties


def LocationAttributeConfig(arg_name='location'):
  return concepts.ResourceParameterAttributeConfig(
      name=arg_name, help_text='The location of the {resource}.'
  )


def BackupVaultAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='backup-vault', help_text='The ID of the Backup Vault.'
  )


def DataSourceAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='data-source', help_text='The ID of the Data Source.'
  )


def GetManagementServerResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.managementServers',
      resource_name='Management Server',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def BackupPlanAssociationProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='workload-project',
      help_text='Cloud project id for the {resource}.',
      fallthroughs=[
          deps.ArgFallthrough('--project'),
          deps.PropertyFallthrough(properties.VALUES.core.project),
      ],
  )


def GetBackupPlanResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupPlans',
      resource_name='Backup Plan',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def GetBackupPlanAssociationResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupPlanAssociations',
      resource_name='Backup Plan Association',
      locationsId=LocationAttributeConfig(),
      projectsId=BackupPlanAssociationProjectAttributeConfig(),
      disable_auto_completers=False,
  )


def GetBackupResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupVaults.dataSources.backups',
      resource_name='Backup',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      backupVaultsId=BackupVaultAttributeConfig(),
      dataSourcesId=DataSourceAttributeConfig(),
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


def AddBackupPlanAssociationResourceArg(parser, help_text):
  """Adds an argument for backup plan association to parser."""
  name = 'backup_plan_association'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetBackupPlanAssociationResourceSpec(),
      help_text,
      required=True,
  ).AddToParser(parser)


def AddBackupResourceArg(parser, help_text):
  """Adds an argument for backup to parser."""
  name = 'backup'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetBackupResourceSpec(),
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
              'Name of the backup plan association to be created. Once the'
              " backup plan association is created, this name can't be changed."
              ' The name must be unique for a project and location. To create'
              " backup plan associations in a project that's different from the"
              ' backup plan, use the --workload-project flag.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--backup-plan',
              GetBackupPlanResourceSpec(),
              'The backup plan to be applied to the resource. E.g.,'
              ' projects/sample-project/locations/us-central1/backupPlans/sample-backup-plan',
              # This hides the location flag for backup plan.
              flag_name_overrides={
                  'location': '',
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
      help=(
          'The resource to which the backup plan is to be applied. E.g.,'
          ' projects/sample-project/zones/us-central1-a/instances/sample-instance'
      ),
  )


def AddTriggerBackupFlags(parser):
  """Adds flags required to create a backup plan association."""
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'BACKUP_PLAN_ASSOCIATION',
              GetBackupPlanAssociationResourceSpec(),
              'Name of an existing backup plan association to use for creating'
              ' an on-demand backup.',
              required=True,
          ),
      ],
  ).AddToParser(parser)

  parser.add_argument(
      '--backup-rule-id',
      required=True,
      type=str,
      help=(
          'Name of an existing backup rule to use for creating an on-demand'
          ' backup.'
      ),
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
  help_text = 'Wait for the operation in progress to complete.'
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


def AddEnforcedRetention(parser, required):
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
          'Backups will be kept for this minimum period before they can be'
          ' deleted. Once the effective time is reached, the enforced retention'
          ' period cannot be decreased or removed. '
      ),
  )


def AddDescription(parser):
  """Adds the --description flag to the given parser."""
  help_text = (
      'Optional description for the backup vault (2048 characters or less).'
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
      'The time at which the enforced retention period becomes locked. It'
      ' should be specified in the format of "YYYY-MM-DD".'
  )
  parser.add_argument(
      '--effective-time',
      type=arg_parsers.Day.Parse,
      help=help_text,
  )


def AddUnlockEnforcedRetention(parser):
  """Adds the --unlock-enforced-retention flag to the given parser."""
  help_text = (
      'Removes the lock on the enforced retention period, and resets the'
      ' effective time. When unlocked, the enforced retention period can be'
      ' changed at any time.'
  )
  parser.add_argument(
      '--unlock-enforced-retention', action='store_true', help=help_text
  )


def AddResourceType(parser, required=True):
  """Adds a positional resource-type argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --resource-type is required.
  """
  parser.add_argument(
      '--resource-type',
      required=required,
      type=str,
      help=("""Type of resource to which the backup plan should be applied.
          E.g., `compute.<UNIVERSE_DOMAIN>.com/Instance` """),
  )


def AddBackupRule(parser, required=True):
  """Adds a positional backup-rule argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --backup-rule is required.
  """

  rule_id_validator = arg_parsers.RegexpValidator(
      r'[a-z][a-z0-9-]{0,62}',
      'Invalid rule-id. This human-readable name must be unique and start with'
      ' a lowercase letter followed by up to 62 lowercase letters, numbers, or'
      ' hyphens',
  )

  backup_vault_validator = arg_parsers.RegexpValidator(
      r'projects\/((?:[^:]+:)?[a-z0-9\\-]+)\/locations\/([a-zA-Z0-9-]+)\/backupVaults\/(.*)$',
      """Invalid backup vault format. Expected format:
      `projects/<project>/locations/<location>/backupVaults/<backup-vault-id>`""",
  )

  month_options = {
      'JAN': 'JANUARY',
      'FEB': 'FEBRUARY',
      'MAR': 'MARCH',
      'APR': 'APRIL',
      'MAY': 'MAY',
      'JUN': 'JUNE',
      'JUL': 'JULY',
      'AUG': 'AUGUST',
      'SEP': 'SEPTEMBER',
      'OCT': 'OCTOBER',
      'NOV': 'NOVEMBER',
      'DEC': 'DECEMBER',
  }
  day_options = {
      'MON': 'MONDAY',
      'TUE': 'TUESDAY',
      'WED': 'WEDNESDAY',
      'THU': 'THURSDAY',
      'FRI': 'FRIDAY',
      'SAT': 'SATURDAY',
      'SUN': 'SUNDAY',
  }

  recurrence_options = ['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']
  recurrence_validator = arg_parsers.CustomFunctionValidator(
      lambda arg: arg in recurrence_options,
      'Recurrence should be one of the following: '
      + ', '.join(recurrence_options),
      str,
  )

  def ArgListParser(obj_parser, delim=' '):
    return arg_parsers.ArgList(obj_parser, custom_delim_char=delim)

  parser.add_argument(
      '--backup-rule',
      required=required,
      type=arg_parsers.ArgDict(
          spec={
              'rule-id': rule_id_validator,
              'backup-vault': backup_vault_validator,
              'retention-days': int,
              'recurrence': recurrence_validator,
              'backup-window-start': arg_parsers.BoundedInt(0, 23),
              'backup-window-end': arg_parsers.BoundedInt(1, 24),
              'time-zone': str,
              'hourly-frequency': arg_parsers.BoundedInt(6, 23),
              'days-of-week': ArgListParser(
                  util.OptionsMapValidator(day_options).Parse
              ),
              'days-of-month': ArgListParser(arg_parsers.BoundedInt(1, 31)),
              'months': ArgListParser(
                  util.OptionsMapValidator(month_options).Parse
              ),
          },
          required_keys=[
              'rule-id',
              'backup-vault',
              'recurrence',
              'retention-days',
              'backup-window-start',
              'backup-window-end',
          ],
      ),
      action='append',
      metavar='PROPERTY=VALUE',
      help=("""
          Name of the backup rule. A backup rule defines parameters for when and how a backup is created. This flag can be repeated to create more backup rules.

          Parameters for the backup rule include::
          - rule-id
          - backup-vault
          - retention-days
          - recurrence
          - backup-window-start
          - backup-window-end
          - time-zone

          Along with any of these mutually exclusive flags:
          - hourly-frequency (for HOURLY recurrence, expects value between 6-23)
          - days-of-week (for WEEKLY recurrence, eg: 'MON TUE')
          - days-of-month (for MONTHLY & YEARLY recurrence, eg: '1 7 5' days)
          - months (for YEARLY recurrence, eg: 'JANUARY JUNE')

          This flag can be repeated to specify multiple backup rules.

          E.g., `rule-id=sample-daily-rule,backup-vault=projects/sample-project/locations/us-central1/backupVaults/sample-backup-vault,recurrence=WEEKLY,backup-window-start=2,backup-window-end=14,retention-days=20,days-of-week='SUNDAY MONDAY'`
          """),
  )
