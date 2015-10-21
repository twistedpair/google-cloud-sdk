# Copyright 2014 Google Inc. All Rights Reserved.

"""The gcloud dns command group."""

import argparse
import urlparse

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.third_party.apis.dns.v1 import dns_v1_client
from googlecloudsdk.third_party.apis.dns.v1 import dns_v1_messages


@base.ReleaseTracks(base.ReleaseTrack.GA)
class DNS(base.Group):
  """Manage your Cloud DNS managed-zones and record-sets.

  This set of commands allows you to create and maintain managed-zones and their
  record-sets.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see how to create and maintain managed-zones, run:

            $ {command} managed-zones

          To see how to maintain the record-sets within a managed-zone, run:

            $ {command} record-sets

          To display Cloud DNS related information for your project, run:

            $ {command} project-info describe
          """,
  }

  @staticmethod
  def Args(parser):
    # The --endpoint flag is deprecated and will be removed.
    # New use cases should use the property api_endpoint_overrides/dns directly.
    parser.add_argument(
        '--endpoint', help=argparse.SUPPRESS,
        action=actions.StoreProperty(
            properties.VALUES.api_endpoint_overrides.dns))

  def Filter(self, context, args):
    project = properties.VALUES.core.project
    resolver = resolvers.FromProperty(project)
    resources.SetParamDefault('dns', None, 'project', resolver)

    dns_client = dns_v1_client.DnsV1(
        url=properties.VALUES.api_endpoint_overrides.dns.Get(),
        get_credentials=False,
        http=self.Http())

    context['dns_client'] = dns_client
    context['dns_messages'] = dns_v1_messages
    context['dns_resources'] = resources

    if args.endpoint:
      log.warn('The --endpoint flag is deprecated and will be removed.  '
               'Set the api_endpoint_overrides/dns property instead.  '
               'e.g. gcloud config set api_endpoint_overrides/dns '
               'https://www.googleapis.com/dns/v1beta1')

    return context
