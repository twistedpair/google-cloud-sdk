# Copyright 2013 Google Inc. All Rights Reserved.

"""The gcloud appengine group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import list_printer

from googlecloudsdk.appengine.lib import appengine_client
from googlecloudsdk.appengine.lib import flags


class List(base.Command):
  """List your existing deployed modules and versions.

  This command lists all the modules and their versions that are currently
  deployed to the App Engine server.  The default serving version for each
  module is indicated with a '*'.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list all modules and versions, run:

            $ {command}

          To list all versions for a specific set of modules, run:

            $ {command} module1 module2
          """,
  }

  @staticmethod
  def Args(parser):
    flags.SERVER_FLAG.AddToParser(parser)
    flags.MODULES_OPTIONAL_ARG.AddToParser(parser)

  def Run(self, args):
    client = appengine_client.AppengineClient(args.server)
    modules = client.ListModules()

    module_versions = []
    for module, versions in sorted(modules.iteritems()):
      if not versions or not isinstance(versions, list):
        # No versions for some reason.
        continue
      if args.modules and module not in args.modules:
        # Not for a module we are interested in.
        continue

      # First version is always the default version (from the API).
      default_version = versions[0]
      for version in sorted(versions):
        module_versions.append(
            {'module': module, 'version': version,
             'is_default': version == default_version})

    return module_versions

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('app.module_versions', result)

