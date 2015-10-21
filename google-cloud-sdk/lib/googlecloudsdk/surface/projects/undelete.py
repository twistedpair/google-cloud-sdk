# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to undelete a project."""

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.projects import util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Undelete(base.Command):
  """Undelete a Project."""

  detailed_help = {
      'brief': 'Undelete a Project.',
      'DESCRIPTION': textwrap.dedent("""\
          This command undeletes the Project with the given Project ID.

          This call can fail for the following reasons:
              * There is no project with the given ID.
    """),
      'EXAMPLES': textwrap.dedent("""\
          The following command will undelete the Project with identifier
          'example-foo-bar-1'

            $ {command} example-foo-bar-1
    """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', metavar='PROJECT_ID',
                        help='The ID for the project you want to undelete.')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']
    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    result = projects.projects.Undelete(
        messages.CloudresourcemanagerProjectsUndeleteRequest(
            projectId=project_ref.Name()))
    log.status.write('Undeleted [{r}].\n'.format(r=project_ref))
    return result
