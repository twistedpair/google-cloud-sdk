# Copyright 2015 Google Inc. All Rights Reserved.

"""List project repositories.
"""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.shared.source import source


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class List(base.Command):
  """Lists all repositories in a particular project.

  By default, repos in the current project are listed; this can be overridden
  with the gcloud --project flag.
  """

  @staticmethod
  def Args(parser):
    pass

  def Run(self, args):
    """Run the list command."""
    project = source.Project(properties.VALUES.core.project.Get(required=True))
    return project.ListRepos()

  def Display(self, args, repos):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      repos: The iterator over Repo messages returned from the Run() method.
    """
    list_printer.PrintResourceList('source.jobs.list', repos)
