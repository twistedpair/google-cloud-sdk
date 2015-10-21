# Copyright 2013 Google Inc. All Rights Reserved.

"""Retrieves information about an SSL cert for a Cloud SQL instance."""


from googlecloudsdk.calliope import base

from googlecloudsdk.shared.sql import cert
from googlecloudsdk.shared.sql import errors
from googlecloudsdk.shared.sql import validate


class _BaseGet(object):
  """Base class for sql ssl_certs list."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'common_name',
        help='User supplied name. Constrained to [a-zA-Z.-_ ]+.')

  @errors.ReraiseHttpException
  def Run(self, args):
    """Retrieves information about an SSL cert for a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the sslCerts resource if the api request was
      successful.
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

    # sha1fingerprint, so that things can work with the resource parser.
    return cert.GetCertFromName(sql_client, sql_messages,
                                instance_ref, args.common_name)

  def Display(self, unused_args, result):
    """Display prints information about what just happened to stdout.

    Args:
      unused_args: The same as the args in Run.
      result: A dict object representing the sslCert resource if the api
      request was successful.
    """
    self.format(result)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Get(_BaseGet, base.Command):
  """Retrieves information about an SSL cert for a Cloud SQL instance."""
  pass


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class GetBeta(_BaseGet, base.Command):
  """Retrieves information about an SSL cert for a Cloud SQL instance."""
  pass
