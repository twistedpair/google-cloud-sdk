# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Common flags for network connectivity commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.network_connectivity import util
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


GLOBAL_ARGUMENT = '--global'
REGION_ARGUMENT = '--region'


def AddExcludeExportRangesFlag(parser, hide_exclude_export_ranges_flag):
  """Adds the --exclude-export-ranges argument to the given parser."""
  parser.add_argument(
      '--exclude-export-ranges',
      required=False,
      type=arg_parsers.ArgList(),
      default=[],
      metavar='CIDR_RANGE',
      hidden=hide_exclude_export_ranges_flag,
      help="""Subnet IP address range(s) to hide from other VPC networks that are
        connected through Network Connectivity Center.""")


def AddIncludeExportRangesFlag(parser, hide_include_export_ranges_flag):
  """Adds the --include-export-ranges argument to the given parser."""

  parser.add_argument(
      '--include-export-ranges',
      required=False,
      type=arg_parsers.ArgList(),
      default=[],
      metavar='CIDR_RANGE',
      hidden=hide_include_export_ranges_flag,
      help="""Subnet IP address range(s) to export to other VPC networks that are
        connected through Network Connectivity Center.""",
  )


def AddUpdateIncludeExportRangesFlag(
    parser, hide_include_export_ranges_flag
):
  """Adds the --include-export-ranges argument to the update operation parser."""

  parser.add_argument(
      '--include-export-ranges',
      required=False,
      type=arg_parsers.ArgList(),
      default=None,
      metavar='CIDR_RANGE',
      hidden=hide_include_export_ranges_flag,
      help="""New include export ranges of the spoke.""",
  )


def AddUpdateExcludeExportRangesFlag(
    parser, hide_exclude_export_ranges_flag
):
  """Adds the --exclude-export-ranges argument to the update operation parser."""

  parser.add_argument(
      '--exclude-export-ranges',
      required=False,
      type=arg_parsers.ArgList(),
      default=None,
      metavar='CIDR_RANGE',
      hidden=hide_exclude_export_ranges_flag,
      help="""New exclude export ranges of the spoke.""",
  )


def GetCapacityArg(gateway_message):
  return arg_utils.ChoiceEnumMapper(
      arg_name='--capacity',
      message_enum=gateway_message.CapacityValueValuesEnum,
      custom_mappings={
          'CAPACITY_1_GBPS': ('1g', 'Gateway will have capacity of 1 Gbps'),
          'CAPACITY_10_GBPS': ('10g', 'Gateway will have capacity of 10 Gbps'),
          'CAPACITY_100_GBPS': (
              '100g',
              'Gateway will have capacity of 100 Gbps',
          ),
      },
      help_str='Set the capacity of the gateway in Gbps.',
      required=True,
  )


def AddCapacityFlag(gateway_message, parser):
  GetCapacityArg(gateway_message).choice_arg.AddToParser(parser)


def AddIpRangeReservationsFlag(parser):
  """Adds the --ip-range-reservation argument to the given parser."""
  parser.add_argument(
      '--ip-range-reservations',
      required=True,
      type=arg_parsers.ArgList(),
      default=[],
      metavar='CIDR_RANGE',
      help="""The IP range reservation for the spoke.""",
  )


def AddLandingNetworkFlag(parser):
  """Adds the --landing-network argument to the given parser."""
  # TODO: b/233653552 - Parse this with a resource argument.
  parser.add_argument(
      '--landing-network',
      help="""The landing network for the spoke. The network must already
      exist.""",
  )


def AddAsyncFlag(parser):
  """Add the --async argument to the given parser."""
  base.ASYNC_FLAG.AddToParser(parser)


def AddHubFlag(parser):
  """Adds the --hub argument to the given parser."""
  # TODO(b/233653552) Parse this with a resource argument.
  parser.add_argument(
      '--hub',
      required=True,
      help='Hub that the spoke will attach to. The hub must already exist.')


def AddSpokeFlag(parser, help_text):
  """Adds the --spoke flag to the given parser."""
  parser.add_argument(
      '--spoke',
      required=True,
      help=help_text)


def AddSpokeEtagFlag(parser, help_text):
  """Adds the --spoke-etag flag to the given parser."""
  parser.add_argument(
      '--spoke-etag',
      required=True,
      help=help_text)


def AddGroupFlag(parser, required=False):
  """Adds the --group argument to the given parser."""
  # TODO(b/233653552) Parse this with a resource argument.
  if required:
    parser.add_argument(
        '--group',
        required=True,
        hidden=False,
        help=(
            'Group that the spoke will be part of. The group must already'
            ' exist.'
        ),
    )
  else:
    parser.add_argument(
        '--group',
        required=False,
        hidden=True,
        help=(
            'Group that the spoke will be part of. The group must already'
            ' exist.'
        ),
    )


def AddNetworkFlag(parser):
  """Adds the --network argument to the given parser."""
  parser.add_argument(
      '--network',
      required=True,
      help="""Your VPC network that contains the peering to the Producer VPC,
      which this spoke connects to the Hub. The peering must already exist and
      be in the ACTIVE state.""")


def AddPeeringFlag(parser):
  """Adds the --peering argument to the given parser."""
  parser.add_argument(
      '--peering',
      required=True,
      help="""Peering between your network and the Producer VPC, which this
      spoke connects to the Hub. The peering must already exist and be in the
      ACTIVATE state.""")


def AddVPCNetworkFlag(parser):
  """Adds the --vpc-network argument to the given parser."""
  # TODO(b/233653552) Parse this with a resource argument.
  parser.add_argument(
      '--vpc-network',
      required=True,
      help="""VPC network that the spoke provides connectivity to.
      The resource must already exist.""")


def AddDescriptionFlag(parser, help_text):
  """Adds the --description flag to the given parser."""
  parser.add_argument(
      '--description',
      required=False,
      help=help_text)


def AddRejectionDetailsFlag(parser):
  """Adds the --details flag to the given parser."""
  parser.add_argument(
      '--details',
      required=False,
      help="""Additional details behind the rejection""")


def AddGlobalFlag(parser, hidden):
  """Add the --global argument to the given parser."""
  parser.add_argument(
      GLOBAL_ARGUMENT,
      help='Indicates that the spoke is global.',
      hidden=hidden,
      action=util.StoreGlobalAction)


def AddRegionFlag(parser, supports_region_wildcard, hidden, required):
  """Add the --region argument to the given parser."""
  region_help_text = """ \
        A Google Cloud region. To see the names of regions, see [Viewing a list of available regions](https://cloud.google.com/compute/docs/regions-zones/viewing-regions-zones#viewing_a_list_of_available_regions)."""  # pylint: disable=line-too-long
  if supports_region_wildcard:
    region_help_text += ' Use ``-`` to specify all regions.'
  parser.add_argument(
      REGION_ARGUMENT, hidden=hidden, required=required, help=region_help_text
  )


def AddRegionGroup(parser,
                   supports_region_wildcard=False,
                   hide_global_arg=False,
                   hide_region_arg=False):
  """Add a group which contains the global and region arguments to the given parser."""
  region_group = parser.add_group(required=False, mutex=True)
  AddGlobalFlag(region_group, hide_global_arg)
  AddRegionFlag(
      region_group, supports_region_wildcard, hide_region_arg, required=False
  )


def AddSpokeLocationsFlag(parser):
  """Add the --spoke-locations argument to the given parser."""
  spoke_locations_help_text = """ \
        A comma separated list of locations. The locations can be set to 'global'
        and/or Google Cloud supported regions. To see the names of regions, see
        [Viewing a list of available regions](https://cloud.google.com/compute/docs/regions-zones/viewing-regions-zones#viewing_a_list_of_available_regions)."""
  parser.add_argument(
      '--spoke-locations',
      required=False,
      help=spoke_locations_help_text,
      type=arg_parsers.ArgList(),
      default=[],
      metavar='LOCATION')


def AddViewFlag(parser):
  """Add the --view argument to the given parser."""
  view_help_text = """ \
       Enumeration to control which spoke fields are included in the response."""
  parser.add_argument(
      '--view',
      required=False,
      choices=['basic', 'detailed'],
      default='basic',
      help=view_help_text)


def AddHubResourceArg(parser, desc):
  """Add a resource argument for a hub.

  Args:
    parser: the parser for the command.
    desc: the string to describe the resource, such as 'to create'.
  """
  hub_concept_spec = concepts.ResourceSpec(
      'networkconnectivity.projects.locations.global.hubs',
      resource_name='hub',
      hubsId=HubAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)

  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='hub',
      concept_spec=hub_concept_spec,
      required=True,
      group_help='Name of the hub {}.'.format(desc))
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddGroupResourceArg(parser, desc):
  """Add a resource argument for a group.

  Args:
    parser: the parser for the command.
    desc: the string to describe the resource, such as 'to create'.
  """
  group_concept_spec = concepts.ResourceSpec(
      'networkconnectivity.projects.locations.global.hubs.groups',
      resource_name='group',
      api_version='v1',
      groupsId=GroupAttributeConfig(),
      hubsId=HubAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)

  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='group',
      concept_spec=group_concept_spec,
      required=True,
      group_help='Name of the group {}.'.format(desc))
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def SpokeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='spoke', help_text='The spoke Id.')


def HubAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='hub', help_text='The hub Id.'
  )


def GroupAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='group', help_text='The group Id.'
  )


def LocationAttributeConfig(location_arguments, region_resource_command=False):
  """Get a location argument with the appropriate fallthroughs."""
  location_fallthroughs = [
      deps.ArgFallthrough(arg) for arg in location_arguments
  ]
  # If this is an attribute for a region resource, add '-' as a fallthrough
  # to default to all regions.
  if region_resource_command:
    location_fallthroughs.append(
        deps.Fallthrough(
            function=lambda: '-',
            hint='defaults to all regions if not specified'))
  return concepts.ResourceParameterAttributeConfig(
      name='location',
      help_text='The location Id.',
      fallthroughs=location_fallthroughs)


def TransportAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='transport', help_text='The transport Id.'
  )


def RemoteProfileAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='remote_profile',
      help_text='The remote profile Id.',
  )


def GetSpokeResourceSpec(location_arguments):
  return concepts.ResourceSpec(
      'networkconnectivity.projects.locations.spokes',
      resource_name='spoke',
      spokesId=SpokeAttributeConfig(),
      locationsId=LocationAttributeConfig(location_arguments),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetRegionResourceSpec(location_arguments):
  return concepts.ResourceSpec(
      'networkconnectivity.projects.locations',
      resource_name='region',
      locationsId=LocationAttributeConfig(
          location_arguments, region_resource_command=True
      ),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False,
  )


def GetTransportResourceSpec(location_arguments):
  return concepts.ResourceSpec(
      'networkconnectivity.projects.locations.transports',
      resource_name='transport',
      transportsId=TransportAttributeConfig(),
      locationsId=LocationAttributeConfig(location_arguments),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      api_version='v1beta',
      disable_auto_completers=False,
  )


def GetRemoteProfileResourceSpec(location_arguments):
  return concepts.ResourceSpec(
      'networkconnectivity.projects.locations.remoteTransportProfiles',
      resource_name='remoteProfile',
      remoteTransportProfilesId=RemoteProfileAttributeConfig(),
      locationsId=LocationAttributeConfig(location_arguments),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      api_version='v1beta',
      disable_auto_completers=False,
  )


def GetResourceLocationArguments(resource_location_type):
  mapping = {
      ResourceLocationType.GLOBAL_ONLY: [GLOBAL_ARGUMENT],
      ResourceLocationType.REGION_ONLY: [REGION_ARGUMENT],
      ResourceLocationType.REGION_AND_GLOBAL: [
          GLOBAL_ARGUMENT,
          REGION_ARGUMENT,
      ],
  }
  return mapping[resource_location_type]


@enum.unique
class ResourceLocationType(enum.Enum):
  """Type of locations supported by a resource."""
  GLOBAL_ONLY = enum.auto()
  REGION_ONLY = enum.auto()
  REGION_AND_GLOBAL = enum.auto()


def AddSpokeResourceArg(
    parser, verb, resource_location_type=ResourceLocationType.REGION_AND_GLOBAL
):
  """Add a resource argument for a spoke.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    resource_location_type: ResourceLocationType, the type of locations
      supported by the resource.
  """
  location_arguments = GetResourceLocationArguments(resource_location_type)
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='spoke',
      concept_spec=GetSpokeResourceSpec(location_arguments),
      required=True,
      flag_name_overrides={'location': ''},
      group_help='Name of the spoke {}.'.format(verb),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddRegionResourceArg(
    parser, verb, resource_location_type=ResourceLocationType.REGION_AND_GLOBAL
):
  """Add a resource argument for a region.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    resource_location_type: ResourceLocationType, the type of locations
      supported by the resource.
  """

  location_arguments = GetResourceLocationArguments(resource_location_type)
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='region',
      concept_spec=GetRegionResourceSpec(location_arguments),
      required=True,
      flag_name_overrides={'location': ''},
      group_help='The region of the spokes {}.'.format(verb),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddPscGroup(parser):
  """Add a group which contains the PSC-related arguments to the given parser."""
  psc_group = parser.add_group(required=False, mutex=True)
  AddExportPscFlag(psc_group)
  psc_gapi_group = psc_group.add_group(required=False, mutex=False, hidden=True)
  AddExportPscPublishedServicesAndRegionalGoogleApisFlag(psc_gapi_group)
  AddExportPscGlobalGoogleApisFlag(psc_gapi_group)


def AddExportPscFlag(parser):
  """Add the --export-psc flag to the given parser."""
  parser.add_argument(
      '--export-psc',
      action=arg_parsers.StoreTrueFalseAction,
      required=False,
      help="""Whether Private Service Connect propagation is enabled for the hub.""",
  )


def AddExportPscPublishedServicesAndRegionalGoogleApisFlag(parser):
  """Add the --export-psc-published-services-and-regional-google-apis flag to the given parser."""
  parser.add_argument(
      '--export-psc-published-services-and-regional-google-apis',
      action=arg_parsers.StoreTrueFalseAction,
      required=False,
      hidden=True,
      help="""Whether propagation for Private Service Connect for published services and regional Google APIs is enabled for the hub.""",
  )


def AddExportPscGlobalGoogleApisFlag(parser):
  """Add the --export-psc-global-google-apis flag to the given parser."""
  parser.add_argument(
      '--export-psc-global-google-apis',
      action=arg_parsers.StoreTrueFalseAction,
      required=False,
      hidden=True,
      help="""Whether propagation for Private Service Connect for global Google APIs is enabled for the hub.""",
  )


def AddActivationKeyFlag(parser, help_text):
  """Adds the --activation-key flag to the given parser."""
  parser.add_argument('--activation-key', required=False, help=help_text)


def AddRemoteAccountIdFlag(parser, help_text):
  """Adds the --remote-account-id flag to the given parser."""
  parser.add_argument('--remote-account-id', required=False, help=help_text)


def AddProfileFlag(parser, help_text):
  """Adds the --remote_profile flag to the given parser."""
  parser.add_argument('--remote-profile', required=False, help=help_text)


def AddBandwidthFlag(parser, help_text):
  """Adds the --bandwidth flag to the given parser."""
  parser.add_argument('--bandwidth', required=True, help=help_text)


def AddAdvertisedRoutesFlag(parser, help_text, required=True):
  """Adds the --advertised-routes flag to the given parser."""
  parser.add_argument('--advertised-routes', required=required, help=help_text)


def AddEnableAdminFlag(parser, help_text):
  """Adds the --enable-admin flag to the given parser."""
  parser.add_argument(
      '--enable-admin',
      action=arg_parsers.StoreTrueFalseAction,
      required=False,
      help=help_text,
  )


def AddStackTypeFlag(parser, help_text):
  """Adds the --stack-type flag to the given parser."""
  parser.add_argument(
      '--stack-type',
      required=False,
      help=help_text,
      default='IPV4_ONLY',
  )


def AddTransportResourceArg(parser, desc):
  """Add a resource argument for a transport.

  Args:
    parser: the parser for the command.
    desc: the string to describe the resource, such as 'to create'.
  """

  location_arguments = GetResourceLocationArguments(
      ResourceLocationType.REGION_ONLY
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='transport',
      concept_spec=GetTransportResourceSpec(location_arguments),
      required=True,
      group_help='Name of the transport {}.'.format(desc),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddRemoteProfileResourceArg(parser, desc):
  """Add a resource argument for a remote transport profile."""
  location_arguments = GetResourceLocationArguments(
      ResourceLocationType.REGION_ONLY
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='remote_profile',
      concept_spec=GetRemoteProfileResourceSpec(location_arguments),
      required=True,
      group_help='Name of the remote transport profile {}.'.format(desc),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
