# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of the gcloud genomics operations list command.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """List Genomics operations in a project.

  Prints a table with summary information on operations in the project.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--limit',
                        type=int,
                        help='The maximum number of results to list.')
    f = parser.add_argument(
        '--where',
        default='',
        type=str,
        help='A filter spec for what operations to display.')
    f.detailed_help = ("""\
        A string for filtering operations. The following filter fields are
        supported:

            createTime - The time this job was created, in seconds from the
                         epoch. Can use '>=' and/or '<=' operators.
            status     - Can be 'RUNNING', 'SUCCESS', 'FAILURE' or 'CANCELED'.
                         Only one status may be specified.

        Example:

            'createTime >= 1432140000 AND
             createTime <= 1432150000 AND status = RUNNING'

        To calculate the timestamp as seconds from the epoch, on UNIX-like
        systems (e.g.: Linux, Mac) use the 'date' command:

        $ date --date '20150701' '+%s'

        1435734000

        or with Python (e.g.: Linux, Mac, Windows):

        $ python -c 'from time import mktime, strptime; print int(mktime(strptime("01 July 2015", "%d %B %Y")))'

        1435734000
        """)

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """Run 'operations list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of operations for this project.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    genomics_util.ValidateLimitFlag(args.limit)

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    if args.where:
      args.where += ' AND '

    args.where += 'projectId=%s' % genomics_util.GetProjectId()

    request = genomics_messages.GenomicsOperationsListRequest(
        name='operations',
        filter=args.where)

    return apitools_base.list_pager.YieldFromList(
        apitools_client.operations, request,
        limit=args.limit,
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='operations')

  @genomics_util.ReraiseHttpException
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a list of Operation objects.

    Raises:
      ValueError: if result is None or not a list
    """
    self.format(result)
