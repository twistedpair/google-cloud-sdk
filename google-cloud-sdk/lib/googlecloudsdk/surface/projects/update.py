# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to update a new project."""

import textwrap
from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Update(base.Command):
  """Update new Project."""

  detailed_help = {
      'brief': 'Update a Project.',
      'DESCRIPTION': textwrap.dedent("""\
          This command updates the given Project with new values.

          This call can fail for the following reasons:
              * There is no project with the given ID.
    """),
      'EXAMPLES': textwrap.dedent("""\
          The following command will update a Project with identifier
          'example-foo-bar-1' to have name "Foo Bar and Grill"

            $ {command} example-foo-bar-1 --name="Foo Bar and Grill"
    """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', metavar='PROJECT_ID',
                        help='The ID for the project you want to update.')
    parser.add_argument('--name', required=True,
                        help='The new name for the project.')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']
    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    result = projects.projects.Update(
        messages.Project(
            projectId=project_ref.Name(),
            name=args.name))
    log.UpdatedResource(project_ref)
    return result

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('cloudresourcemanager.projects', [result])
