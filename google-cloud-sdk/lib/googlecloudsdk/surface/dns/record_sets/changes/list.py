# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets changes list command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.shared.dns import util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """View the list of changes that have been made to your record-sets.

  This command displays the list of changes that have been made to your
  record-sets.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of changes, run:

            $ {command}

          To see the list of first 10 changes, run:

            $ {command} --limit=10
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--limit', default=None, required=False, type=int,
        help='Maximum number of changes to list.')
    parser.add_argument(
        '--sort-order', default=None, required=False,
        choices=['ascending', 'descending'],
        help='Sort order for listing (ascending|descending).')

  def Run(self, args):
    dns_client = self.context['dns_client']
    dns_messages = self.context['dns_messages']

    project_id = properties.VALUES.core.project.Get(required=True)

    return apitools_base.YieldFromList(
        dns_client.changes,
        dns_messages.DnsChangesListRequest(
            project=project_id,
            managedZone=args.zone,
            sortOrder=args.sort_order),
        limit=args.limit, field='changes')

  @util.HandleHttpError
  def Display(self, args, result):
    list_printer.PrintResourceList('dns.changes', result)
