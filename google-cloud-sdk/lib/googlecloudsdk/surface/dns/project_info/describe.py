# Copyright 2014 Google Inc. All Rights Reserved.

"""gcloud dns project-info describe command."""

from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """View Cloud DNS related information for a project.

  This command displays Cloud DNS related information for your project including
  quotas for various resources and operations.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To display Cloud DNS related information for your project, run:

            $ {command} my_project_id
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'dns_project', metavar='PROJECT_ID',
        help='The identifier for the project you want DNS related info for.')

  @util.HandleHttpError
  def Run(self, args):
    dns = self.context['dns_client']
    resources = self.context['dns_resources']
    project_ref = resources.Parse(args.dns_project, collection='dns.projects')

    return dns.projects.Get(project_ref.Request())

  def Display(self, args, result):
    self.format(result)
