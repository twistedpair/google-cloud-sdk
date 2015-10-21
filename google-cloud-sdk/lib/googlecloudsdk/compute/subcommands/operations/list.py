# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing operations."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.shared.compute import constants
from googlecloudsdk.shared.compute import request_helper


def AddFlags(parser, is_ga):
  """Helper function for adding flags dependant on the release track."""
  base_classes.BaseLister.Args(parser)
  if is_ga:
    scope = parser.add_mutually_exclusive_group()

    scope.add_argument(
        '--zones',
        metavar='ZONE',
        help=('If provided, only zonal resources are shown. '
              'If arguments are provided, only resources from the given '
              'zones are shown.'),
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(switch_value=[]))
    scope.add_argument(
        '--regions',
        metavar='REGION',
        help=('If provided, only regional resources are shown. '
              'If arguments are provided, only resources from the given '
              'regions are shown.'),
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(switch_value=[]))
    scope.add_argument(
        '--global',
        action='store_true',
        help='If provided, only global resources are shown.',
        default=False)
  else:
    parser.add_argument(
        '--zones',
        metavar='ZONE',
        help=('If arguments are provided, only resources from the given '
              'zones are shown. If no arguments are provided all zonal '
              'operations are shown.'),
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(switch_value=[]))
    parser.add_argument(
        '--regions',
        metavar='REGION',
        help=('If arguments are provided, only resources from the given '
              'regions are shown. If no arguments are provided all regional '
              'operations are shown.'),
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(switch_value=[]))
    parser.add_argument(
        '--global',
        action='store_true',
        help='If provided, all global resources are shown.',
        default=False)
    parser.add_argument(
        '--accounts',
        action='store_true',
        help='If provided, all accounts resources are shown.',
        default=False)


@base.ReleaseTracks(base.ReleaseTrack.GA)
class ListGA(base_classes.BaseLister):
  """List Google Compute Engine operations."""

  def __init__(self, *args, **kwargs):
    super(ListGA, self).__init__(*args, **kwargs)
    self._ga = True

  @staticmethod
  def Args(parser):
    AddFlags(parser, True)

  @property
  def global_service(self):
    return self.compute.globalOperations

  @property
  def regional_service(self):
    return self.compute.regionOperations

  @property
  def zonal_service(self):
    return self.compute.zoneOperations

  @property
  def account_service(self):
    return self.clouduseraccounts.globalAccountsOperations

  @property
  def resource_type(self):
    return 'operations'

  @property
  def allowed_filtering_types(self):
    return ['globalOperations', 'regionOperations', 'zoneOperations']

  def NoArguments(self, args):
    """Determine if the user provided any flags indicating scope."""
    no_compute_args = (args.zones is None and args.regions is None and
                       not getattr(args, 'global'))
    if self._ga:
      return no_compute_args
    else:
      return no_compute_args and not args.accounts

  def GetResources(self, args, errors):
    """Yields zonal, regional, and/or global resources."""
    # This is True if the user provided no flags indicating scope.
    no_scope_flags = self.NoArguments(args)

    requests = []
    filter_expr = self.GetFilterExpr(args)
    max_results = constants.MAX_RESULTS_PER_PAGE
    project = self.project

    # TODO(user): Start using aggregatedList for zones and regions when the
    # operations list API supports them.
    if no_scope_flags:
      requests.append(
          (self.global_service,
           'AggregatedList',
           self.global_service.GetRequestType('AggregatedList')(
               filter=filter_expr,
               maxResults=max_results,
               project=project)))
      if not self._ga:
        # Add a request to get all Compute Account operations.
        requests.append(
            (self.account_service,
             'List',
             self.account_service.GetRequestType('List')(
                 filter=filter_expr,
                 maxResults=max_results,
                 project=project)))
    else:
      if getattr(args, 'global'):
        requests.append(
            (self.global_service,
             'List',
             self.global_service.GetRequestType('List')(
                 filter=filter_expr,
                 maxResults=max_results,
                 project=project)))
      if args.regions is not None:
        args_region_names = [
            self.CreateGlobalReference(region, resource_type='regions').Name()
            for region in args.regions or []]
        # If no regions were provided by the user, fetch a list.
        region_names = (
            args_region_names or [res.name for res in self.FetchChoiceResources(
                attribute='region',
                service=self.compute.regions,
                flag_names=['--regions'])])
        for region_name in region_names:
          requests.append(
              (self.regional_service,
               'List',
               self.regional_service.GetRequestType('List')(
                   filter=filter_expr,
                   maxResults=constants.MAX_RESULTS_PER_PAGE,
                   region=region_name,
                   project=self.project)))
      if args.zones is not None:
        args_zone_names = [
            self.CreateGlobalReference(zone, resource_type='zones').Name()
            for zone in args.zones or []]
        # If no zones were provided by the user, fetch a list.
        zone_names = (
            args_zone_names or [res.name for res in self.FetchChoiceResources(
                attribute='zone',
                service=self.compute.zones,
                flag_names=['--zones'])])
        for zone_name in zone_names:
          requests.append(
              (self.zonal_service,
               'List',
               self.zonal_service.GetRequestType('List')(
                   filter=filter_expr,
                   maxResults=constants.MAX_RESULTS_PER_PAGE,
                   zone=zone_name,
                   project=self.project)))
      if not self._ga and args.accounts:
        requests.append(
            (self.account_service,
             'List',
             self.account_service.GetRequestType('List')(
                 filter=filter_expr,
                 maxResults=max_results,
                 project=project)))

    return request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None)


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class ListBeta(ListGA):
  """List Google Compute Engine operations."""

  def __init__(self, *args, **kwargs):
    super(ListBeta, self).__init__(*args, **kwargs)
    self._ga = False

  @staticmethod
  def Args(parser):
    AddFlags(parser, False)


ListGA.detailed_help = base_classes.GetGlobalRegionalListerHelp('operations')
ListBeta.detailed_help = {
    'brief': 'List Google Compute Engine operations',
    'DESCRIPTION': """\
        *{command}* displays all Google Compute Engine operations in a
        project.

        By default, all global, regional, zonal and Compute Accounts operations
        are listed. The results can be narrowed by providing combinations of
        the --zones, --regions, --global and --accounts flags.
        """,
    'EXAMPLES': """\
        To list all operations in a project in table form, run:

          $ {command}

        To list the URIs of all operations in a project, run:

          $ {command} --uri

        To list all operations in zones us-central1-b and
        europe-west1-d, run:

           $ {command} --regions us-central1 europe-west1

        To list all global operations in a project, run:

           $ {command} --global

        To list all regional operations in a project, run:

           $ {command} --regions

        To list all operations in the us-central1 and europe-west1
        regions and all operations in the us-central1-a zone, run:

           $ {command} --zones us-central1-a \\
               --regions us-central1 europe-west1

        To list all Compute Accounts operations, run:

           $ {command} --accounts
        """,
}
