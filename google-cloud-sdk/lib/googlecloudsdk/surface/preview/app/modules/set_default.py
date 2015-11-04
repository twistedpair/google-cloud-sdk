# Copyright 2013 Google Inc. All Rights Reserved.

"""The Set Default command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import flags
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class SetDefault(base.Command):
  """Set the default serving version for the given modules.

  This command sets the default serving version for the given modules.
  The default version for a module is served when you visit
  mymodule.myapp.appspot.com.'
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To set the default version for a single module, run:

            $ {command} default --version=1

          To set the default version for multiple modules, run:

            $ {command} module1 module2 --version=1
          """,
  }

  @staticmethod
  def Args(parser):
    flags.SERVER_FLAG.AddToParser(parser)
    flags.VERSION_FLAG.AddToParser(parser)
    flags.MODULES_ARG.AddToParser(parser)

  def Run(self, args):
    client = appengine_client.AppengineClient(args.server)

    message = ('You are about to set the default serving version to [{version}]'
               ' for the following modules:\n\t'.format(version=args.version))
    message += '\n\t'.join([client.project + '/' + m for m in args.modules])
    console_io.PromptContinue(message=message, cancel_on_no=True)

    client.SetDefaultVersion(args.modules, args.version)
    log.status.Print('Default serving version set to: ' + args.version)
