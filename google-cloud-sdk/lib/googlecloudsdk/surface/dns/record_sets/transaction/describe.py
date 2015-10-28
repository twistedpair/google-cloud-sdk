# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction describe command."""

from googlecloudsdk.api_lib.dns import transaction_util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Describe the transaction.

  This command displays the contents of the transaction.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To look at the contents of the transaction, run:

            $ {command} -z MANAGED_ZONE
          """,
  }

  def Run(self, args):
    with transaction_util.TransactionFile(args.transaction_file) as trans_file:
      return transaction_util.ChangeFromYamlFile(trans_file)

  def Display(self, args, result):
    self.format(result)
