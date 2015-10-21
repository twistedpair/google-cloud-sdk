# Copyright 2013 Google Inc. All Rights Reserved.

"""A calliope command that prints help for another calliope command."""

from googlecloudsdk.calliope import base


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Help(base.Command):
  """Prints detailed help messages for the specified commands.

  This command prints a detailed help message for the commands specified
  after the ``help'' operand.
  """

  @staticmethod
  def Args(parser):
    command_arg = parser.add_argument(
        'command',
        nargs='*',
        help='The commands to get help for.')
    command_arg.detailed_help = """\
        A sequence of group and command names with no flags.
        """

  def Run(self, args):
    # --document=style=help to signal the metrics.Help() 'help' label in
    # actions.RenderDocumentAction().Action().
    self.cli.Execute(args.command + ['--document=style=help'])
    return None
