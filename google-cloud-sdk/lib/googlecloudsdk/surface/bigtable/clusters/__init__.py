# Copyright 2015 Google Inc. All Rights Reserved.

"""The main command group for bigtable."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import properties


class Clusters(base.Group):
  """Manage Cloud Bigtable clusters."""

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    pass

