# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for deleting access configs from virtual machine instances."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import utils


class DeleteAccessConfig(base_classes.NoOutputAsyncMutator):
  """Delete an access configuration from a virtual machine network interface.

  *{command}* is used to delete access configurations from network
  interfaces of Google Compute Engine virtual machines.
  """

  @staticmethod
  def Args(parser):
    utils.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='delete an access config from')

    access_config_name = parser.add_argument(
        '--access-config-name',
        default=constants.DEFAULT_ACCESS_CONFIG_NAME,
        help='Specifies the name of the access configuration to delete.')
    access_config_name.detailed_help = """\
        Specifies the name of the access configuration to delete.
        ``{0}'' is used as the default if this flag is not provided.
        """.format(constants.DEFAULT_ACCESS_CONFIG_NAME)

    parser.add_argument(
        'name',
        completion_resource='compute.instances',
        help=('The name of the instance from which to delete the access '
              'configuration.'))

    network_interface = parser.add_argument(
        '--network-interface',
        default='nic0',
        help=('Specifies the name of the network interface from which to '
              'delete the access configuration.'))
    network_interface.detailed_help = """\
        Specifies the name of the network interface from which to delete the
        access configuration. If this is not provided, then ``nic0'' is used
        as the default.
        """

  @property
  def service(self):
    return self.compute.instances

  @property
  def method(self):
    return 'DeleteAccessConfig'

  @property
  def resource_type(self):
    return 'instances'

  def CreateRequests(self, args):
    """Returns a request necessary for removing an access config."""
    instance_ref = self.CreateZonalReference(args.name, args.zone)

    request = self.messages.ComputeInstancesDeleteAccessConfigRequest(
        accessConfig=args.access_config_name,
        instance=instance_ref.Name(),
        networkInterface=args.network_interface,
        project=self.project,
        zone=instance_ref.zone)

    return [request]
