# Copyright 2015 Google Inc. All Rights Reserved.

"""The 'gcloud test android versions list' command."""

from googlecloudsdk.api_lib.test import util
from googlecloudsdk.calliope import base


class List(base.ListCommand):
  """List all Android OS versions available for testing."""

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags for this command.

    Args:
      parser: An argparse parser used to add arguments that follow this
          command in the CLI. Positional arguments are allowed.
    """
    pass

  def Run(self, args):
    """Run the 'gcloud test android versions list' command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation (i.e. group and command arguments combined).

    Returns:
      The list of Android OS versions we want to have printed later.
    """
    catalog = util.GetAndroidCatalog(self.context)
    return catalog.versions

  def Collection(self, unused_args):
    """Choose the default resource collection key used to list OS versions.

    Returns:
      A collection string used as a key to select the default ResourceInfo
      from core.resources.resource_registry.RESOURCE_REGISTRY.
    """
    return 'test.android.versions'
