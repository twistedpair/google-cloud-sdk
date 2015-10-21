# Copyright 2015 Google Inc. All Rights Reserved.

"""List operation command."""
import json

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties

from googlecloudsdk.dataproc.lib import util


STATE_MATCHER_MAP = {'active': 'ACTIVE', 'inactive': 'NON_ACTIVE'}
STATE_MATCHER_FILTER = 'operation_state_matcher'
CLUSTER_NAME_FILTER = 'cluster_name'
PROJECT_FILTER = 'project_id'


class List(base.Command):
  """View the list of all operations."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of all operations, run:

            $ {command}

          To see the list of all active operations in a cluster, run:

            $ {command} --state-filter active --cluster my_cluster
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--cluster',
        help='Restrict to the operations of this Dataproc cluster.')

    parser.add_argument(
        '--state-filter',
        choices=sorted(STATE_MATCHER_MAP.keys()),
        help='Filter by cluster state. Choices are {0}.'.format(
            sorted(STATE_MATCHER_MAP.keys())))

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    project = properties.VALUES.core.project.Get(required=True)
    filter_dict = dict()
    filter_dict[PROJECT_FILTER] = project
    if args.state_filter:
      filter_dict[STATE_MATCHER_FILTER] = STATE_MATCHER_MAP[args.state_filter]
    if args.cluster:
      filter_dict[CLUSTER_NAME_FILTER] = args.cluster

    request = messages.DataprocOperationsListRequest(
        name='operations', filter=json.dumps(filter_dict))

    response = client.operations.List(request)
    return response.operations

  def Display(self, args, result):
    list_printer.PrintResourceList('dataproc.operations', result)
