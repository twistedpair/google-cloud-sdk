# Copyright 2015 Google Inc. All Rights Reserved.

"""The Start command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io


class VersionsStartError(exceptions.Error):
  """Errors occurring when starting versions."""
  pass


class Start(base.Command):
  """Start serving specified versions.

  This command starts serving the specified versions. It may only be used if the
  scaling module for your service has been set to manual.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To start a specific version across all services, run:

            $ {command} v1

          To start multiple named versions across all services, run:

            $ {command} v1 v2

          To start a single version on a single service, run:

            $ {command} servicename/v1

          or

            $ {command} --service servicename v1

          To start multiple versions in a single service, run:

            $ {command} --service servicename v1 v2
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('versions', nargs='+', help=(
        'The versions to start. (optionally filtered by the --service flag). '
        'Can also be a resource path (<service name>/<version name> or '
        '<project name>/<service name>/<version name>).'))
    parser.add_argument('--service', '-s',
                        help=('If specified, only start versions from the '
                              'given service.'))

  def Run(self, args):
    # TODO(markpell): This fails with "module/version does not exist" even
    # when it exists if the scaling mode is set to auto.  It would be good
    # to improve that error message.

    client = appengine_client.AppengineClient()
    versions = version_util.GetMatchingVersions(client.ListVersions(),
                                                args.versions, args.service,
                                                client.project)

    if not versions:
      log.warn('No matching versions found.')
      return

    printer = console_io.ListPrinter('Starting the following versions:')
    printer.Print(versions, output_stream=log.status)
    console_io.PromptContinue(cancel_on_no=True)

    errors = {}
    for version in versions:
      try:
        with console_io.ProgressTracker('Starting [{0}]'.format(version)):
          client.StartModule(module=version.service, version=version.version)
      except util.RPCError as err:
        errors[version] = str(err)
    if errors:
      printable_errors = {}
      for version, error_msg in errors.items():
        short_name = '[{0}/{1}]'.format(version.service, version.version)
        printable_errors[short_name] = '{0}: {1}'.format(short_name, error_msg)
      raise VersionsStartError(
          'Issues starting version(s): {0}\n\n'.format(
              ', '.join(printable_errors.keys())) +
          '\n\n'.join(printable_errors.values()))
