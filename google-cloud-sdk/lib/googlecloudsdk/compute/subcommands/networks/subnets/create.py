# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating subnetworks."""

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class Create(base_classes.BaseAsyncCreator):
  """Define a subnet for a network in custom subnet mode."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--description',
        help='An optional description of this subnetwork.')

    parser.add_argument(
        '--network',
        required=True,
        help='The network to which the subnetwork belongs.')

    parser.add_argument(
        '--range',
        required=True,
        help='The IP space allocated to this subnetwork in CIDR format.')

    utils.AddRegionFlag(
        parser,
        resource_type='subnetwork',
        operation_type='create')

    parser.add_argument(
        'name',
        help='The name of the subnetwork.')

  @property
  def service(self):
    return self.compute.subnetworks

  @property
  def method(self):
    return 'Insert'

  @property
  def resource_type(self):
    return 'subnetworks'

  def CreateRequests(self, args):
    """Returns a list of requests necessary for adding a subnetwork."""

    network_ref = self.CreateGlobalReference(
        args.network, resource_type='networks')
    subnet_ref = self.CreateRegionalReference(args.name, args.region)

    request = self.messages.ComputeSubnetworksInsertRequest(
        subnetwork=self.messages.Subnetwork(
            name=subnet_ref.Name(),
            description=args.description,
            network=network_ref.SelfLink(),
            ipCidrRange=args.range
        ),
        region=subnet_ref.region,
        project=self.project)

    return [request]
