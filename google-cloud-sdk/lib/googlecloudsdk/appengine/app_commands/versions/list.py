# Copyright 2015 Google Inc. All Rights Reserved.
"""`gcloud app versions list` command."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log

from googlecloudsdk.appengine.lib import appengine_client


class ServiceNotFoundError(exceptions.Error):
  pass


class List(base.Command):
  """List your existing versions.

  This command lists all the versions of all services that are currently
  deployed to the App Engine server.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list all services and versions, run:

            $ {command}

          To list all versions for a specific service, run:

            $ {command} --service service1

          To list only versions that are receiving traffic, run:

            $ {command} --hide-no-traffic
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument('--service', '-s',
                        help='Only show versions from this service.')
    parser.add_argument('--hide-no-traffic', action='store_true',
                        help='Only show versions that are receiving traffic.')

  def Run(self, args):
    client = appengine_client.AppengineClient()
    services = client.ListModules()
    log.debug('All services: {0}'.format(services))

    if args.service and args.service not in services:
      raise ServiceNotFoundError(
          'Service [{0}] not found.'.format(args.service))

    versions = []
    for service, versions_for_service in sorted(services.iteritems()):
      if not versions_for_service or not isinstance(versions, list):
        log.warn('Unexpected version list for service [{0}]'.format(service))
        continue
      if args.service and service != args.service:
        # Not for a service we are interested in.
        continue

      # First version is always the default version (from the API).
      default_version = versions_for_service[0]
      for version in sorted(versions_for_service):
        traffic_split_percentage = 100 if (version == default_version) else 0
        versions.append({
            'service': service,
            'version': version,
            'traffic_split': traffic_split_percentage
        })

    if args.hide_no_traffic:
      versions = [v for v in versions if v['traffic_split']]
    return versions

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('app.versions', result)
