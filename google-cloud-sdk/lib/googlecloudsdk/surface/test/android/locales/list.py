# Copyright 2015 Google Inc. All Rights Reserved.

"""The 'gcloud test android locales list' command."""

from googlecloudsdk.api_lib.test import util
from googlecloudsdk.calliope import base


class List(base.ListCommand):
  """List all Android locales available for testing internationalized apps."""

  # TODO(pauldavis): add command examples with --filter when it is available

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags for this command.

    Args:
      parser: An argparse parser used to add arguments that follow this
          command in the CLI. Positional arguments are allowed.
    """
    pass

  def Run(self, args):
    """Run the 'gcloud test android locales list' command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation (i.e. group and command arguments combined).

    Returns:
      The list of Android locales we want to have printed later.
    """
    catalog = util.GetAndroidCatalog(self.context)
    return catalog.runtimeConfiguration.locales

  def Collection(self, unused_args):
    """Choose the default resource collection key used to list Android locales.

    Returns:
      A collection string used as a key to select the default ResourceInfo
      from core.resources.resource_registry.RESOURCE_REGISTRY.
    """
    return 'test.android.locales'
