# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction execute command."""

import os

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.shared.dns import import_util
from googlecloudsdk.shared.dns import transaction_util
from googlecloudsdk.shared.dns import util


class Execute(base.Command):
  """Execute the transaction on Cloud DNS.

  This command executes the transaction on Cloud DNS. This will result in
  record-sets being changed as specified in the transaction.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To execute the transaction, run:

            $ {command} -z MANAGED_ZONE
          """,
  }

  @util.HandleHttpError
  def Run(self, args):
    with transaction_util.TransactionFile(args.transaction_file) as trans_file:
      change = transaction_util.ChangeFromYamlFile(trans_file)

    if import_util.IsOnlySOAIncrement(change):
      log.status.Print(
          'Nothing to do, empty transaction [{0}]'.format(
              args.transaction_file))
      os.remove(args.transaction_file)
      return None

    dns = self.context['dns_client']
    messages = self.context['dns_messages']
    resources = self.context['dns_resources']
    project_id = properties.VALUES.core.project.Get(required=True)
    zone_ref = resources.Parse(args.zone, collection='dns.managedZones')

    # Send the change to the service.
    result = dns.changes.Create(messages.DnsChangesCreateRequest(
        change=change, managedZone=zone_ref.Name(), project=project_id))
    change_ref = resources.Create(
        collection='dns.changes', project=project_id,
        managedZone=zone_ref.Name(), changeId=result.id)
    msg = 'Executed transaction [{0}] for managed-zone [{1}].'.format(
        args.transaction_file, zone_ref.Name())
    log.status.Print(msg)
    log.CreatedResource(change_ref)
    os.remove(args.transaction_file)
    return result

  def Display(self, args, result):
    if result:
      list_printer.PrintResourceList('dns.changes', [result])
