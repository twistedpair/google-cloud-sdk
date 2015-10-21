# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of gcloud genomics datasets describe.
"""
from googlecloudsdk.calliope import base
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Describe(base.Command):
  """Returns details about a dataset.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=str,
                        help='The ID of the dataset to be described.')

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a Dataset message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    resources = self.context[lib.GENOMICS_RESOURCES_KEY]

    dataset_resource = resources.Parse(args.id, collection='genomics.datasets')
    return apitools_client.datasets.Get(dataset_resource.Request())

  def Display(self, args_unused, dataset):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      dataset: The Dataset message returned from the Run() method.
    """
    self.format(dataset)
