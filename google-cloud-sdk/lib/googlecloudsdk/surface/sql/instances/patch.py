# Copyright 2013 Google Inc. All Rights Reserved.

"""Updates the settings of a Cloud SQL instance."""

from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import instances
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resource_printer
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class _BasePatch(object):
  """Updates the settings of a Cloud SQL instance."""

  @classmethod
  def Args(cls, parser):
    """Args is called by calliope to gather arguments for this command.

    Please add arguments in alphabetical order except for no- or a clear-
    pair for that argument which can follow the argument itself.
    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        '--activation-policy',
        required=False,
        choices=['ALWAYS', 'NEVER', 'ON_DEMAND'],
        help='The activation policy for this instance. This specifies when the '
        'instance should be activated and is applicable only when the '
        'instance state is RUNNABLE.')
    parser.add_argument(
        '--assign-ip',
        action='store_true',
        default=None,  # Tri-valued: None => don't change the setting.
        help='The instance must be assigned an IP address.')
    gae_apps_group = parser.add_mutually_exclusive_group()
    gae_apps_group.add_argument(
        '--authorized-gae-apps',
        type=arg_parsers.ArgList(min_length=1),
        metavar='APP',
        required=False,
        action=arg_parsers.FloatingListValuesCatcher(),
        help='A list of App Engine app IDs that can access this instance.')
    gae_apps_group.add_argument(
        '--clear-gae-apps',
        required=False,
        action='store_true',
        help=('Specified to clear the list of App Engine apps that can access '
              'this instance.'))
    networks_group = parser.add_mutually_exclusive_group()
    networks_group.add_argument(
        '--authorized-networks',
        type=arg_parsers.ArgList(min_length=1),
        metavar='NETWORK',
        required=False,
        action=arg_parsers.FloatingListValuesCatcher(),
        help='The list of external networks that are allowed to connect to the '
        'instance. Specified in CIDR notation, also known as \'slash\' '
        'notation (e.g. 192.168.100.0/24).')
    networks_group.add_argument(
        '--clear-authorized-networks',
        required=False,
        action='store_true',
        help='Clear the list of external networks that are allowed to connect '
        'to the instance.')
    backups_group = parser.add_mutually_exclusive_group()
    backups_group.add_argument(
        '--backup-start-time',
        required=False,
        help='The start time of daily backups, specified in the 24 hour format '
        '- HH:MM, in the UTC timezone.')
    backups_group.add_argument(
        '--no-backup',
        required=False,
        action='store_true',
        help='Specified if daily backup should be disabled.')
    database_flags_group = parser.add_mutually_exclusive_group()
    database_flags_group.add_argument(
        '--database-flags',
        type=arg_parsers.ArgDict(min_length=1),
        metavar='FLAG=VALUE',
        required=False,
        action=arg_parsers.FloatingListValuesCatcher(),
        help='A space-separated list of database flags to set on the instance. '
        'Use an equals sign to separate flag name and value. Flags without '
        'values, like skip_grant_tables, can be written out without a value '
        'after, e.g., `skip_grant_tables=`. Use on/off for '
        'booleans. View the Instance Resource API for allowed flags. '
        '(e.g., `--database-flags max_allowed_packet=55555 skip_grant_tables= '
        'log_output=1`)')
    database_flags_group.add_argument(
        '--clear-database-flags',
        required=False,
        action='store_true',
        help='Clear the database flags set on the instance. '
        'WARNING: Instance will be restarted.')
    parser.add_argument(
        '--enable-bin-log',
        action='store_true',
        default=None,  # Tri-valued: None => don't change the setting.
        help='Enable binary log. If backup configuration is disabled, binary '
        'log should be disabled as well.')
    parser.add_argument(
        '--follow-gae-app',
        required=False,
        help='The App Engine app this instance should follow. It must be in '
        'the same region as the instance. '
        'WARNING: Instance may be restarted.')
    parser.add_argument(
        '--gce-zone',
        required=False,
        help='The preferred Compute Engine zone (e.g. us-central1-a, '
        'us-central1-b, etc.). '
        'WARNING: Instance may be restarted.')
    parser.add_argument(
        'instance',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')
    parser.add_argument(
        '--pricing-plan',
        '-p',
        required=False,
        choices=['PER_USE', 'PACKAGE'],
        help='The pricing plan for this instance.')
    parser.add_argument(
        '--replication',
        required=False,
        choices=['SYNCHRONOUS', 'ASYNCHRONOUS'],
        help='The type of replication this instance uses.')
    parser.add_argument(
        '--require-ssl',
        action='store_true',
        default=None,  # Tri-valued: None => don't change the setting.
        help='mysqld should default to \'REQUIRE X509\' for users connecting '
        'over IP.')
    parser.add_argument(
        '--tier',
        '-t',
        required=False,
        help='The tier of service for this instance, for example D0, D1. '
        'WARNING: Instance will be restarted.')
    parser.add_argument(
        '--enable-database-replication',
        action='store_true',
        default=None,  # Tri-valued: None => don't change the setting.
        help='Enable database replication. Applicable only '
        'for read replica instance(s). WARNING: Instance will be restarted.')
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.')
    parser.add_argument(
        '--diff',
        action='store_true',
        help='Show what changed as a result of the update.')

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.
      result: A dict object representing the operations resource describing the
      patch operation if the patch was successful.
    """
    if args.diff:
      resource_printer.Print(result, 'text')

  def _PrintAndConfirmWarningMessage(self, args):
    """Print and confirm warning indicating the effect of applying the patch."""
    continue_msg = None
    if any([args.tier, args.database_flags, args.clear_database_flags,
            args.enable_database_replication is not None]):
      continue_msg = ('WARNING: This patch modifies a value that requires '
                      'your instance to be restarted. Submitting this patch '
                      'will immediately restart your instance if it\'s running.'
                     )
    else:
      if any([args.follow_gae_app, args.gce_zone]):
        continue_msg = ('WARNING: This patch modifies the zone your instance '
                        'is set to run in, which may require it to be moved. '
                        'Submitting this patch will restart your instance '
                        'if it is running in a different zone.')

    if continue_msg and not console_io.PromptContinue(continue_msg):
      raise exceptions.ToolException('canceled by the user.')

  def _GetConfirmedClearedFields(self, args, patch_instance):
    """Clear fields according to args and confirm with user."""
    cleared_fields = []

    if args.clear_gae_apps:
      cleared_fields.append('settings.authorizedGaeApplications')
    if args.clear_authorized_networks:
      cleared_fields.append('settings.ipConfiguration.authorizedNetworks')
    if args.clear_database_flags:
      cleared_fields.append('settings.databaseFlags')

    log.status.write(
        'The following message will be used for the patch API method.\n')
    log.status.write(
        apitools_base.MessageToJson(
            patch_instance, include_fields=cleared_fields)+'\n')

    self._PrintAndConfirmWarningMessage(args)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Patch(_BasePatch, base.Command):
  """Updates the settings of a Cloud SQL instance."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Updates settings of a Cloud SQL instance using the patch api method.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the patch
      operation if the patch was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """

    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    original_instance_resource = sql_client.instances.Get(
        instance_ref.Request())

    patch_instance = instances.InstancesV1Beta3.ConstructInstanceFromArgs(
        sql_messages, args, original=original_instance_resource)
    patch_instance.project = instance_ref.project
    patch_instance.instance = instance_ref.instance

    cleared_fields = self._GetConfirmedClearedFields(args, patch_instance)

    with sql_client.IncludeFields(cleared_fields):
      result = sql_client.instances.Patch(patch_instance)

    operation_ref = resources.Create(
        'sql.operations',
        operation=result.operation,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta3.WaitForOperation(
        sql_client, operation_ref, 'Patching Cloud SQL instance')

    log.UpdatedResource(instance_ref)

    if args.diff:
      changed_instance_resource = sql_client.instances.Get(
          instance_ref.Request())
      return resource_printer.ResourceDiff(
          original_instance_resource, changed_instance_resource)

    return sql_client.instances.Get(instance_ref.Request())


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class PatchBeta(_BasePatch, base.Command):
  """Updates the settings of a Cloud SQL instance."""

  @errors.ReraiseHttpException
  def Run(self, args):
    """Updates settings of a Cloud SQL instance using the patch api method.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the operations resource describing the patch
      operation if the patch was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """

    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    original_instance_resource = sql_client.instances.Get(
        instance_ref.Request())

    patch_instance = instances.InstancesV1Beta3.ConstructInstanceFromArgs(
        sql_messages, args, original=original_instance_resource)
    patch_instance.project = instance_ref.project
    patch_instance.name = instance_ref.instance

    cleared_fields = self._GetConfirmedClearedFields(args, patch_instance)

    with sql_client.IncludeFields(cleared_fields):
      result_operation = sql_client.instances.Patch(patch_instance)

    operation_ref = resources.Create(
        'sql.operations',
        operation=result_operation.name,
        project=instance_ref.project,
        instance=instance_ref.instance,
    )

    if args.async:
      return sql_client.operations.Get(operation_ref.Request())

    operations.OperationsV1Beta4.WaitForOperation(
        sql_client, operation_ref, 'Patching Cloud SQL instance')

    log.UpdatedResource(instance_ref)

    if args.diff:
      changed_instance_resource = sql_client.instances.Get(
          instance_ref.Request())
      return resource_printer.ResourceDiff(
          original_instance_resource, changed_instance_resource)

    return sql_client.instances.Get(instance_ref.Request())
