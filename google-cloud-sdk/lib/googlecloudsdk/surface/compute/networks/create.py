# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating networks."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import networks_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


class _BaseCreate(object):
  """Create a Google Compute Engine network.

  *{command}* is used to create virtual networks. A network
  performs the same function that a router does in a home
  network: it describes the network range and gateway IP
  address, handles communication between instances, and serves
  as a gateway between instances and callers outside the
  network.
  """

  @staticmethod
  def Args(parser):
    """Arguments for command."""
    parser.add_argument(
        '--description',
        help='An optional, textual description for the network.')

    parser.add_argument(
        'name',
        help='The name of the network.')

  @property
  def service(self):
    return self.compute.networks

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'networks'


@base.ReleaseTracks(base.ReleaseTrack.GA)
class Create(_BaseCreate, base_classes.BaseAsyncCreator):
  """Create a Google Compute Engine network.

  *{command}* is used to create virtual networks. A network
  performs the same function that a router does in a home
  network: it describes the network range and gateway IP
  address, handles communication between instances, and serves
  as a gateway between instances and callers outside the
  network.
  """

  @staticmethod
  def Args(parser):
    """Arguments for command."""
    _BaseCreate.Args(parser)

    range_arg = parser.add_argument(
        '--range',
        help='Specifies the IPv4 address range of this network.',
        required=True)
    range_arg.detailed_help = """\
        Specifies the IPv4 address range of this network. The range
        must be specified in CIDR format:
        link:http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing[].
        """

  def CreateRequests(self, args):
    """Returns the request necessary for adding the network."""

    network_ref = self.CreateGlobalReference(
        args.name, resource_type='networks')

    request = self.messages.ComputeNetworksInsertRequest(
        network=self.messages.Network(
            name=network_ref.Name(),
            IPv4Range=args.range,
            description=args.description),
        project=self.project)

    return [request]


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class CreateAlpha(_BaseCreate, base_classes.BaseAsyncCreator):
  """Create a Google Compute Engine network.

  *{command}* is used to create virtual networks. A network
  performs the same function that a router does in a home
  network: it describes the network range and gateway IP
  address, handles communication between instances, and serves
  as a gateway between instances and callers outside the
  network.
  """

  def ComputeDynamicProperties(self, args, items):
    return networks_utils.AddMode(items)

  @staticmethod
  def Args(parser):
    _BaseCreate.Args(parser)

    mode_arg = parser.add_argument(
        '--mode',
        choices=['auto', 'custom', 'legacy'],
        required=True,
        help='The type of network: auto, custom, or legacy.')
    mode_arg.detailed_help = """\
        Mode may be auto, custom, or legacy. It is recommended that you
        create an "auto" where subnets are created for you automatically.
        Custom can be used to create subnets manually. Legacy will create an
        old style network that has a range and cannot have subnets.
        """
    range_arg = parser.add_argument(
        '--range',
        help='Specifies the IPv4 address range of this network.')
    range_arg.detailed_help = """\
        Specifies the IPv4 address range of legacy mode networks. The range
        must be specified in CIDR format:
        http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing.
        """

  def CreateRequests(self, args):
    """Returns the request necessary for adding the network."""

    if args.mode != 'legacy' and args.range is not None:
      raise exceptions.InvalidArgumentException(
          '--range', '--range can only be used if --mode=legacy')

    network_ref = self.CreateGlobalReference(
        args.name, resource_type='networks')

    if args.mode == 'legacy':
      return [self.messages.ComputeNetworksInsertRequest(
          network=self.messages.Network(
              name=network_ref.Name(),
              IPv4Range=args.range,
              description=args.description),
          project=self.project)]

    request = self.messages.ComputeNetworksInsertRequest(
        network=self.messages.Network(
            name=network_ref.Name(),
            autoCreateSubnetworks=args.mode == 'auto',
            description=args.description),
        project=self.project)

    return [request]
