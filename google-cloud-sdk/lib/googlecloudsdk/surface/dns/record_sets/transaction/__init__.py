# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets transaction command group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.shared.dns import transaction_util


class Transaction(base.Group):
  """Make scriptable and transactional changes to your record-sets."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To start a transaction, run:

            $ {command} start

          To append a record-set addition to the transaction, run:

            $ {command} add --name RECORD_SET_NAME --ttl TTL --type TYPE DATA

          To append a record-set removal to the transaction, run:

            $ {command} remove --name RECORD_SET_NAME --ttl TTL --type TYPE DATA

          To look at the details of the transaction, run:

            $ {command} describe

          To delete the transaction, run:

            $ {command} abort

          To execute the transaction, run:

            $ {command} execute
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--transaction-file',
        default=transaction_util.DEFAULT_PATH,
        help='Path of the file which contains the transaction.')
