# Copyright 2015 Google Inc. All Rights Reserved.

"""Clone GCP git repository.
"""

import textwrap
from googlecloudsdk.api_lib.source import git
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store as c_store


class Clone(base.Command):
  """Clone project git repository in the current directory."""

  detailed_help = {
      'DESCRIPTION': """\
          This command clones git repository for the currently active
          Google Cloud Platform project into the specified folder in the
          current directory.
      """,
      'EXAMPLES': textwrap.dedent("""\
          To use the default Google Cloud repository for development, use the
          following commands. We recommend that you use your project name as
          TARGET_DIR to make it apparent which directory is used for which
          project. We also recommend to clone the repository named 'default'
          since it is automatically created for each project, and its
          contents can be browsed and edited in the Developers Console.

            $ gcloud init
            $ gcloud source repos clone default TARGET_DIR
            $ cd TARGET_DIR
            ... create/edit files and create one or more commits ...
            $ git push origin master
      """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'src',
        metavar='REPOSITORY_NAME',
        help=('Name of the repository. '
              'Note: GCP projects generally have (if created) repository '
              'named "default"'))
    parser.add_argument(
        'dst',
        metavar='DIRECTORY_NAME',
        nargs='?',
        help=('Directory name for the cloned repo. Defaults to the repository '
              'name.'))

  @c_exc.RaiseToolExceptionInsteadOf(git.Error, c_store.Error)
  def Run(self, args):
    """Clone a GCP repository to the current directory.

    Args:
      args: argparse.Namespace, the arguments this command is run with.

    Raises:
      ToolException: on project initialization errors.

    Returns:
      The path to the new git repository.
    """
    # Ensure that we're logged in.
    c_store.Load()

    project_id = properties.VALUES.core.project.Get(required=True)
    project_repo = git.Git(project_id, args.src)
    path = project_repo.Clone(destination_path=args.dst or args.src)
    if path:
      log.status.write('Project [{prj}] repository [{repo}] was cloned to '
                       '[{path}].\n'.format(prj=project_id, path=path,
                                            repo=project_repo.GetName()))

