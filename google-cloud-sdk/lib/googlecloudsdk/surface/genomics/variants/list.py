# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics variants list.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.third_party.apitools.base.py import list_pager

_COLUMNS = [
    ('VARIANT_SET_ID', 'variantSetId'),
    ('REFERENCE_NAME', 'referenceName'),
    ('START', 'start'),
    ('END', 'end'),
    ('REFERENCE_BASES', 'referenceBases'),
    ('ALTERNATE_BASES', 'alternateBases'),
]
_PROJECTIONS = [
    '{0}:label={1}'.format(field, col) for col, field in _COLUMNS
]
_API_FIELDS = ','.join(['nextPageToken'] + [
    'variants.' + f for _, f in _COLUMNS
    ])


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
    parser.add_argument('--reference-name',
                        type=str,
                        help='Only return variants in this reference sequence.')
    parser.add_argument('--start',
                        type=long,
                        help=('The beginning of the window (0-based '
                              'inclusive) for which overlapping variants '
                              'should be returned. If unspecified, defaults '
                              'to 0.'))
    parser.add_argument('--end',
                        type=long,
                        help=('The end of the window (0-based exclusive) for '
                              'which variants should be returned. If '
                              'unspecified or 0, defaults to the length of the '
                              'reference.'))

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
    genomics_util.ValidateLimitFlag(args.limit_calls, 'limit-calls')

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    # Filter down to just the displayed fields, if we know we're using the
    # default format. This appears to only be the case when --format is unset.
    global_params = None
    if not args.format:
      global_params = messages.StandardQueryParameters(fields=_API_FIELDS)

    pager = list_pager.YieldFromList(
        apitools_client.variants,
        messages.SearchVariantsRequest(
            variantSetIds=[args.variant_set_id],
            callSetIds=args.call_set_ids,
            referenceName=args.reference_name,
            start=args.start,
            end=args.end,
            maxCalls=args.limit_calls),
        global_params=global_params,
        limit=args.limit,
        method='Search',
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='variants')
    return genomics_util.ReraiseHttpExceptionPager(pager)

  def Format(self, unused_args):
    """Returns a paginated box table layout format string."""
    # page allows us to incrementally show results as they stream in, thereby
    # giving the user incremental feedback if they've queried a large set of
    # results.
    return 'table[box,page=512]({0})'.format(','.join(_PROJECTIONS))
