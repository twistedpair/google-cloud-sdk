# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Common classes and functions for firewall rules."""
import re

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as calliope_exceptions

ALLOWED_METAVAR = 'PROTOCOL[:PORT[-PORT]]'
LEGAL_SPECS = re.compile(
    r"""

    (?P<protocol>[a-zA-Z0-9+.-]+) # The protocol group.

    (:(?P<ports>\d+(-\d+)?))?     # The optional ports group.
                                  # May specify a range.

    $                             # End of input marker.
    """,
    re.VERBOSE)


def AddCommonArgs(parser, for_update=False):
  """Adds common arguments for firewall create or update subcommands."""

  min_length = 0 if for_update else 1
  switch = [] if min_length == 0 else None

  allow = parser.add_argument(
      '--allow',
      metavar=ALLOWED_METAVAR,
      type=arg_parsers.ArgList(min_length=min_length),
      action=arg_parsers.FloatingListValuesCatcher(switch_value=switch),
      help='The list of IP protocols and ports which will be allowed.',
      required=not for_update)
  allow.detailed_help = """\
      A list of protocols and ports whose traffic will be allowed.

      PROTOCOL is the IP protocol whose traffic will be allowed.
      PROTOCOL can be either the name of a well-known protocol
      (e.g., tcp or icmp) or the IP protocol number.
      A list of IP protocols can be found at
      link:http://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml[].

      A port or port range can be specified after PROTOCOL to
      allow traffic through specific ports. If no port or port range
      is specified, connections through all ranges are allowed. For
      example, the following will create a rule that allows TCP traffic
      through port 80 and allows ICMP traffic:

        $ {command} MY-RULE --allow tcp:80,icmp

      TCP and UDP rules must include a port or port range.
      """
  if for_update:
    allow.detailed_help += """
      Setting this will override the current values.
      """

  parser.add_argument(
      '--description',
      help='A textual description for the firewall rule.{0}'.format(
          ' Set to an empty string to clear existing.' if for_update else ''))

  source_ranges = parser.add_argument(
      '--source-ranges',
      default=None if for_update else [],
      metavar='CIDR_RANGE',
      type=arg_parsers.ArgList(min_length=min_length),
      action=arg_parsers.FloatingListValuesCatcher(switch_value=switch),
      help=('A list of IP address blocks that may make inbound connections '
            'in CIDR format.'))
  source_ranges.detailed_help = """\
      A list of IP address blocks that are allowed to make inbound
      connections that match the firewall rule to the instances on
      the network. The IP address blocks must be specified in CIDR
      format:
      link:http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing[].
      """
  if for_update:
    source_ranges.detailed_help += """
      Setting this will override the existing source ranges for the firewall.
      The following will clear the existing source ranges:
        $ {command} MY-RULE --source-ranges
      """
  else:
    source_ranges.detailed_help += """
      If neither --source-ranges nor --source-tags is provided, then this
      flag will default to 0.0.0.0/0, allowing all sources. Multiple IP
      address blocks can be specified if they are separated by spaces.
      """

  source_tags = parser.add_argument(
      '--source-tags',
      default=None if for_update else [],
      metavar='TAG',
      type=arg_parsers.ArgList(min_length=min_length),
      action=arg_parsers.FloatingListValuesCatcher(switch_value=switch),
      help=('A list of instance tags indicating the set of instances on the '
            'network which may make network connections that match the '
            'firewall rule.'))
  source_tags.detailed_help = """\
      A list of instance tags indicating the set of instances on the
      network which may make network connections that match the
      firewall rule. If omitted, all instances on the network can
      make connections that match the rule.

      Tags can be assigned to instances during instance creation.
      """
  if for_update:
    source_tags.detailed_help += """
      Setting this will override the existing source tags for the firewall.
      The following will clear the existing source tags:
        $ {command} MY-RULE --source-tags
      """

  target_tags = parser.add_argument(
      '--target-tags',
      default=None if for_update else [],
      metavar='TAG',
      type=arg_parsers.ArgList(min_length=min_length),
      action=arg_parsers.FloatingListValuesCatcher(switch_value=switch),
      help=('A list of instance tags indicating the set of instances on the '
            'network which may make accept inbound connections that match '
            'the firewall rule.'))
  target_tags.detailed_help = """\
      A list of instance tags indicating the set of instances on the
      network which may make accept inbound connections that match the
      firewall rule. If omitted, all instances on the network can
      receive inbound connections that match the rule.

      Tags can be assigned to instances during instance creation.
      """
  if for_update:
    target_tags.detailed_help += """
      Setting this will override the existing target tags for the firewall.
      The following will clear the existing target tags:

        $ {command} MY-RULE --target-tags
      """

  parser.add_argument(
      'name',
      help='The name of the firewall rule to {0}'.format(
          'update.' if for_update else 'create.'))


def ParseAllowed(allowed, message_classes):
  """Parses protocol:port mappings from --allow command line."""
  allowed_value_list = []
  for spec in allowed or []:
    match = LEGAL_SPECS.match(spec)
    if not match:
      raise calliope_exceptions.ToolException(
          'Firewall rules must be of the form {0}; received [{1}].'
          .format(ALLOWED_METAVAR, spec))
    if match.group('ports'):
      ports = [match.group('ports')]
    else:
      ports = []
    allowed_value_list.append(message_classes.Firewall.AllowedValueListEntry(
        IPProtocol=match.group('protocol'),
        ports=ports))

  return allowed_value_list
