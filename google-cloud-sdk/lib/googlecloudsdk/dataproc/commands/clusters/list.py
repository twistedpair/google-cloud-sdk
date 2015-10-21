# Copyright 2015 Google Inc. All Rights Reserved.

"""List cluster command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties

from googlecloudsdk.dataproc.lib import util


class List(base.Command):
  """View a list of all clusters in a project."""

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To see the list of all clusters, run:

            $ {command}
          """,
  }

  @util.HandleHttpError
  def Run(self, args):
    client = self.context['dataproc_client']
    messages = self.context['dataproc_messages']

    project = properties.VALUES.core.project.Get(required=True)

    request = messages.DataprocProjectsClustersListRequest(
        projectId=project)

    response = client.projects_clusters.List(request)
    return response.clusters

  def Display(self, args, result):
    list_printer.PrintResourceList('dataproc.clusters', result)
