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

"""Service Registry transforms and symbols dict."""


def _GetWithPrefix(item, attribute, prefix):
  """Convenience method to get an attribute from an item and attach a prefix.

  Args:
    item: Any dict-like object with attribute fetching provided by 'get'.
    attribute: Attribute to retrieve from item.
    prefix: A string prefix for the returned string, if item.attribute has
        a value.

  Returns:
    Grabs the attribute from item if it exists and returns it with prefix
    prepended.
  """
  value = item.get(attribute, None)
  if value:
    value = str(prefix) + str(value)
  return value


def _BuildPortDisplayComponents(ports):
  """Build a list representation for one or more ports.

  Args:
    ports: JSON-serializable representation of address ports.

  Returns:
    A list meant to be joined into a string representing the ports.
  """
  port_components = []
  for port in ports:
    port_components.append(';')

    name = _GetWithPrefix(port, 'name', 'port_name=')
    if name:
      port_components.append(name)

    number = _GetWithPrefix(port, 'portNumber', ',port_number=')
    if number:
      port_components.append(number)

    protocol = _GetWithPrefix(port, 'protocol', ',protocol=')
    if protocol:
      port_components.append(protocol)

  return port_components


def _HasOneSimplePort(ports):
  """Check if this list of ports only contains a single simple port.

  Args:
    ports: JSON-serializable representation of address ports.

  Returns:
    True if ports is length 1 and the only attribute is just a port number
    with no protocol.
  """
  if len(ports) == 1:
    protocol = ports[0].get('protocol', None)
    port_name = ports[0].get('name', None)
    return (not protocol) and (not port_name)
  else:
    return False


def TransformEndpointAddress(r, undefined=''):
  """Returns a compact representation of an endpoint address.

  The compact representation for a plain address (no port information) is
  just the address. The compact representation for an address with a port
  is of the form [HOST/IP]:PORT and addresses with more details or more ports
  will look like

    address=ADDRESS[;port_number=PORT[,protocol=PROTOCOL][,port_name=name]]+

  Args:
    r: JSON-serializable representation of a Service Registry address.
    undefined: Returns this value if the resource cannot be formatted.

  Returns:
    A compact string describing the address, r.

  Example:
    `--format="table(name, addresses[].map().endpoint_address())"`:::
    Displays each address as an endpoint address.
  """
  display_components = []
  address = None if not r else r.get('address', None)
  if address:
    display_components.append(address)
    ports = r.get('ports', None)
    if ports:
      if _HasOneSimplePort(ports):
        display_components += [':', str(ports[0].get('portNumber'))]
      else:
        display_components = ['address='] + display_components
        display_components += _BuildPortDisplayComponents(ports)
    return ''.join(display_components)
  return undefined


_TRANSFORMS = {'endpoint_address': TransformEndpointAddress}


def GetTransforms():
  """Returns the service registry specific resource transform symbol table."""
  return _TRANSFORMS

