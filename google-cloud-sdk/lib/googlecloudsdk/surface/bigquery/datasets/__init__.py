# Copyright 2014 Google Inc. All Rights Reserved.

"""The command group for gcloud bigquery datasets.
"""

from googlecloudsdk.calliope import base


class Datasets(base.Group):
  """A group of subcommands for working with datasets.

  A dataset is a collection of related tables.
  """

  def Filter(self, context, args):
    """Modify the context that will be given to this group's commands when run.

    The context is a dictionary into which you can insert whatever you like.
    The context is given to each command under this group.  You can do common
    initialization here and insert it into the context for later use.  Of course
    you can also do common initialization as a function that can be called in a
    library.

    Args:
      context: {str:object}, A set of key-value pairs that can be used for
          common initialization among commands.
      args: argparse.Namespace: The same namespace given to the corresponding
          .Run() invocation.
    """
    pass
