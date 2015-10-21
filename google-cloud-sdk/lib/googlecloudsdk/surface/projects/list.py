# Copyright 2014 Google Inc. All Rights Reserved.
"""Command to list all Project IDs associated with the active user."""

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core import resources
from googlecloudsdk.shared.projects import util
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class List(base.Command):
  """List all active Projects.

  *{command}* lists all active Projects (ID and title), for the active
  user's credentials, in alphabetical order by Project title.
  Projects which have been deleted or are pending deletion will not be
  included.

  You can specify the maximum number of Projects to list with the 'limit' flag.
  """

  detailed_help = {
      'EXAMPLES': textwrap.dedent("""\
          The following command will list a maximum of 5 Projects, out of all
          of the active user's active Projects, sorted alphabetically by title.

            $ {command} --limit=5
      """),
  }

  @staticmethod
  def ProjectIdToLink(item):
    instance_ref = resources.Parse(item.projectId,
                                   collection='cloudresourcemanager.projects')
    return instance_ref.SelfLink()

  @staticmethod
  def Args(parser):
    parser.add_argument('--limit', default=None, type=int,
                        help='Maximum number of results.')

  @util.HandleHttpError
  def Run(self, args):
    """Run the list command."""

    projects = self.context['projects_client']
    messages = self.context['projects_messages']
    remote_completion.SetGetInstanceFun(self.ProjectIdToLink)
    for project in apitools_base.YieldFromList(
        projects.projects,
        messages.CloudresourcemanagerProjectsListRequest(),
        limit=args.limit,
        field='projects',
        predicate=util.IsActive,
        batch_size_attribute='pageSize'):
      yield project

  def Display(self, args, result):
    instance_refs = []
    items = remote_completion.Iterate(result, instance_refs,
                                      self.ProjectIdToLink)
    list_printer.PrintResourceList('cloudresourcemanager.projects', items)
    cache = remote_completion.RemoteCompletion()
    cache.StoreInCache(instance_refs)
