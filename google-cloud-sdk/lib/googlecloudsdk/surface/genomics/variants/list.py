# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variants list.
"""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """Lists variants that match the search criteria.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('--limit',
                        type=int,
                        help='The maximum number of variants to return.')
    parser.add_argument('--limit-calls',
                        type=int,
                        help=('The maximum number of calls to return.'
                              'At least one variant will be returned even '
                              'if it exceeds this limit.'))
    parser.add_argument('--variant-set-id',
                        type=str,
                        help=('Restrict the list to variants in this variant '
                              'set. If omitted, a call set id must be included '
                              'in the request.'))
    parser.add_argument('--call-set-ids',
                        type=arg_parsers.ArgList(min_length=1),
                        default=[],
                        help=('Restrict the list to variants which have calls '
                              'from the listed call sets. If omitted, a '
                              '--variant-set-id must be specified.'))
    parser.add_argument('--variant-name',
                        type=str,
                        help=('Only return variants which have exactly this '
                              'name.'))
    parser.add_argument('--reference-name',
                        type=str,
                        help='Only return variants in this reference sequence.')
    parser.add_argument('--start',
                        type=long,
                        help=('The beginning of the window (0-based, '
                              'inclusive) for which overlapping variants '
                              'should be returned. If unspecified, defaults '
                              'to 0.'))
    parser.add_argument('--end',
                        type=long,
                        help=('The end of the window, 0-based exclusive. If '
                              'unspecified or 0, defaults to the length of '
                              'the reference.'))

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      A list of variants that meet the search criteria.
    """
    genomics_util.ValidateLimitFlag(args.limit)
    genomics_util.ValidateLimitFlag(args.limit_calls, 'limit_calls')

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    req_class = (self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
                 .SearchVariantsRequest)
    request = req_class(
        variantSetIds=[args.variant_set_id],
        callSetIds=args.call_set_ids,
        variantName=args.variant_name,
        referenceName=args.reference_name,
        start=args.start,
        end=args.end,
        maxCalls=args.limit_calls)
    return apitools_base.list_pager.YieldFromList(
        apitools_client.variants,
        request,
        limit=args.limit,
        method='Search',
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='variants')

  @genomics_util.ReraiseHttpException
  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a list of Variant objects.

    Raises:
      ValueError: if result is None or not a list
    """
    list_printer.PrintResourceList('genomics.variants', result)
