# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to delete a project."""

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.shared.projects import util


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Delete(base.Command):
  """Delete a Project."""

  detailed_help = {
      'brief': 'Delete a Project.',
      'DESCRIPTION': textwrap.dedent("""\
          This command deletes the Project with the given Project ID.

          This call can fail for the following reasons:
              * There is no project with the given ID.
    """),
      'EXAMPLES': textwrap.dedent("""\
          The following command will delete the Project with identifier
          'example-foo-bar-1'

            $ {command} example-foo-bar-1
    """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', metavar='PROJECT_ID',
                        completion_resource='cloudresourcemanager.projects',
                        list_command_path='beta.projects',
                        help='The ID for the project you want to delete.')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']
    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    if not console_io.PromptContinue('Your project will be deleted.'):
      return None
    result = projects.projects.Delete(
        messages.CloudresourcemanagerProjectsDeleteRequest(
            projectId=project_ref.Name()))
    log.DeletedResource(project_ref)
    return result
