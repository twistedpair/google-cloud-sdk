# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction add command."""

from googlecloudsdk.api_lib.dns import transaction_util as trans_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Add(base.Command):
  """Append a record-set addition to the transaction.

  This command appends a record-set addition to the transaction.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To add an A record, run:

            $ {command} -z MANAGED_ZONE --name my.domain. --ttl 1234 --type A "1.2.3.4"

          To add a TXT record with multiple data values, run:

            $ {command} -z MANAGED_ZONE --name my.domain. --ttl 2345 --type TXT "Hello world" "Bye world"
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--name', required=True,
        help='DNS name of the record-set to be added.')
    parser.add_argument(
        '--ttl', required=True, type=int,
        help='TTL for the record-set to be added.')
    parser.add_argument(
        '--type', required=True,
        help='Type of the record-set to be added.')
    parser.add_argument(
        'data', nargs='+',
        help='DNS name of the record-set to be added.')

  def Run(self, args):
    with trans_util.TransactionFile(args.transaction_file) as trans_file:
      change = trans_util.ChangeFromYamlFile(trans_file)

    change.additions.append(trans_util.CreateRecordSetFromArgs(args))

    with trans_util.TransactionFile(args.transaction_file, 'w') as trans_file:
      trans_util.WriteToYamlFile(trans_file, change)

    log.status.Print(
        'Record addition appended to transaction at [{0}].'.format(
            args.transaction_file))
