# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for describing operations."""


from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources as resource_exceptions


def AddFlags(parser, is_ga):
  """Helper function for adding flags dependant on the release track."""
  base_classes.BaseDescriber.Args(parser)
  base_classes.AddFieldsFlag(parser, 'operations')

  scope = parser.add_mutually_exclusive_group()

  scope.add_argument(
      '--global',
      action='store_true',
      help=('If provided, it is assumed that the requested operation is '
            'global.'))

  scope.add_argument(
      '--region',
      help='The region of the operation to fetch.',
      action=actions.StoreProperty(properties.VALUES.compute.region))

  scope.add_argument(
      '--zone',
      help='The zone of the operation to fetch.',
      action=actions.StoreProperty(properties.VALUES.compute.zone))

  if not is_ga:
    scope.add_argument(
        '--user-accounts',
        action='store_true',
        help=('If provided, it is assumed that the requested operation is '
              'a Compute User Accounts operation.'))


@base.ReleaseTracks(base.ReleaseTrack.GA)
class DescribeGA(base_classes.BaseDescriber):
  """Describe a Google Compute Engine operation."""

  def __init__(self, *args, **kwargs):
    super(DescribeGA, self).__init__(*args, **kwargs)
    self._ga = True

  @staticmethod
  def Args(parser):
    AddFlags(parser, True)

  @property
  def service(self):
    return self._service

  def ReferenceFromUri(self, args):
    """Helper function for creating a ref from a Uri."""
    try:
      ref = self.resources.Parse(args.name, params={
          'region': args.region, 'zone': args.zone})
      return ref
    except resource_exceptions.InvalidResourceException as e:
      if not self._ga:
        ref = self.clouduseraccounts_resources.Parse(
            args.name)
        return ref
      else:
        raise e

  def ValidCollection(self, ref):
    """Helper function for checking a reference is for an operation."""
    if self._ga:
      return ref.Collection() in (
          'compute.globalOperations',
          'compute.regionOperations',
          'compute.zoneOperations')
    else:
      return ref.Collection() in (
          'compute.globalOperations',
          'compute.regionOperations',
          'compute.zoneOperations',
          'clouduseraccounts.globalAccountsOperations')

  def CreateReference(self, args):
    try:
      ref = self.ReferenceFromUri(args)
    except resource_exceptions.UnknownCollectionException:
      if getattr(args, 'global'):
        ref = self.CreateGlobalReference(
            args.name, resource_type='globalOperations')
      elif args.region:
        ref = self.CreateRegionalReference(
            args.name, args.region, resource_type='regionOperations')
      elif args.zone:
        ref = self.CreateZonalReference(
            args.name, args.zone, resource_type='zoneOperations')
      elif not self._ga and args.user_accounts:
        ref = self.CreateAccountsReference(
            args.name, resource_type='globalAccountsOperations')
      else:
        # TODO(user): Instead of raising here, we should really just
        # prompt for {global, <list of regions>, <list of zones>}, but
        # for now, it's more important to go into GA than to solve
        # this small problem.
        raise exceptions.ToolException(
            ('Either pass in the full URI of an operation object or pass in '
             '[--global], [--region], or [--zone] when specifying just the '
             'operation name.') if self._ga else
            ('Either pass in the full URI of an operation object or pass in '
             '[--global], [--region], [--zone], or [--user-accounts] when '
             'specifying just the operation name.'))

    if not self.ValidCollection(ref):
      raise exceptions.ToolException(
          ('You must pass in a reference to a global, regional, or zonal '
           'operation.') if self._ga else
          ('You must pass in a reference to a global, regional, zonal, or '
           'user accounts operation.'))
    else:
      if ref.Collection() == 'compute.globalOperations':
        self._service = self.compute.globalOperations
      elif ref.Collection() == 'compute.regionOperations':
        self._service = self.compute.regionOperations
      elif ref.Collection() == 'clouduseraccounts.globalAccountsOperations':
        self._service = self.clouduseraccounts.globalAccountsOperations
      else:
        self._service = self.compute.zoneOperations
      return ref

  def ScopeRequest(self, ref, request):
    if ref.Collection() == 'compute.regionOperations':
      request.region = ref.region
    elif ref.Collection() == 'compute.zoneOperations':
      request.zone = ref.zone


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class DescribeBeta(DescribeGA):
  """Describe a Google Compute Engine operation."""

  def __init__(self, *args, **kwargs):
    super(DescribeBeta, self).__init__(*args, **kwargs)
    self._ga = False

  @staticmethod
  def Args(parser):
    AddFlags(parser, False)


def DetailedHelp(version):
  """Construct help text based on the command release track."""
  detailed_help = {
      'brief': 'Describe a Google Compute Engine operation',
      'DESCRIPTION': """\
        *{command}* displays all data associated with a Google Compute
        Engine operation in a project.
        """,
      'EXAMPLES': """\
        To get details about a global operation, run:

          $ {command} OPERATION --global

        To get details about a regional operation, run:

          $ {command} OPERATION --region us-central1

        To get details about a zonal operation, run:

          $ {command} OPERATION --zone us-central1-a
        """,
  }
  if version == 'BETA':
    detailed_help['EXAMPLES'] = """\
        To get details about a global operation, run:

          $ {command} OPERATION --global

        To get details about a regional operation, run:

          $ {command} OPERATION --region us-central1

        To get details about a zonal operation, run:

          $ {command} OPERATION --zone us-central1-a

        To get details about a Compute User Accounts operation, run:

          $ {command} OPERATION --user-accounts
        """
  return detailed_help

DescribeGA.detailed_help = DetailedHelp('GA')
DescribeBeta.detailed_help = DetailedHelp('BETA')
