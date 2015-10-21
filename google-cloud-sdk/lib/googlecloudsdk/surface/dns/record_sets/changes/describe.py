# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns record-sets changes describe command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import resolvers
from googlecloudsdk.shared.dns import util


class Describe(base.Command):
  """View the details of a change.

  This command displays the details of the specified change.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display the details of a change, run:

            $ {command} change_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'change_id', metavar='CHANGE_ID',
        help='The ID of the change you want details for.')

  @util.HandleHttpError
  def Run(self, args):
    dns = self.context['dns_client']
    resources = self.context['dns_resources']
    change_ref = resources.Parse(
        args.change_id,
        params={'managedZone': resolvers.FromArgument('--zone', args.zone)},
        collection='dns.changes')

    return dns.changes.Get(change_ref.Request())

  def Display(self, args, result):
    self.format(result)
