# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns managed-zones list command."""

from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """View the list of all your managed-zones.

  This command displays the list of your managed-zones.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of all managed-zones, run:

            $ {command}

          To see the list of first 10 managed-zones, run:

            $ {command} --limit=10
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--limit', default=None, required=False, type=int,
        help='Maximum number of managed-zones to list.')

  @staticmethod
  def GetRef(item):
    instance_ref = resources.Create('dns.managedZones',
                                    managedZone=item.name)
    return instance_ref.SelfLink()

  def Run(self, args):
    dns_client = self.context['dns_client']
    dns_messages = self.context['dns_messages']

    project_id = properties.VALUES.core.project.Get(required=True)
    remote_completion.SetGetInstanceFun(self.GetRef)

    return apitools_base.YieldFromList(
        dns_client.managedZones,
        dns_messages.DnsManagedZonesListRequest(project=project_id),
        limit=args.limit, field='managedZones')

  @util.HandleHttpError
  def Display(self, args, result):
    instance_refs = []
    items = remote_completion.Iterate(result, instance_refs, self.GetRef)
    list_printer.PrintResourceList('dns.managedZones', items)
    cache = remote_completion.RemoteCompletion()
    cache.StoreInCache(instance_refs)
