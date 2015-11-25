# Copyright 2013 Google Inc. All Rights Reserved.

"""The command to install/update gcloud components."""

import argparse

from googlecloudsdk.calliope import base
from googlecloudsdk.core.console import console_io


class Update(base.Command):
  """Update all of your installed components to the latest version.

  Ensure that the latest version of all installed components is installed on the
  local workstation.
  """
  detailed_help = {
      'DESCRIPTION': """\
          {description}

          The command lists all components it is about to update, and asks for
          confirmation before proceeding.

          By default, this command will update all components to their latest
          version.  This can be configured by using the --version flag to choose
          a specific version to update to.  This version may also be a version
          older than the one that is currently installed.

          You can see your current Cloud SDK version by running:

            $ {top_command} version
      """,
      'EXAMPLES': """\
          To update all installed components to the latest version:

            $ {command}

          To update all installed components to version 1.2.3:

            $ {command} --version 1.2.3
      """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--version',
        help='An optional Cloud SDK version to update your components to.  By '
        'default, components are updated to the latest available version.')
    parser.add_argument(
        'component_ids',
        metavar='COMPONENT-IDS',
        nargs='*',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--allow-no-backup',
        required=False,
        action='store_true',
        help=argparse.SUPPRESS)

  def Run(self, args):
    """Runs the list command."""

    if args.component_ids and not args.version:
      install = console_io.PromptContinue(
          message='You have specified individual components to update.  If you '
          'are trying to install new components, use:\n  $ gcloud '
          'components install {components}'.format(
              components=' '.join(args.component_ids)),
          prompt_string='Do you want to run install instead',
          default=False,
          throw_if_unattended=False,
          cancel_on_no=False)
      if install:
        self.group.update_manager.Install(
            args.component_ids, allow_no_backup=args.allow_no_backup)
        return

    self.group.update_manager.Update(
        args.component_ids, allow_no_backup=args.allow_no_backup,
        version=args.version)
