# Copyright 2015 Google Inc. All Rights Reserved.

"""Command for adding a BGP peer to a router."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.py27 import copy


class AddBgpPeer(base_classes.ReadWriteCommand):
  """Add a BGP peer to a router."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--peer-name',
        required=True,
        help='The name of the peer being added.')

    parser.add_argument(
        '--peer-asn',
        required=True,
        type=int,
        help='The asn of the peer being added.')

    parser.add_argument(
        '--vpn-tunnel',
        required=True,
        help='The tunnel of the peer being added.')

    parser.add_argument(
        '--ip-address',
        help='The link local address of the router for this peer.')

    parser.add_argument(
        '--peer-ip-address',
        help='The link local address of the peer.')

    parser.add_argument(
        '--mask-length',
        type=int,
        # TODO(stephenmw): better help
        help='The mask for network used for the server and peer IP addresses.')

    utils.AddRegionFlag(
        parser,
        resource_type='router',
        operation_type='update')

    parser.add_argument(
        'name',
        help='The name of the router.')

  @property
  def service(self):
    return self.compute.routers

  @property
  def resource_type(self):
    return 'routers'

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def GetGetRequest(self, args):
    return (self.service,
            'Get',
            self.messages.ComputeRoutersGetRequest(
                router=self.ref.Name(),
                region=self.ref.region,
                project=self.project))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'Update',
            self.messages.ComputeRoutersUpdateRequest(
                router=self.ref.Name(),
                routerResource=replacement,
                region=self.ref.region,
                project=self.project))

  def Modify(self, args, existing):
    replacement = copy.deepcopy(existing)

    mask = None

    # by convention the interface name will be if-name_of_peer
    interface_name = 'if-' + args.peer_name

    if args.ip_address is not None:
      if args.mask_length is not None:
        mask = '{0}/{1}'.format(args.ip_address, args.mask_length)
      else:
        raise exceptions.ToolException(
            '--mask-length must be set if --ip-address is set')

    peer = self.messages.RouterBgpPeer(
        name=args.peer_name,
        interfaceName=interface_name,
        ipAddress=args.ip_address,
        peerIpAddress=args.peer_ip_address,
        peerAsn=args.peer_asn)

    vpn_ref = self.CreateRegionalReference(
        args.vpn_tunnel, args.region, resource_type='vpnTunnels')

    interface = self.messages.RouterInterface(
        name=interface_name,
        linkedVpnTunnel=vpn_ref.SelfLink(),
        ipRange=mask)

    replacement.bgpPeers.append(peer)
    replacement.interfaces.append(interface)

    return replacement


AddBgpPeer.detailed_help = {
    'brief': 'Add a BGP peer to a router.',
    'DESCRIPTION': """
        *{command}* is used to add a BGP peer to a router.
        """,
}
