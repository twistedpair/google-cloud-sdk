# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets command group."""
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


class RecordSets(base.Group):
  """Manage the record-sets within your managed-zones."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To import record-sets from a BIND zone file, run:

            $ {command} -z MANAGED_ZONE import --zone-file-format ZONE_FILE

          To export record-sets in yaml format, run:

            $ {command} -z MANAGED_ZONE export

          To see how to make scriptable changes to your record-sets through transactions, run:

            $ {command} -z MANAGED_ZONE transaction

          To see change details or list of all changes, run:

            $ {command} -z MANAGED_ZONE changes

          To see the list of all record-sets, run:

            $ {command} -z MANAGED_ZONE list
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--zone',
        '-z',
        completion_resource='dns.managedZones',
        help='Name of the managed-zone whose record-sets you want to manage.')

  def Filter(self, context, args):
    if not args.zone:
      raise exceptions.ToolException('parameter --zone/-z is required')
