# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to install/update gcloud components."""

from googlecloudsdk.calliope import base


class Reinstall(base.Command):
  """Reinstall the Cloud SDK with the same components you have now.

  If your Cloud SDK installation becomes corrupt, this command attempts to fix
  it by downloading the latest version of the Cloud SDK and reinstalling it.
  This will replace your existing installation with a fresh one.  The command is
  the equivalent of deleting your current installation, downloading a fresh
  copy of the SDK, and installing in the same location.
  """

  @staticmethod
  def Args(parser):
    pass

  def Run(self, args):
    """Runs the list command."""
    self.group.update_manager.Reinstall()
