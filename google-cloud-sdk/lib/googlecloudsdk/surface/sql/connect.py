# Copyright 2013 Google Inc. All Rights Reserved.

"""Connects to a Cloud SQL instance."""

import datetime
from googlecloudsdk.api_lib.sql import errors
from googlecloudsdk.api_lib.sql import network
from googlecloudsdk.api_lib.sql import operations
from googlecloudsdk.api_lib.sql import validate
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import execution_utils
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import retry
from googlecloudsdk.third_party.apitools.base.protorpclite import util as protorpc_util
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions


def _WhitelistClientIP(instance_ref, sql_client, sql_messages, resources):
  """Add CLIENT_IP to the authorized networks list.

  Makes an API call to add CLIENT_IP to the authorized networks list.
  The server knows to interpret the string CLIENT_IP as the address with which
  the client reaches the server. This IP will be whitelisted for 1 minute.

  Args:
    instance_ref: resources.Resource, The instance we're connecting to.
    sql_client: apitools.BaseApiClient, A working client for the sql version
        to be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    resources: resources.Registry, The registry that can create resource refs
        for the sql version to be used.

  Returns:
    string, The name of the authorized network rule. Callers can use this name
    to find out the IP the client reached the server with.
  Raises:
    HttpException: An http error response was received while executing api
        request.
    ToolException: Server did not complete the whitelisting operation in time.
  """
  datetime_now = datetime.datetime.now(
      protorpc_util.TimeZoneOffset(datetime.timedelta(0)))

  acl_name = 'sql connect at time {0}'.format(datetime_now)
  user_acl = sql_messages.AclEntry(
      name=acl_name,
      expirationTime=datetime_now + datetime.timedelta(minutes=1),
      value='CLIENT_IP')

  try:
    original = sql_client.instances.Get(instance_ref.Request())
  except apitools_exceptions.HttpError as error:
    raise exceptions.HttpException(errors.GetErrorMessage(error))

  original.settings.ipConfiguration.authorizedNetworks.append(user_acl)
  patch_request = sql_messages.SqlInstancesPatchRequest(
      databaseInstance=original,
      project=instance_ref.project,
      instance=instance_ref.instance)
  result = sql_client.instances.Patch(patch_request)

  operation_ref = resources.Create(
      'sql.operations',
      operation=result.name,
      project=instance_ref.project,
      instance=instance_ref.instance)
  message = 'Whitelisting your IP for incoming connection for 1 minute'

  operations.OperationsV1Beta4.WaitForOperation(
      sql_client, operation_ref, message)

  return acl_name


def _GetClientIP(instance_ref, sql_client, acl_name):
  instance_info = sql_client.instances.Get(instance_ref.Request())
  networks = instance_info.settings.ipConfiguration.authorizedNetworks
  client_ip = None
  for net in networks:
    if net.name == acl_name:
      client_ip = net.value
      break
  return instance_info, client_ip


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Connect(base.Command):
  """Connects to a Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'instance',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')

    parser.add_argument(
        '--user', '-u',
        required=False,
        help='Cloud SQL instance user to connect as.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Connects to a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      If no exception is raised this method does not return. A new process is
      started and the original one is killed.
    Raises:
      HttpException: An http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    # Do the mysql executable check first. This way we can return an error
    # faster and not wait for whitelisting IP and other operations.
    mysql_executable = files.FindExecutableOnPath('mysql')
    if not mysql_executable:
      raise exceptions.ToolException(
          'Mysql client not found. Please install a mysql client and make sure '
          'it is in PATH to be able to connect to the database instance.')

    validate.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    acl_name = _WhitelistClientIP(instance_ref, sql_client, sql_messages,
                                  resources)

    # Get the client IP that the server sees. Sadly we can only do this by
    # checking the name of the authorized network rule.
    retryer = retry.Retryer(max_retrials=2, exponential_sleep_multiplier=2)
    try:
      instance_info, client_ip = retryer.RetryOnResult(
          _GetClientIP,
          [instance_ref, sql_client, acl_name],
          should_retry_if=lambda x, s: x[1] is None,  # client_ip is None
          sleep_ms=500)
    except retry.RetryException:
      raise exceptions.ToolException('Could not whitelist client IP. Server '
                                     'did not reply with the whitelisted IP.')

    # Check the version of IP and decide if we need to add ipv4 support.
    ip_type = network.GetIpVersion(client_ip)
    if ip_type == network.IP_VERSION_4:
      if instance_info.settings.ipConfiguration.ipv4Enabled:
        ip_address = instance_info.ipAddresses[0].ipAddress
      else:
        # TODO(svalentin): ask user if we should enable ipv4 addressing
        message = ('It seems your client does not have ipv6 connectivity and '
                   'the database instance does not have an ipv4 address. '
                   'Please request an ipv4 address for this database instance.')
        raise exceptions.ToolException(message)
    elif ip_type == network.IP_VERSION_6:
      ip_address = instance_info.ipv6Address
    else:
      raise exceptions.ToolException('Could not connect to SQL server.')

    # We have everything we need, time to party!
    mysql_args = [mysql_executable, '-h', ip_address]
    if args.user:
      mysql_args.extend(['-u', args.user])
    mysql_args.append('-p')
    execution_utils.Exec(mysql_args)
