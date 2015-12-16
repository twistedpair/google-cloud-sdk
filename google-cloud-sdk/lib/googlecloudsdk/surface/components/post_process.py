# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to perform any necessary post installation steps."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core.updater import local_state


@base.Hidden
class PostProcess(base.Command):
  """Performs any necessary post installation steps."""

  @staticmethod
  def Args(parser):
    parser.add_argument('data', nargs='*', default='')

  def Run(self, args):
    state = local_state.InstallationState.ForCurrent()
    state.CompilePythonFiles()
