# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to create a new project."""

import textwrap
from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class Create(base.Command):
  """Create a new Project."""

  detailed_help = {
      'brief': 'Create a new Project.',
      'DESCRIPTION': textwrap.dedent("""\
          This command creates a new Project with the given Project ID.

          This call can fail for the following reasons:
              * The project ID is not available.
    """),
      'EXAMPLES': textwrap.dedent("""\
          The following command will create a Project with identifier
          'example-foo-bar-1'

            $ {command} example-foo-bar-1
    """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id', metavar='PROJECT_ID',
                        help='The ID for the project you want to create.')
    parser.add_argument('--name',
                        help='The name for the project you want to create.')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    resources = self.context['projects_resources']
    # TODO(svalentin): handle invalid names/ project ids nicely
    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    result = projects.projects.Create(
        messages.Project(
            projectId=project_ref.Name(),
            name=args.name))
    log.CreatedResource(project_ref)
    return result

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('cloudresourcemanager.projects', [result])
