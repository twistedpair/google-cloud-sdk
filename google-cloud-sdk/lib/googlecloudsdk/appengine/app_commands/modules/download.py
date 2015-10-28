# Copyright 2013 Google Inc. All Rights Reserved.

"""The Download command."""

import os

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files

from googlecloudsdk.appengine.lib import appengine_client
from googlecloudsdk.appengine.lib import flags


class Download(base.Command):
  """(DEPRECATED) Download a specific version of the given modules of your app.

  This command is deprecated and will soon be removed.

  This command downloads the files that were in the deployment of the given
  modules.  For each module you specify, a directory named for that module will
  be created under ``output-dir'' with the files belonging to that module.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To download a single module, run:

            $ {command} default --version=1 --output-dir=~/download

          To download multiple modules, run:

            $ {command} module1 module2 --version=1 --output-dir=~/download
          """,
  }

  @staticmethod
  def Args(parser):
    flags.SERVER_FLAG.AddToParser(parser)
    flags.VERSION_FLAG.AddToParser(parser)
    flags.MODULES_ARG.AddToParser(parser)
    parser.add_argument('--output-dir',
                        help='An optional directory to download the app to.  '
                        'By default, the current directory will be used.')

  def Run(self, args):
    log.warn('The download command is deprecated, and will soon be removed.')
    if args.output_dir:
      output_dir = args.output_dir
      if not os.path.isdir(output_dir):
        raise exceptions.InvalidArgumentException(
            'output-dir', 'The directory does not exist.')
    else:
      output_dir = os.getcwd()

    client = appengine_client.AppengineClient(args.server)
    for m in args.modules:
      module_dir = os.path.join(output_dir, m)
      files.MakeDir(module_dir)
      log.status.Print('Downloading module [{module}] to [{dir}]'.format(
          module=m, dir=module_dir))
      client.DownloadModule(m, args.version, module_dir)
