# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Code that's shared between multiple routers subcommands."""

import operator

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.console import console_io


_MODE_CHOICES = {
    'DEFAULT': 'Default (Google-managed) BGP advertisements.',
    'CUSTOM': 'Custom (user-configured) BGP advertisements.',
}

_GROUP_CHOICES = {
    'ALL_SUBNETS': 'Automatically advertise all available subnets.',
}

_MODE_SWITCH_MESSAGE = (
    'WARNING: switching from custom advertisement mode to default will clear '
    'out any existing advertised groups/ranges from this {resource}.')

_CUSTOM_WITH_DEFAULT_ERROR_MESSAGE = (
    'Cannot modify custom advertisements for a {resource} with default mode.')


class RouterError(core_exceptions.Error):
  """Error superclass for all router surface-related errors."""


class PeerNotFoundError(RouterError):
  """Raised when a peer is specified but not found in the router."""

  def __init__(self, name):
    self.name = name
    msg = 'peer `{0}` not found'.format(name)
    super(PeerNotFoundError, self).__init__(msg)


class CustomWithDefaultError(RouterError):
  """Raised when custom advertisements are specified with default mode."""

  def __init__(self, messages, resource_class):
    resource_str = _GetResourceClassStr(messages, resource_class)
    error_msg = _CUSTOM_WITH_DEFAULT_ERROR_MESSAGE.format(resource=resource_str)
    super(CustomWithDefaultError, self).__init__(error_msg)


def _GetResourceClassStr(messages, resource_class):
  if resource_class is messages.RouterBgp:
    return 'router'
  elif resource_class is messages.RouterBgpPeer:
    return 'peer'
  else:
    raise ValueError('Invalid resource_class value: {0}'.format(resource_class))


def ParseMode(resource_class, mode):
  return resource_class.AdvertiseModeValueValuesEnum(mode)


def ParseGroups(resource_class, groups):
  return map(resource_class.AdvertisedGroupsValueListEntryValuesEnum, groups)


def ParseRanges(messages, ranges):
  """Parse a dict of IP ranges into AdvertisedPrefix objects.

  Args:
    messages: API messages holder.
    ranges: A dict of IP ranges of the form ip_range=description, where ip_range
            is a CIDR-formatted IP and description is an optional text label.

  Returns:
    A list of AdvertisedPrefix objects containing the specified ranges.
  """
  prefixes = [
      messages.RouterAdvertisedPrefix(prefix=ip_range, description=description)
      for ip_range, description in ranges.items()
  ]
  # Sort the resulting list so that requests have a deterministic ordering
  # for test validations and user output.
  prefixes.sort(key=operator.attrgetter('prefix', 'description'))
  return prefixes


def AddUpdateBgpPeerArgs(parser):
  """Adds common update Bgp peer arguments."""

  parser.add_argument(
      '--peer-name',
      required=True,
      help='The name of the peer being modified.')

  parser.add_argument(
      '--interface',
      help='The name of the new Cloud Router interface for this BGP peer.')

  parser.add_argument(
      '--peer-asn',
      type=int,
      help='The new BGP autonomous system number (ASN) for this BGP peer. '
           'For more information see: https://tools.ietf.org/html/rfc6996.')

  parser.add_argument(
      '--ip-address',
      help='The new link local address of the Cloud Router interface for this '
           'BGP peer. Must be a link-local IP address belonging to the range '
           '169.254.0.0/16 and must belong to same subnet as the interface '
           'address of the peer router.')

  parser.add_argument(
      '--peer-ip-address',
      help='The new link local address of the peer router. Must be a '
           'link-local IP address belonging to the range 169.254.0.0/16.')

  parser.add_argument(
      '--advertised-route-priority',
      type=int,
      help='The priority of routes advertised to this BGP peer. In the case '
           'where there is more than one matching route of maximum length, '
           'the routes with lowest priority value win. 0 <= priority <= '
           '65535.')


def AddCustomAdvertisementArgs(parser, resource_str):
  """Adds common arguments for setting/updating custom advertisements."""

  parser.add_argument(
      '--advertisement-mode',
      choices=_MODE_CHOICES,
      type=lambda mode: mode.upper(),
      metavar='MODE',
      help="""The new advertisement mode for this {0}.""".format(resource_str))

  set_group_range_args = parser.add_argument_group('Custom advertisement flags')

  set_group_range_args.add_argument(
      '--advertisement-groups',
      type=arg_parsers.ArgList(
          choices=_GROUP_CHOICES, element_type=lambda group: group.upper()),
      metavar='GROUP',
      help="""The list of pre-defined groups of prefixes to dynamically
              advertise on this {0}. This list can only be specified in
              custom advertisement mode.""".format(resource_str))

  set_group_range_args.add_argument(
      '--advertisement-ranges',
      type=arg_parsers.ArgDict(allow_key_only=True),
      metavar='CIDR_RANGE=DESC',
      help="""The list of individual IP ranges, in CIDR format, to dynamically
              advertise on this {0}. Each IP range can (optionally) be given a
              text description DESC. For example, to advertise a specific range,
              use `--advertisement-ranges=192.168.10.0/24`.  To store a
              description with the range, use
              `--advertisement-ranges=192.168.10.0/24=my-networks`. This list
              can only be specified in custom advertisement mode."""
      .format(resource_str))


def ParseAdvertisements(messages, resource_class, args):
  """Parses and validates a completed advertisement configuration from flags.

  Args:
    messages: API messages holder.
    resource_class: RouterBgp or RouterBgpPeer class type to parse for.
    args: Flag arguments to generate configuration from.

  Returns:
    The validated tuple of mode, groups and prefixes.  If mode is DEFAULT,
    validates that no custom advertisements were specified and returns empty
    lists for each.

  Raises:
    CustomWithDefaultError: If custom advertisements were specified at the same
    time as DEFAULT mode.
  """

  mode = None
  if args.advertisement_mode is not None:
    mode = ParseMode(resource_class, args.advertisement_mode)
  groups = None
  if args.advertisement_groups is not None:
    groups = ParseGroups(resource_class, args.advertisement_groups)
  prefixes = None
  if args.advertisement_ranges is not None:
    prefixes = ParseRanges(messages, args.advertisement_ranges)

  if (mode is not None and
      mode is resource_class.AdvertiseModeValueValuesEnum.DEFAULT):
    if groups or prefixes:
      raise CustomWithDefaultError(messages, resource_class)
    else:
      # Switching to default mode clears out any existing custom advertisements
      return mode, [], []
  else:
    return mode, groups, prefixes


def ValidateCustomMode(messages, resource_class, resource):
  """Validate that a router/peer is in custom mode."""

  if (resource.advertiseMode
      is not resource_class.AdvertiseModeValueValuesEnum.CUSTOM):
    raise CustomWithDefaultError(messages, resource_class)


def PromptIfSwitchToDefaultMode(
    messages, resource_class, existing_mode, new_mode):
  """If necessary, prompts the user for switching modes."""

  if (existing_mode is not None and
      existing_mode is resource_class.AdvertiseModeValueValuesEnum.CUSTOM and
      new_mode is not None and
      new_mode is resource_class.AdvertiseModeValueValuesEnum.DEFAULT):
    resource_str = _GetResourceClassStr(messages, resource_class)
    console_io.PromptContinue(
        message=_MODE_SWITCH_MESSAGE.format(resource=resource_str),
        cancel_on_no=True)


def FindBgpPeerOrRaise(resource, peer_name):
  """Searches for and returns a BGP peer from within a router resource.

  Args:
    resource: The router resource to find the peer for.
    peer_name: The name of the peer to find.

  Returns:
    A reference to the specified peer, if found.

  Raises:
    PeerNotFoundError: If the specified peer was not found in the router.
  """
  for peer in resource.bgpPeers:
    if peer.name == peer_name:
      return peer
  raise PeerNotFoundError(peer_name)
