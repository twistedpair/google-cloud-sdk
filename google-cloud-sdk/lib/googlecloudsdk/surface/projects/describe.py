# Copyright 2014 Google Inc. All Rights Reserved.

"""Command to show metadata for a specified project."""

import textwrap
from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base


class Describe(base.Command):
  """Show metadata for a Project."""

  detailed_help = {
      'brief': 'Show metadata for a Project.',
      'DESCRIPTION': textwrap.dedent("""\
          This command shows metadata for a Project, given a valid Project ID.

          This call can fail for the following reasons:
              * The project specified does not exist.
              * The active user does not have permission to access the given
                project.
    """),
      'EXAMPLES': textwrap.dedent("""\
          The following command will print metadata for a Project with
          identifier 'example-foo-bar-1'

            $ {command} example-foo-bar-1
    """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('id',
                        completion_resource='cloudresourcemanager.projects',
                        list_command_path='beta.projects',
                        help='Project ID')

  @util.HandleHttpError
  def Run(self, args):
    projects = self.context['projects_client']
    resources = self.context['projects_resources']
    project_ref = resources.Parse(args.id,
                                  collection='cloudresourcemanager.projects')
    return projects.projects.Get(project_ref.Request())

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    # pylint:disable=not-callable, self.format is callable.
    self.format(result)
