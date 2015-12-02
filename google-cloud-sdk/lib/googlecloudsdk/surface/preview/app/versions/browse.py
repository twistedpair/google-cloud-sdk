# Copyright 2015 Google Inc. All Rights Reserved.

"""The Browse command."""


from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import deploy_command_util
from googlecloudsdk.api_lib.app import version_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.appengine.api import appinfo


class UnsupportedAppIdError(exceptions.Error):
  pass


def OpenInBrowser(url):
  # pylint: disable=g-import-not-at-top
  # Import in here for performance reasons
  import webbrowser
  # pylint: enable=g-import-not-at-top
  webbrowser.open_new_tab(url)


class Browse(base.Command):
  """Open the specified versions in a browser.

  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To show version `v1` for the default service in the browser, run:

              $ {command} v1

          To show version `v1` of a specific service in the browser, run:

              $ {command} v1 --service="myService"

          To show multiple versions side-by-side, run:

              $ {command} v1 v2 --service="myService"
          """,
  }

  @staticmethod
  def Args(parser):
    versions = parser.add_argument('versions', nargs='+',
                                   help='The versions to open.')
    versions.detailed_help = (
        'The versions to open. (optionally filtered by the --service flag). '
        'Can also be a resource path (<service name>/<version name> or '
        '<project name>/<service name>/<version name>).')
    parser.add_argument('--service', '-s',
                        help=('If specified, only open versions from the '
                              'given service. If not specified, use the '
                              'default service.'))

  def Run(self, args):
    if ':' in properties.VALUES.core.project.Get(required=True):
      raise UnsupportedAppIdError(
          '`browse` command is currently unsupported for app IDs with custom '
          'domains.')
    client = appengine_client.AppengineClient()
    versions = version_util.GetMatchingVersions(client.ListVersions(),
                                                args.versions, args.service,
                                                client.project)
    if not args.service and not any('/' in v for v in args.versions):
      # If no resource paths were provided and the service was not specified,
      # assume the default service.
      versions = [v for v in versions if v.service == 'default']

    if not versions:
      log.warn('No matching versions found.')

    for version in versions:
      # Assume HTTPS. There's not enough information to determine based on the
      # results of ListVersions, but HTTPS is always more secure (though HTTP
      # will work in all cases, since it will redirect to HTTPS).
      url = deploy_command_util.GetAppHostname(version.project, version.service,
                                               version.version,
                                               use_ssl=appinfo.SECURE_HTTPS)
      log.status.Print(
          'Opening [{0}] in a new tab in your default browser.'.format(url))
      OpenInBrowser(url)
