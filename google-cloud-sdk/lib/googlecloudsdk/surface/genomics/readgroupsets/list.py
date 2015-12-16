# Copyright 2015 Google Inc. All Rights Reserved.

"""readgroupsets list command."""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """List genomics read group sets in a dataset.

  Prints a table with summary information on read group sets in the dataset.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument(
        'dataset_ids',
        nargs='+',
        help="""Restrict the query to read group sets within the given datasets.
             At least one ID must be provided.""")

    parser.add_argument(
        '--name',
        help="""Only return read group sets for which a substring of the
             name matches this string.""")

    parser.add_argument(
        '--limit',
        type=int,
        help='The maximum number of results to list.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """Run 'readgroupsets list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of read group sets matching the given dataset ids.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    genomics_util.ValidateLimitFlag(args.limit)

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    req_class = (self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
                 .SearchReadGroupSetsRequest)
    request = req_class(
        name=args.name,
        datasetIds=args.dataset_ids)
    return apitools_base.list_pager.YieldFromList(
        apitools_client.readgroupsets,
        request,
        method='Search',
        limit=args.limit,
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='readGroupSets')

  @genomics_util.ReraiseHttpException
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a list of ReadGroupSet objects.

    Raises:
      ValueError: if result is None or not a list
    """
    list_printer.PrintResourceList('genomics.readGroupSets', result)
