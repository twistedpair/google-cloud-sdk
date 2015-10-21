# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction abort command."""

import os

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log


class Abort(base.Command):
  """Abort transaction.

  This command aborts the transaction and deletes the transaction file.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To abort the transaction, run:

            $ {command} -z MANAGED_ZONE
          """,
  }

  def Run(self, args):
    if not os.path.isfile(args.transaction_file):
      raise exceptions.ToolException(
          'transaction not found at [{0}]'.format(args.transaction_file))

    os.remove(args.transaction_file)

    log.status.Print('Aborted transaction [{0}].'.format(args.transaction_file))
