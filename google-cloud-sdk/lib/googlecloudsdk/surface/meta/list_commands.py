# Copyright 2014 Google Inc. All Rights Reserved.

"""A command that lists all possible gcloud commands excluding flags."""

import sys

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import walker_util


def PrintFlattenedCommandTree(command, out=None):
  """Prints the commands in the command tree in sorted order to out.

  Args:
    command: dict, The tree (nested dict) of command/group names.
    out: stream, The output stream, sys,stdout if None.
  """

  def WalkCommandTree(commands, command, args):
    """Visit each command and group in the CLI command tree.

    Each command line is added to the commands list.

    Args:
      commands: [str], The list of command strings.
      command: dict, The tree (nested dict) of command/group names.
      args: [str], The subcommand arg prefix.
    """
    if '_name_' in command:
      args_next = args + [command['_name_']]
      commands.append(' '.join(args_next))
    else:
      args_next = args + [command['_root_']]
    if 'commands' in command:
      for c in command['commands']:
        commands.append(' '.join(args_next + [c]))
    if 'groups' in command:
      for g in command['groups']:
        WalkCommandTree(commands, g, args_next)

  commands = []
  WalkCommandTree(commands, command, [])
  if not out:
    out = sys.stdout
  out.write('\n'.join(sorted(commands)) + '\n')


class ListCommands(base.Command):
  """List all possible gcloud commands excluding flags."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--hidden',
        action='store_true',
        default=None,
        help=('Include hidden commands and groups.'))
    parser.add_argument(
        'restrict',
        metavar='COMMAND/GROUP',
        nargs='*',
        default=None,
        help='Restrict the listing to the specified command groups.')

  def Run(self, args):
    return walker_util.CommandTreeGenerator(self.cli).Walk(args.hidden,
                                                           args.restrict)

  def Display(self, args, result):
    return PrintFlattenedCommandTree(result)
