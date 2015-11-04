# Copyright 2014 Google Inc. All Rights Reserved.

"""The 'gcloud test android devices list' command."""

from googlecloudsdk.api_lib.test import util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer


class List(base.Command):
  """List all Android device environments available for testing."""

  @staticmethod
  def Args(parser):
    """Method called by Calliope to register flags for this command.

    Args:
      parser: An argparse parser used to add arguments that follow this
          command in the CLI. Positional arguments are allowed.
    """
    pass

  def Run(self, args):
    """Run the 'gcloud test android devices list' command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation (i.e. group and command arguments combined).

    Returns:
      The list of device models we want to have printed later.
    """
    catalog = util.GetAndroidCatalog(self.context)
    return catalog.models

  def Display(self, args, result):
    """Method called by Calliope to print the result of the Run() method.

    Args:
      args: The arguments that the command was run with.
      result: The Run() method's result, which is a list of AndroidModels.
    """
    list_printer.PrintResourceList('test.android.devices', result)
