# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction start command."""

import os
from googlecloudsdk.api_lib.dns import import_util
from googlecloudsdk.api_lib.dns import transaction_util
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files
from googlecloudsdk.third_party.apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.third_party.apitools.base.py import list_pager


class Start(base.Command):
  """Start a transaction.

  This command starts a transaction.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To start a transaction, run:

            $ {command} -z MANAGED_ZONE
          """,
  }

  @util.HandleHttpError
  def Run(self, args):
    if os.path.isfile(args.transaction_file):
      raise exceptions.ToolException(
          'transaction already exists at [{0}]'.format(args.transaction_file))

    dns = self.context['dns_client']
    messages = self.context['dns_messages']
    resources = self.context['dns_resources']
    project_id = properties.VALUES.core.project.Get(required=True)

    # Get the managed-zone.
    zone_ref = resources.Parse(args.zone, collection='dns.managedZones')
    try:
      zone = dns.managedZones.Get(zone_ref.Request())
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(util.GetErrorMessage(error))

    # Initialize an empty change
    change = messages.Change()

    # Get the SOA record, there will be one and only one.
    # Add addition and deletion for SOA incrementing to change.
    records = [record for record in list_pager.YieldFromList(
        dns.resourceRecordSets,
        messages.DnsResourceRecordSetsListRequest(
            project=project_id,
            managedZone=zone_ref.Name(),
            name=zone.dnsName,
            type='SOA'),
        field='rrsets')]
    change.deletions.append(records[0])
    change.additions.append(import_util.NextSOARecordSet(records[0]))

    # Write change to transaction file
    try:
      with files.Context(open(args.transaction_file, 'w')) as transaction_file:
        transaction_util.WriteToYamlFile(transaction_file, change)
    except Exception as exp:
      msg = 'unable to write transaction [{0}] because [{1}]'
      msg = msg.format(args.transaction_file, exp)
      raise exceptions.ToolException(msg)

    log.status.Print('Transaction started [{0}].'.format(
        args.transaction_file))
