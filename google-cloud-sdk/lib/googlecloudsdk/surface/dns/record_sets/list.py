# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets list command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.shared.dns import util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """View the list of record-sets in a managed-zone.

  This command displays the list of record-sets contained within the specified
  managed-zone.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of all record-sets in my_zone, run:

            $ {parent_command} -z my_zone list

          To see the list of first 10 record-sets in my_zone, run:

            $ {parent_command} -z my_zone list --limit=10

          To see the list of 'my.zone.com.' record-sets in my_zone, run:

            $ {parent_command} -z my_zone list --name="my.zone.com."

          To see the list of 'my.zone.com.' CNAME record-sets in my_zone, run:

            $ {parent_command} -z my_zone list --name="my.zone.com." --type="CNAME"
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--limit', default=None, required=False, type=int,
        help='Maximum number of record-sets to list.')
    parser.add_argument(
        '--name', required=False,
        help='Only list record-sets with this exact domain name.')
    parser.add_argument(
        '--type', required=False,
        help='Only list records of this type. If present, the --name parameter '
        'must also be present.')

  def Run(self, args):
    dns_client = self.context['dns_client']
    dns_messages = self.context['dns_messages']

    project_id = properties.VALUES.core.project.Get(required=True)

    if args.type and not args.name:
      raise exceptions.ToolException(
          '--name should also be provided when --type is used')

    return apitools_base.YieldFromList(
        dns_client.resourceRecordSets,
        dns_messages.DnsResourceRecordSetsListRequest(
            project=project_id,
            managedZone=args.zone,
            name=util.AppendTrailingDot(args.name),
            type=args.type),
        limit=args.limit, field='rrsets')

  @util.HandleHttpError
  def Display(self, args, result):
    list_printer.PrintResourceList('dns.resourceRecordSets', result)
