# Copyright 2014 Google Inc. All Rights Reserved.

"""operations wait command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.shared.deployment_manager import dm_v2_util
from googlecloudsdk.shared.deployment_manager.exceptions import DeploymentManagerError

# Number of seconds (approximately) to wait for each operation to complete.
OPERATION_TIMEOUT = 20 * 60  # 20 mins


class Wait(base.Command):
  """Wait for all operations specified to complete before returning.

  Polls until all operations have finished, then prints the resulting operations
  along with any operation errors.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To poll until an operation has completed, run:

            $ {command} operation-name

          To poll until several operations have all completed, run:

            $ {command} operation-one operation-two operation-three
          """,
  }

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('operation_name', nargs='+', help='Operation name.')

  def Run(self, args):
    """Run 'operations wait'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    Raises:
      DeploymentManagerError: Operation finished with error(s) or timed out.
    """
    project = properties.VALUES.core.project.Get(required=True)
    failed_ops = []
    for operation_name in args.operation_name:
      try:
        dm_v2_util.WaitForOperation(
            operation_name, project, self.context, '', OPERATION_TIMEOUT)
      except DeploymentManagerError:
        failed_ops.append(operation_name)
    if failed_ops:
      if len(failed_ops) == 1:
        raise DeploymentManagerError(
            'Operation %s failed to complete or has errors.' % failed_ops[0])
      else:
        raise DeploymentManagerError(
            'Some operations failed to complete without errors:\n'
            + '\n'.join(failed_ops))
    else:
      log.status.Print('All operations completed successfully.')
