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

import argparse
import itertools
from typing import Any

import frozendict
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.backupdr import util
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core import properties


MONTH_OPTIONS = frozendict.frozendict({
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
})
DAY_OPTIONS = frozendict.frozendict({
    'MON': 'MONDAY',
    'TUE': 'TUESDAY',
    'WED': 'WEDNESDAY',
    'THU': 'THURSDAY',
    'FRI': 'FRIDAY',
    'SAT': 'SATURDAY',
    'SUN': 'SUNDAY',
})
RECURRENCE_OPTIONS = ('HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')
WEEK_OPTIONS = ('FIRST', 'SECOND', 'THIRD', 'FOURTH', 'LAST')
BACKUP_RULE_COMMON_HELP_TEXT = """
Parameters for the backup rule include:

*rule-id*::: Name of the backup rule. The name must be unique and
start with a lowercase letter followed by up to 62 lowercase letters,
numbers, or hyphens.

*retention-days*::: Duration for which backup data should be
retained. It must be defined in "days". The value should be greater
than or equal to the enforced retention period set for the backup vault.

*recurrence*::: Frequency for the backup schedule. It must be either:
HOURLY, DAILY, WEEKLY, MONTHLY or YEARLY.

*backup-window-start*::: Start time of the interval during which
backup jobs should be executed. It can be defined as backup-window-start=2,
that means backup window starts at 2 a.m. The start time and end time must
have an interval of 6 hours.

*backup-window-end*::: End time of the interval during which backup
jobs should be executed. It can be defined as backup-window-end=14,
that means backup window ends at 2 p.m. The start time and end time
must have an interval of 6 hours.

Jobs are queued at the beginning of the window and will be marked as
`SKIPPED` if they do not start by the end time. Jobs that are
in progress will not be canceled at the end time.

*time-zone*::: The time zone to be used for the backup schedule.
The value must exist in the
[IANA tz database](https://www.iana.org/time-zones).
The default value is UTC. E.g., Europe/Paris

::: Following flags are mutually exclusive:

*hourly-frequency*::: Frequency for hourly backups. An hourly
frequency of 2 means backup jobs will run every 2 hours from start
time till the end time defined. The hourly frequency must be between
4 and 23. The value is needed only if recurrence type is HOURLY.

*days-of-week*::: Days of the week when the backup job should be
executed. The value is needed if recurrence type is WEEKLY.
E.g., MONDAY,TUESDAY

*days-of-month*::: Days of the month when the backup job should
be executed. The value is needed only if recurrence type is YEARLY.
E.g.,"1,5,14"

*months*::: Month for the backup schedule. The value is needed only if
recurrence type is YEARLY. E.g., JANUARY, MARCH

*week-day-of-month*::: Recurring day of the week in the month or
year when the backup job should be executed. E.g. FIRST-SUNDAY, THIRD-MONDAY.
The value can only be provided if the recurrence type is MONTHLY or YEARLY.
Allowed values for the number of week - FIRST, SECOND, THIRD, FOURTH, LAST.
Allowed values for days of the week - MONDAY to SUNDAY.

::: E.g., "rule-id=sample-daily-rule,recurrence=WEEKLY,backup-window-start=2,backup-window-end=14,retention-days=20,days-of-week='SUNDAY MONDAY'"
"""


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

  AddResourceType(
      parser,
      """Type of resource to which the backup plan should be applied.
          E.g., `compute.<UNIVERSE_DOMAIN>.com/Instance` """,
  )


def AddUpdateBackupPlanAssociationFlags(parser):
  """Adds flags required to update a backup plan association."""
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'BACKUP_PLAN_ASSOCIATION',
              GetBackupPlanAssociationResourceSpec(),
              'Backup plan association to be updated. To update'
              " backup plan associations in a project that's different from the"
              ' backup plan, use the --workload-project flag.',
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--backup-plan',
              GetBackupPlanResourceSpec(),
              'Name of the specific backup plan to be applied to the backup'
              ' plan association. E.g.,'
              ' projects/sample-project/locations/us-central1/backupPlans/'
              'sample-backup-plan',
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


def AddNetwork(parser, required=False):
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
      action=actions.DeprecationAction('--network', removed=False),
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


def GetBackupVaultResourceSpec():
  return concepts.ResourceSpec(
      'backupdr.projects.locations.backupVaults',
      resource_name='Backup Vault',
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def LocationAttributeConfig(arg_name='location', default=None):
  """Creates location attribute config."""
  fallthroughs = []
  if default:
    fallthroughs.append(
        deps.Fallthrough(
            lambda: default,
            'Defaults to all locations',
        )
    )

  return concepts.ResourceParameterAttributeConfig(
      name=arg_name,
      fallthroughs=fallthroughs,
      help_text='The location of the {resource}.',
  )


def GetLocationResourceSpec(resource_name='location', default=None):
  return concepts.ResourceSpec(
      'backupdr.projects.locations',
      resource_name=resource_name,
      locationsId=LocationAttributeConfig(default=default),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
  )


def AddLocationResourceArg(parser, help_text, default=None, required=True):
  """Adds an argument for location to parser."""
  name = '--location'
  override = None
  if default == 'global':
    override = {'location': ''}

  concept_parsers.ConceptParser.ForResource(
      name,
      GetLocationResourceSpec(default=default),
      help_text,
      flag_name_overrides=override,
      required=required,
  ).AddToParser(parser)


def AddNoAsyncFlag(parser):
  """Adds the --no-async flag to the given parser."""
  help_text = 'Wait for the operation in progress to complete.'
  parser.add_argument('--no-async', action='store_true', help=help_text)


def AddIgnoreInactiveDatasourcesFlag(parser):
  """Adds a --ignore-inactive-datasources flag to the given parser."""
  help_text = (
      'If set, the following restrictions against deletion of'
      ' the backup vault instance can be overridden:'
      ' * deletion of a backup vault instance containing no backups,'
      'but still contains empty datasources.'
  )
  parser.add_argument(
      '--ignore-inactive-datasources', action='store_true', help=help_text
  )


def AddIgnoreBackupPlanReferencesFlag(parser):
  """Adds a --ignore-backup-plan-references flag to the given parser."""
  help_text = (
      'If set, the following restrictions against deletion of'
      ' the backup vault instance can be overridden:'
      ' * deletion of a backup vault instance being actively referenced'
      ' by a backup plan.'
  )
  parser.add_argument(
      '--ignore-backup-plan-references', action='store_true', help=help_text
  )


def AddForceUpdateFlag(parser):
  """Adds a --force-update flag to the given parser."""
  help_text = (
      'If set, allow update to extend the minimum enforced retention for backup'
      ' vault. This overrides the restriction against conflicting retention'
      ' periods. This conflict may occur when the expiration schedule defined'
      ' by the associated backup plan is shorter than the minimum retention set'
      ' by the backup vault.'
  )
  parser.add_argument('--force-update', action='store_true', help=help_text)


def AddBackupPlanResourceArg(parser, help_text):
  """Adds an argument for backup plan to parser."""
  name = 'backup_plan'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetBackupPlanResourceSpec(),
      help_text,
      required=True,
  ).AddToParser(parser)


def AddBackupPlanResourceArgWithBackupVault(parser, help_text):
  """Adds an argument for backup plan & backup vault to parser."""
  concept_parsers.ConceptParser(
      [
          presentation_specs.ResourcePresentationSpec(
              'BACKUP_PLAN',
              GetBackupPlanResourceSpec(),
              help_text,
              required=True,
          ),
          presentation_specs.ResourcePresentationSpec(
              '--backup-vault',
              GetBackupVaultResourceSpec(),
              """The backup vault where the backups gets stored using this
              backup plan.
              """,
              flag_name_overrides={
                  'location': '',
              },
              required=True,
          ),
      ],
      command_level_fallthroughs={
          '--backup-vault.location': ['BACKUP_PLAN.location'],
      },
  ).AddToParser(parser)


def AddEnforcedRetention(parser, required):
  """Adds a positional enforced-retention argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    required: Whether or not --backup-min-enforced-retention is required.
  """
  parser.add_argument(
      '--backup-min-enforced-retention',
      required=required,
      type=arg_parsers.Duration(
          lower_bound='0', upper_bound='36159d', parsed_unit='s'
      ),
      help=(
          'Backups will be kept for this minimum period before they can be'
          ' deleted. Once the effective time is reached, the enforced retention'
          ' period cannot be decreased or removed. The value must be specified'
          ' in relative time format (e.g. p1d, p1m, p1m1d).'
      ),
  )


def AddBackupRetentionInheritance(parser):
  """Adds the --backup-retention-inheritance flag to the given parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--backup-retention-inheritance',
      required=False,
      choices=[
          'inherit-vault-retention',
          'match-backup-expire-time',
      ],
      hidden=True,
      help=(
          'The inheritance mode for enforced retention end time of the backup'
          ' within this backup vault. Once set, the inheritance mode cannot be'
          ' changed. Default is inherit-vault-retention. If set to'
          ' inherit-vault-retention, the backup retention period will be'
          ' inherited from the backup vault. If set to'
          ' match-backup-expire-time, the backup retention period will  be the'
          ' same as the backup expiration time. '
      ),
  )


def AddBackupEnforcedRetentionEndTime(parser):
  """Adds the --enforced-retention-end-time flag to the given parser."""
  help_text = """
   Backups cannot be deleted until this time or later. This period can be extended, but not shortened.
   It should be specified in the format of "YYYY-MM-DD".

   * For backup configured with a backup appliance, there are additional restrictions:
     1. Enforced retention cannot be extended past the expiry time.
     2. Enforced retention can only be updated for finalized backups.
  """

  parser.add_argument(
      '--enforced-retention-end-time',
      required=True,
      type=arg_parsers.Datetime.Parse,
      help=help_text,
  )


def AddBackupExpireTime(parser):
  """Adds the --expire-time flag to the given parser."""
  help_text = """
   The date when this backup is automatically expired. This date can be extended, but not shortened. It should be specified in the format of "YYYY-MM-DD"."""
  parser.add_argument(
      '--expire-time',
      required=True,
      type=arg_parsers.Datetime.Parse,
      help=help_text,
      hidden=True,
  )


def AddOutputFormat(parser, output_format):
  parser.display_info.AddFormat(output_format)
  parser.display_info.AddTransforms({
      'backupMinimumEnforcedRetentionDuration': util.TransformEnforcedRetention,
  })


def AddDescription(parser, help_text=None):
  """Adds the --description flag to the given parser."""
  final_help_text = (
      help_text
      or 'Optional description for the backup vault (2048 characters or less).'
  )
  parser.add_argument('--description', type=str, help=final_help_text)


def AddLabels(parser, help_text=None):
  """Adds the --labels flag to the given parser."""
  final_help_text = (
      help_text
      or 'Optional resource labels to represent metadata provided by the user.'
  )
  parser.add_argument(
      '--labels',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help=final_help_text,
  )


def AddEffectiveTime(parser):
  """Adds the --effective-time flag to the given parser."""
  help_text = (
      'The time at which the enforced retention period becomes locked. This'
      ' flag is mutually exclusive with --unlock-backup-min-enforced-retention.'
  )
  parser.add_argument(
      '--effective-time',
      type=arg_parsers.Datetime.Parse,
      help=help_text,
  )


def AddAllowMissing(parser, resource):
  """Adds the --allow-missing flag to the given parser for delete operation to return success and perform no action when there is no matching resource."""
  help_text = (
      'Allow idempotent deletion of {resource}. The request will still succeed'
      ' in case the {resource} does not exist.'
  )
  parser.add_argument(
      '--allow-missing',
      action='store_true',
      help=help_text.format(resource=resource),
  )


def AddUnlockBackupMinEnforcedRetention(parser):
  """Adds the --unlock-backup-min-enforced-retention flag to the given parser."""
  help_text = (
      'Removes the lock on the backup minimum enforced retention period, and'
      ' resets the effective time. When unlocked, the enforced retention period'
      ' can be changed at any time. This flag is mutually exclusive with'
      ' --effective-time.'
  )
  parser.add_argument(
      '--unlock-backup-min-enforced-retention',
      action='store_true',
      help=help_text,
  )


def AddBackupVaultAccessRestrictionEnumFlag(parser, command: str):
  """Adds Backup Vault's Access Restriction flag to the parser."""
  choices = [
      'within-project',
      'within-org',
      'unrestricted',
      'within-org-but-unrestricted-for-ba',
  ]
  if command == 'create':
    help_text = (
        'Authorize certain sources and destinations for data being sent into,'
        ' or restored from, the backup vault being created. This choice '
        ' determines the type of resources that can be stored.'
        ' Restricting access to within your project or organization limits'
        ' the resources to those managed through the Google Cloud console'
        ' (e.g., Compute Engine VMs). Unrestricted access is required for'
        ' resources managed through the management console (e.g., VMware'
        ' Engine VMs, databases, and file systems).'
    )
    default = 'within-org'
    hidden = False
  else:
    help_text = """
Authorize certain sources and destinations for data being sent into, or restored from the current backup vault.

Access restrictions can be modified to be more or less restrictive.

    ::: More restrictive access restriction update will fail by default if there will be non compliant Data Sources.
    To allow such updates, use the --force-update-access-restriction flag.
    :::  For Google Cloud Console resources, the following changes are allowed to make access restrictions more restrictive:
        *   `UNRESTRICTED` to `WITHIN_PROJECT` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA` / `WITHIN_ORGANIZATION`
        *   `WITHIN_PROJECT` to `WITHIN_ORGANIZATION` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA`

    ::: For Management Server resources, the following changes are allowed to make access restrictions more restrictive:
        *   `UNRESTRICTED` to `WITHIN_PROJECT` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA` / `WITHIN_ORGANIZATION`
        *   `WITHIN_PROJECT` to `WITHIN_ORGANIZATION` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA`

    :::   For both Google Cloud Console and Management Server resources, the following changes are allowed to make access restrictions more restrictive:
        *   `UNRESTRICTED` to `WITHIN_PROJECT` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA` / `WITHIN_ORGANIZATION`
        *   `WITHIN_PROJECT` to `WITHIN_ORGANIZATION` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA`

    ::: For Google Cloud Console resources,  the following changes are allowed to make access restrictions less restrictive:
        *   `WITHIN_ORGANIZATION` to `UNRESTRICTED` / `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA`
        *   `WITHIN_PROJECT` to `UNRESTRICTED`
        *   `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA` to `UNRESTRICTED`

    ::: For Management Server resources, the following changes are allowed to make access restrictions less restrictive:
        *   `WITHIN_ORG_BUT_UNRESTRICTED_FOR_BA` to `UNRESTRICTED`
    """
    default = None
    hidden = True

  parser.add_argument(
      '--access-restriction',
      choices=choices,
      default=default,
      hidden=hidden,
      help=help_text,
  )


def AddForceUpdateAccessRestriction(parser):
  """Adds the --force-update-access-restriction flag to the given parser."""
  help_text = (
      'If set, the access restriction can be updated even if there are'
      ' non-compliant data sources. Backups for those data sources will fail'
      ' afterward.'
  )
  parser.add_argument(
      '--force-update-access-restriction',
      action='store_true',
      help=help_text,
      hidden=True,
  )


def AddResourceType(parser, help_text):
  """Adds a positional resource-type argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    help_text: Help text for the resource-type argument.
  """
  parser.add_argument(
      '--resource-type',
      required=True,
      type=str,
      help=help_text,
  )


def AddLogRetentionDays(parser, hidden=True):
  """Adds a positional log-retention-days argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
    hidden: Whether or not --log-retention-days is hidden. Default is True.
  """
  parser.add_argument(
      '--log-retention-days',
      required=False,
      hidden=hidden,
      type=int,
      help=("""Configures how long logs will be stored. It is defined in "days".
          This value should be greater than or equal to minimum enforced log
          retention duration of the backup vault."""),
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

  week_day_of_month_options = [
      f'{week}-{day}'
      for week, day in itertools.product(WEEK_OPTIONS, DAY_OPTIONS.values())
  ]

  def ArgListParser(obj_parser: Any, delim: str = ' ') -> arg_parsers.ArgList:
    return arg_parsers.ArgList(obj_parser, custom_delim_char=delim)

  recurrence_validator = util.GetOneOfValidator(
      'recurrence', RECURRENCE_OPTIONS
  )

  parser.add_argument(
      '--backup-rule',
      required=required,
      type=arg_parsers.ArgDict(
          spec={
              'rule-id': rule_id_validator,
              'retention-days': int,
              'recurrence': recurrence_validator,
              'backup-window-start': arg_parsers.BoundedInt(0, 23),
              'backup-window-end': arg_parsers.BoundedInt(1, 24),
              'time-zone': str,
              'hourly-frequency': int,
              'days-of-week': ArgListParser(
                  util.OptionsMapValidator(DAY_OPTIONS).Parse
              ),
              'days-of-month': ArgListParser(arg_parsers.BoundedInt(1, 31)),
              'months': ArgListParser(
                  util.OptionsMapValidator(MONTH_OPTIONS).Parse
              ),
              'week-day-of-month': util.GetOneOfValidator(
                  'week-day-of-month', week_day_of_month_options
              ),
          },
          required_keys=[
              'rule-id',
              'recurrence',
              'retention-days',
              'backup-window-start',
              'backup-window-end',
          ],
      ),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          f"""Backup rule that defines parameters for when and how a backup
          is created. This flag can be repeated to create more backup rules.

          {BACKUP_RULE_COMMON_HELP_TEXT}
          """
      ),
  )


def AddUpdateBackupRule(parser: argparse.ArgumentParser):
  """Adds a positional backup-rule argument to parser.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """

  rule_id_validator = arg_parsers.RegexpValidator(
      r'[a-z][a-z0-9-]{0,62}',
      'Invalid rule-id. This human-readable name must be unique and start with'
      ' a lowercase letter followed by up to 62 lowercase letters, numbers, or'
      ' hyphens',
  )

  week_day_of_month_options = [
      f'{week}-{day}'
      for week, day in itertools.product(WEEK_OPTIONS, DAY_OPTIONS.values())
  ]

  def ArgListParser(obj_parser: Any, delim: str = ' ') -> arg_parsers.ArgList:
    return arg_parsers.ArgList(obj_parser, custom_delim_char=delim)

  recurrence_validator = util.GetOneOfValidator(
      'recurrence', RECURRENCE_OPTIONS
  )

  parser.add_argument(
      '--backup-rule',
      type=arg_parsers.ArgDict(
          spec={
              'rule-id': rule_id_validator,
              'retention-days': int,
              'recurrence': recurrence_validator,
              'backup-window-start': arg_parsers.BoundedInt(0, 23),
              'backup-window-end': arg_parsers.BoundedInt(1, 24),
              'time-zone': str,
              'hourly-frequency': int,
              'days-of-week': ArgListParser(
                  util.OptionsMapValidator(DAY_OPTIONS).Parse
              ),
              'days-of-month': ArgListParser(arg_parsers.BoundedInt(1, 31)),
              'months': ArgListParser(
                  util.OptionsMapValidator(MONTH_OPTIONS).Parse
              ),
              'week-day-of-month': util.GetOneOfValidator(
                  'week-day-of-month', week_day_of_month_options
              ),
          },
          required_keys=['rule-id'],
      ),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          f"""Full definition of an existing backup rule with updated values.
          The existing backup rule is replaced by this new set of values.
          This flag can be repeated to update multiple backup rules.
          It is not allowed to pass the same rule-id in this flag more than once
          in the same command.

          {BACKUP_RULE_COMMON_HELP_TEXT}
          """
      ),
  )


def AddAddBackupRule(parser):
  """Adds flags required to add a backup rule.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """

  rule_id_validator = arg_parsers.RegexpValidator(
      r'[a-z][a-z0-9-]{0,62}',
      'Invalid rule-id. This human-readable name must be unique and start with'
      ' a lowercase letter followed by up to 62 lowercase letters, numbers, or'
      ' hyphens',
  )

  week_day_of_month_options = [
      f'{week}-{day}'
      for week, day in itertools.product(WEEK_OPTIONS, DAY_OPTIONS.values())
  ]

  def ArgListParser(obj_parser: Any, delim: str = ' ') -> arg_parsers.ArgList:
    return arg_parsers.ArgList(obj_parser, custom_delim_char=delim)

  recurrence_validator = util.GetOneOfValidator(
      'recurrence', RECURRENCE_OPTIONS
  )

  parser.add_argument(
      '--add-backup-rule',
      required=False,
      type=arg_parsers.ArgDict(
          spec={
              'rule-id': rule_id_validator,
              'retention-days': int,
              'recurrence': recurrence_validator,
              'backup-window-start': arg_parsers.BoundedInt(0, 23),
              'backup-window-end': arg_parsers.BoundedInt(1, 24),
              'time-zone': str,
              'hourly-frequency': int,
              'days-of-week': ArgListParser(
                  util.OptionsMapValidator(DAY_OPTIONS).Parse
              ),
              'days-of-month': ArgListParser(arg_parsers.BoundedInt(1, 31)),
              'months': ArgListParser(
                  util.OptionsMapValidator(MONTH_OPTIONS).Parse
              ),
              'week-day-of-month': util.GetOneOfValidator(
                  'week-day-of-month', week_day_of_month_options
              ),
          },
          required_keys=[
              'rule-id',
              'recurrence',
              'retention-days',
              'backup-window-start',
              'backup-window-end',
          ],
      ),
      action='append',
      metavar='PROPERTY=VALUE',
      help=(
          """Parameters of backup rule to be added to the Backup Plan. This flag can be repeated to add more backup rules.
          """
      ),
  )


def AddRemoveBackupRule(parser):
  """Adds flags required to remove a backup rule.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--remove-backup-rule',
      required=False,
      type=str,
      help=(
          """Name of an existing backup rule to be removed from the Backup Plan. This flag can be repeated to remove more backup rules.
          """
      ),
      action='append',
      metavar='RULE-ID',
  )


def AddBackupRulesFromFile(parser):
  """Adds flags required to add backup rules from a file.

  Args:
    parser: argparse.Parser: Parser object for command line inputs.
  """
  parser.add_argument(
      '--backup-rules-from-file',
      required=False,
      type=arg_parsers.FileContents(),
      help='Path to a YAML or JSON file containing backup rules.',
  )
