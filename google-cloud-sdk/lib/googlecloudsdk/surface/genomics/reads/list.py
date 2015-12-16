# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics reads list.
"""

from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import base
from googlecloudsdk.third_party.apitools.base.py import list_pager

_COLUMNS = [
    ('REFERENCE_NAME', 'alignment.position.referenceName'),
    ('POSITION', 'alignment.position.position'),
    ('REVERSE_STRAND', 'alignment.position.reverseStrand'),
    ('FRAGMENT_NAME', 'fragmentName'),
    ('SEQUENCE', 'alignedSequence'),
]
_PROJECTIONS = [
    '{0}:label={1}'.format(field, col) for col, field in _COLUMNS
]
_API_FIELDS = ','.join(['nextPageToken'] + [
    'alignments.' + f for _, f in _COLUMNS
    ])


class List(base.Command):
  """Lists reads within a given read group set.

  Prints a table with summary information on reads in the read group set.
  Results may be restricted to reads which are aligned to a given reference
  (--reference-name) or may be further filtered to reads that have alignments
  overlapping a given range (--reference-name, --start, --end).
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('read_group_set_id',
                        type=str,
                        help=('Restrict the list to reads in this read '
                              'group set.'))
    parser.add_argument('--reference-name',
                        type=str,
                        help=('Only return reads which are aligned to this '
                              'reference. Pass * to list unmapped reads '
                              'only.'))
    parser.add_argument('--start',
                        type=long,
                        help=('The beginning of the window (0-based '
                              'inclusive) for which overlapping reads '
                              'should be returned. If unspecified, defaults '
                              'to 0.'))
    parser.add_argument('--end',
                        type=long,
                        help=('The end of the window (0-based exclusive) for '
                              'which overlapping reads should be returned. If '
                              'unspecified or 0, defaults to the length of '
                              'the reference.'))
    parser.add_argument('--limit',
                        type=int,
                        help='The maximum number of reads to return.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      A list of reads that meet the search criteria.
    """
    genomics_util.ValidateLimitFlag(args.limit)

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    # Filter down to just the displayed fields, if we know we're using the
    # default format. This appears to only be the case when --format is unset.
    global_params = None
    if not args.format:
      global_params = messages.StandardQueryParameters(fields=_API_FIELDS)

    pager = list_pager.YieldFromList(
        apitools_client.reads,
        messages.SearchReadsRequest(
            readGroupSetIds=[args.read_group_set_id],
            referenceName=args.reference_name,
            start=args.start,
            end=args.end),
        global_params=global_params,
        limit=args.limit,
        method='Search',
        batch_size_attribute='pageSize',
        batch_size=args.limit,  # Use limit if any, else server default.
        field='alignments')
    return genomics_util.ReraiseHttpExceptionPager(pager)

  def Format(self, unused_args):
    """Returns a paginated box table layout format string."""
    # page allows us to incrementally show results as they stream in, thereby
    # giving the user incremental feedback if they've queried a large set of
    # results.
    return 'table[box,page=512]({0})'.format(','.join(_PROJECTIONS))
