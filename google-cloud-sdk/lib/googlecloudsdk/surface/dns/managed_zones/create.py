# Copyright 2014 Google Inc. All Rights Reserved.
"""gcloud dns managed-zone create command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.shared.dns import util


class Create(base.Command):
  """Create a Cloud DNS managed-zone.

  This command creates a Cloud DNS managed-zone.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To create a managed-zone, run:

            $ {command} my_zone --dns_name my.zone.com. --description "My zone!"
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('dns_zone',
                        metavar='ZONE_NAME',
                        help='Name of the managed-zone to be created.')
    parser.add_argument(
        '--dns-name',
        required=True,
        help='The DNS name suffix that will be managed with the created zone.')
    parser.add_argument('--description',
                        required=True,
                        help='Short description for the managed-zone.')

  @util.HandleHttpError
  def Run(self, args):
    dns = self.context['dns_client']
    messages = self.context['dns_messages']
    resources = self.context['dns_resources']

    zone_ref = resources.Parse(args.dns_zone, collection='dns.managedZones')

    zone = messages.ManagedZone(name=zone_ref.managedZone,
                                dnsName=util.AppendTrailingDot(args.dns_name),
                                description=args.description)

    result = dns.managedZones.Create(
        messages.DnsManagedZonesCreateRequest(managedZone=zone,
                                              project=zone_ref.project))
    log.CreatedResource(zone_ref)
    return result

  def Display(self, args, result):
    list_printer.PrintResourceList('dns.managedZones', [result])
