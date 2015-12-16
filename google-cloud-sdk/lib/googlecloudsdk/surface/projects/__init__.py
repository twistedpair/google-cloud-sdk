# Copyright 2014 Google Inc. All Rights Reserved.

"""The command group for the Projects CLI."""

from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Projects(base.Group):
  """Manage your Projects.

  Commands to get information about your Google Developer Projects.
  """

  def Filter(self, context, _):
    context['projects_resources'] = resources
    context['projects_client'] = util.GetClient(self.Http())
    context['projects_messages'] = util.GetMessages()
