# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A module for Service Registry address parsing with argparse."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions

COMPUTE_RESOURCE_URL = 'https://www.googleapis.com/compute/v1/projects/{0}/global/networks/{1}'


class ArgEndpointAddress(arg_parsers.ArgType):
  """Interpret an argument value as an EndpointAddress."""

  def __call__(self, arg_value):
    """Parses arg_value into an EndpointAddress.

    Args:
      arg_value: A simple or "full" address. Simple addresses are just the
        address (IPv6/v4 or domain) optionally followed by a :PORT. Full
        addresses are of the form
          address=ADRESS[;port_number=NUM[,protocol=PROTOCOL][,port_name=NAME]]+
        port_name must be specified if more than one port specification is
        supplied for the address.
    Returns:
      An EndpointAddress represented by arg_value
    """
    self.arg_value = arg_value

    if not arg_value:
      self.raiseValidationError('Address arguments can not be empty')

    messages = apis.GetMessagesModule('serviceregistry', 'v1alpha')
    if arg_value.startswith('address='):
      # It's a keyed address
      arg_parts = arg_value.split(';')
      address_parts = arg_parts[0].split('=')

      if len(address_parts) < 2:
        self.raiseValidationError('The address can not be empty.')

      address = address_parts[1]
      ports = self.parse_port_specs(address_parts[1], arg_parts[1:])
      return messages.EndpointAddress(address=address, ports=ports)
    elif ';' in arg_value or ',' in arg_value:
      # Don't let users accidentally mix the simple and keyed schemes
      self.raiseValidationError(
          'The target specification contains a comma or semi-colon and looks '
          'like a fully keyed target specification. This format must begin '
          'with address=')
    else:
      # It's just an ADDRESS:PORT
      host_port = arg_parsers.HostPort.Parse(arg_value, ipv6_enabled=True)

      endpoint_address = messages.EndpointAddress(address=host_port.host)

      if host_port.port:
        endpoint_address.ports = [
            messages.EndpointPort(portNumber=int(host_port.port))
        ]

      return endpoint_address

  def parse_port_specs(self, address, port_specifications):
    name_required = len(port_specifications) > 1

    messages = apis.GetMessagesModule('serviceregistry', 'v1alpha')
    ports = []
    for port_spec in port_specifications:
      if not port_spec:
        self.raiseValidationError('Port specifications can not be empty.')

      port_number, port_name, protocol = self.parse_single_port_spec(port_spec)
      if name_required and not port_name:
        self.raiseValidationError(
            '"port_name" is required when adding multiple ports to an address.')
      endpoint_port = messages.EndpointPort(portNumber=port_number)
      if port_name:
        endpoint_port.name = port_name
      if protocol:
        endpoint_port.protocol = protocol
      ports.append(endpoint_port)

    return ports

  def parse_single_port_spec(self, port_spec):
    port_args = port_spec.split(',')
    port_number = None
    port_name = None
    protocol = None
    for arg in port_args:
      if 'protocol=' in arg:
        if not protocol:
          protocol = arg.split('protocol=')[1]
        else:
          self.raiseValidationError(
              'Multiple protocols are not allowed in an endpoint port.')
      elif 'port_name=' in arg:
        if not port_name:
          port_name = arg.split('port_name=')[1]
        else:
          self.raiseValidationError(
              'Multiple port_names are not allowed in an endpoint port.')
      elif 'port_number=' in arg:
        if not port_number:
          try:
            port_number = int(arg.split('port_number=')[1])
          except (ValueError, TypeError):
            self.raiseValidationError(
                'port_number must be an integer.')
        else:
          self.raiseValidationError(
              'Multiple port_numbers are not allowed in an endpoint port.')
      elif arg:
        self.raiseValidationError(
            'Ports only take port_number, port_name and protocol arguments.')

    if not port_number:
      self.raiseValidationError(
          'You must specify a port_number for an endpoint port.')

    return port_number, port_name, protocol

  def raiseValidationError(self, message):
    """Constructs an InvalidArgumentException using message and the arg value.

    Args:
      message: The specific error message.
    Raises:
      InvalidArgumentException: The address argument being validated was
        malformed.
    """
    raise exceptions.InvalidArgumentException(
        'address',
        'Bad address argument [{0}]. {1}'.format(self.arg_value, message))


def AddTargetArg(parser):
  """Called by commands to add an address argument.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument(
      '--target',
      type=ArgEndpointAddress(),
      action='append',
      required=True,
      help='A target specifies an address (with optional ports) for an '
      'endpoint. This argument is repeatable for multiple addresses and can '
      'take the form of a single address (hostname, IPv4, or IPv6) and port:'
      '\n\n  ADDRESS[:PORT]\n\n'
      'In this format you must enclose IPv6 addresses in square brackets: '
      'e.g.\n\n'
      '  [2001:db8:0:0:0:ff00:42:8329]:8080\n\n'
      'You can also use a fully keyed version when you want to specify '
      'port details:\n\n'
      '  address=ADDRESS[;port_number=PORT[,protocol=PROTOCOL]'
      '[,port_name=name]]+\n\n'
      'port specifications are separated by semi-colons, and the '
      '"address=" portion must come first. If you are specifying more than one '
      'port, then port_name is required.',
      metavar='TARGET')


def ExpandNetworks(networks, project):
  """Parses networks into fully qualified Compute Engine network URLs.

  The URLs will be a compute/v1 reference.

  Args:
    networks: A list of full Compute Engine network URLs or just the network
      name.
    project: The project name these networks are associated with.

  Returns:
    A full GCP network url String.
  """
  expanded_networks = []
  for network in networks:
    if network.startswith('https://'):
      expanded_networks.append(network)
    else:
      expanded_networks.append(COMPUTE_RESOURCE_URL.format(project, network))
  return expanded_networks


def AddNetworksArg(parser):
  """Called by commands to add a networks argument.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument(
      '--networks',
      type=arg_parsers.ArgList(),
      help='A comma separated list of networks your endpoint should have '
      'private DNS records created in. Each network is represented by its name '
      'or a full resource url. For example, to refer to the default network '
      ' in "my-project", you can use\n\n'
      '   default\n\n'
      'or\n\n'
      '   https://www.googleapis.com/compute/v1/projects/my-project/global/networks/default\n\n',  # pylint:disable=line-too-long
      metavar='NETWORKS',
      default=[])


def AddEndpointNameArg(parser):
  """Provides the endpoint_name arg.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument('endpoint_name', help='Endpoint name.')


def AddAsyncArg(parser):
  """Provides the async arg.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument(
      '--async',
      help='Return immediately and print information about the Operation in '
      'progress rather than waiting for the Operation to complete. '
      '(default=False)',
      dest='async',
      default=False,
      action='store_true')


def AddDescriptionArg(parser):
  """Provides the description arg.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument(
      '--description',
      type=str,
      help='A description of your endpoint.',
      default='',
      metavar='DESCRIPTION')


def AddEnableExternalArg(parser):
  """Provides the enableExternal arg.

  Args:
    parser: argparse parser for specifying command line arguments
  """
  parser.add_argument(
      '--enable-external',
      help='Externalize the endpoint through a cloud.goog record.'
      '(default=False)',
      default=False,
      action='store_true')
