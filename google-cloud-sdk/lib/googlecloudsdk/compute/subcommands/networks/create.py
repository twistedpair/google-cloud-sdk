# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating networks."""
from googlecloudsdk.api_lib.compute import base_classes


class Create(base_classes.BaseAsyncCreator):
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
    parser.add_argument(
        '--description',
        help='An optional, textual description for the network.')

    range_arg = parser.add_argument(
        '--range',
        help='Specifies the IPv4 address range of this network.',
        required=True)
    range_arg.detailed_help = """\
        Specifies the IPv4 address range of this network. The range
        must be specified in CIDR format:
        link:http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing[].
        """

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
