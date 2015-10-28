# Copyright 2015 Google Inc. All Rights Reserved.

"""The Stop command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.appengine.lib import appengine_client
from googlecloudsdk.appengine.lib import util
from googlecloudsdk.appengine.lib import version_util


class VersionsStopError(exceptions.Error):
  """Errors occurring when stopping versions."""
  pass


class Stop(base.Command):
  """Stop serving specified versions.

  This command stops serving the specified versions. It may only be used if the
  scaling module for your service has been set to manual.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To stop a specific version across all services, run:

            $ {command} v1

          To stop multiple named versions across all services, run:

            $ {command} v1 v2

          To stop a single version on a single service, run:

            $ {command} servicename/v1

          or

            $ {command} --service servicename v1

          To stop multiple versions in a single service, run:

            $ {command} --service servicename v1 v2

          Note that that last example may be more simply written using the
          `services stop` command (see its documentation for details).
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('versions', nargs='+', help=(
        'The versions to stop (optionally filtered by the --service flag). '
        'Can also be a resource path (<service name>/<version name> or '
        '<project name>/<service name>/<version name>).'))
    parser.add_argument('--service', '-s',
                        help=('If specified, only stop versions from the '
                              'given service.'))

  def Run(self, args):
    # TODO(user): This fails with "module/version does not exist" even
    # when it exists if the scaling mode is set to auto.  It would be good
    # to improve that error message.

    client = appengine_client.AppengineClient()
    versions = version_util.GetMatchingVersions(client.ListVersions(),
                                                args.versions, args.service,
                                                client.project)

    if versions:
      printer = console_io.ListPrinter('Stopping the following versions:')
      printer.Print(versions, output_stream=log.status)
      console_io.PromptContinue(cancel_on_no=True)
    else:
      log.warn('No matching versions found.')

    errors = []
    for version in sorted(versions):
      try:
        with console_io.ProgressTracker('Stopping [{0}]'.format(version)):
          client.StopModule(module=version.service, version=version.version)
      except util.RPCError as err:
        errors.append(str(err))
    if errors:
      raise VersionsStopError('\n\n'.join(errors))
