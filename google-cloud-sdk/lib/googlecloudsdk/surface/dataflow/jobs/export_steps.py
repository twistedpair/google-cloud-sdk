# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud dataflow jobs export-steps command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.shared.dataflow import job_utils
from googlecloudsdk.shared.dataflow import step_graph
from googlecloudsdk.shared.dataflow import step_json


class ExportSteps(base.Command):
  """Exports information about the steps for the given job.

  The only currently supported format is to a GraphViz dot file.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command.

    Args:
      parser: argparse.ArgumentParser to register arguments with.
    """
    job_utils.ArgsForJobRef(parser)

  def Run(self, args):
    """Runs the command.

    Args:
      args: All the arguments that were provided to this command invocation.

    Returns:
      An iterator over the steps in the given job.
    """
    return step_json.ExtractSteps(job_utils.GetJobForArgs(self.context, args))

  def Display(self, args, steps):
    """This method is called to print the result of the Run() method.

    Args:
      args: all the arguments that were provided to this command invocation.
      steps: The step information returned from Run().
    """
    if steps:
      for line in step_graph.YieldGraphviz(steps, 'StepGraph'):
        # TODO(bchambers): Write this to a file rather than stdout.
        log.out.write(line)
        log.out.write('\n')
