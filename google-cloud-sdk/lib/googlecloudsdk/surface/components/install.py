# Copyright 2015 Google Inc. All Rights Reserved.

"""The command to install/update gcloud components."""

import argparse
import textwrap

from googlecloudsdk.calliope import base


@base.Hidden
class Install(base.Command):
  """Install one or more Cloud SDK components.

  Ensure that each of the specified components (as well as any dependent
  components) is installed on the local workstation.  Components are installed
  without performing any upgrades to your existing SDK installation.  All
  components are installed at the current version of your SDK.
  """
  # TODO(markpell): Stop using dedent across all these commands. This happens
  # automatically.
  detailed_help = {
      'DESCRIPTION': textwrap.dedent("""\
          {description}

          Components that are available for installation can be viewed by
          running:

            $ {parent_command} list

          Installing a given component will also install all components on which
          it depends.  The command lists all components it is about to install,
          and asks for confirmation before proceeding.

          ``{command}'' installs components from the version of the Cloud SDK
          you currently have installed.  You can see your current version by
          running:

            $ {top_command} version

          If you want to update your Cloud SDK installation to the latest
          available version, use:

            $ {parent_command} update
      """),
      'EXAMPLES': textwrap.dedent("""\
          The following command installs ``COMPONENT-1'', ``COMPONENT-2'',
          and all components that they depend on:

            $ {command} COMPONENT-1 COMPONENT-2
      """),
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'component_ids',
        metavar='COMPONENT-IDS',
        nargs='+',
        help='The IDs of the components to be installed.')
    parser.add_argument(
        '--allow-no-backup',
        required=False,
        action='store_true',
        help=argparse.SUPPRESS)

  def Run(self, args):
    """Runs the list command."""
    self.group.update_manager.Install(
        args.component_ids, allow_no_backup=args.allow_no_backup)
