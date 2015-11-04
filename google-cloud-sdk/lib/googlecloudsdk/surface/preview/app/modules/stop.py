# Copyright 2013 Google Inc. All Rights Reserved.

"""The Stop command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import flags
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Stop(base.Command):
  """Stop serving a specific version of the given modules.

  This command stops serving a specific version of the given modules.  It may
  only be used if the scaling module for your module has been set to manual.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To stop serving a single module, run:

            $ {command} default --version=1

          To stop serving multiple modules, run:

            $ {command} module1 module2 --version=1
          """,
  }

  @staticmethod
  def Args(parser):
    flags.SERVER_FLAG.AddToParser(parser)
    flags.VERSION_FLAG.AddToParser(parser)
    flags.MODULES_ARG.AddToParser(parser)

  def Run(self, args):
    # TODO(markpell): This fails with "module/version does not exist" even
    # when it exists if the scaling mode is set to auto.  It would be good
    # to improve that error message.
    client = appengine_client.AppengineClient(args.server)
    for module in args.modules:
      client.StopModule(module=module, version=args.version)
      log.status.Print('Stopped: {0}/{1}/{2}'.format(
          client.project, module, args.version))
