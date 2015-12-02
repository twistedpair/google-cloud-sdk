# Copyright 2014 Google Inc. All Rights Reserved.

"""A command that lists all possible gcloud commands, optionally with flags."""

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
      if commands:
        commands.append(' '.join(args_next))
      else:
        # List the global flags with the root command.
        commands.append(' '.join(args_next + command.get('_flags_', [])))
    else:
      args_next = args + [command['_root_']]
    if 'commands' in command:
      for c in command['commands']:
        name = c.get('_name_', c)
        flags = c.get('_flags_', [])
        commands.append(' '.join(args_next + [name] + flags))
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
        '--flags',
        action='store_true',
        help='Include the non-global flags for each command/group.')
    flag_values = parser.add_argument(
        '--flag-values',
        action='store_true',
        help=('Include the non-global flags and flag values/types for each '
              'command/group.'))
    flag_values.detailed_help = (
        'Include the non-global flags and flag values/types for each '
        'command/group. Flags with fixed choice values will be listed as '
        '--flag=choice1,..., and flags with typed values will be listed '
        'as --flag=<type>.')
    parser.add_argument(
        '--hidden',
        action='store_true',
        help='Include hidden commands and groups.')
    parser.add_argument(
        'restrict',
        metavar='COMMAND/GROUP',
        nargs='*',
        help='Restrict the listing to the specified command groups.')

  def Run(self, args):
    return walker_util.CommandTreeGenerator(
        self.cli, with_flags=args.flags,
        with_flag_values=args.flag_values).Walk(args.hidden, args.restrict)

  def Display(self, args, result):
    return PrintFlattenedCommandTree(result)
