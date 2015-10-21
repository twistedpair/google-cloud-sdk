# Copyright 2013 Google Inc. All Rights Reserved.

"""Lists all SSL certs for a Cloud SQL instance."""


from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer

from googlecloudsdk.shared.sql import errors
from googlecloudsdk.shared.sql import validate


class _BaseList(object):
  """Base class for sql ssl_certs list."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    pass

  @errors.ReraiseHttpException
  def Run(self, args):
    """Lists all SSL certs for a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object that has the list of sslCerts resources if the api request
      was successful.
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

    result = sql_client.sslCerts.List(sql_messages.SqlSslCertsListRequest(
        project=instance_ref.project,
        instance=instance_ref.instance))
    return iter(result.items)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('sql.sslCerts', result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class List(_BaseList, base.Command):
  """Lists all SSL certs for a Cloud SQL instance."""
  pass


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class ListBeta(_BaseList, base.Command):
  """Lists all SSL certs for a Cloud SQL instance."""
  pass
