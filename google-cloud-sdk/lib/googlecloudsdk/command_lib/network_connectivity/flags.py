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

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.network_connectivity import util
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
      help="""IP address range(s) to hide from subnets in VPC networks that are peered
        through Network Connectivity Center peering.""")


def AddAsyncFlag(parser):
  """Add the --async argument to the given parser."""
  base.ASYNC_FLAG.AddToParser(parser)


def AddHubFlag(parser):
  """Adds the --hub argument to the given parser."""
  # TODO(b/233653552) Parse this with a resouce argument.
  parser.add_argument(
      '--hub',
      required=True,
      help='Hub that the spoke will attach to. The hub must already exist.')


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


def AddGlobalFlag(parser, hidden):
  """Add the --global argument to the given parser."""
  parser.add_argument(
      GLOBAL_ARGUMENT,
      help='Indicates that the spoke is global.',
      hidden=hidden,
      action=util.StoreGlobalAction)


def AddRegionFlag(parser, supports_region_wildcard, hidden):
  """Add the --region argument to the given parser."""
  region_help_text = """ \
        A Google Cloud region. To see the names of regions, see [Viewing a list of available regions](https://cloud.google.com/compute/docs/regions-zones/viewing-regions-zones#viewing_a_list_of_available_regions)."""  # pylint: disable=line-too-long
  if supports_region_wildcard:
    region_help_text += ' Use ``-`` to specify all regions.'
  parser.add_argument(
      REGION_ARGUMENT,
      hidden=hidden,
      help=region_help_text)


def AddRegionGroup(parser,
                   supports_region_wildcard=False,
                   hide_global_arg=False,
                   hide_region_arg=False):
  """Add a group which contains the global and region arguments to the given parser."""
  region_group = parser.add_group(required=False, mutex=True)
  AddGlobalFlag(region_group, hide_global_arg)
  AddRegionFlag(region_group, supports_region_wildcard, hide_region_arg)


def SpokeAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='spoke', help_text='The spoke Id.')


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
          location_arguments, region_resource_command=True),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetResourceLocationArguments(vpc_spoke_only_command):
  if not vpc_spoke_only_command:
    return [GLOBAL_ARGUMENT, REGION_ARGUMENT]
  else:
    return [GLOBAL_ARGUMENT]


def AddSpokeResourceArg(parser, verb, vpc_spoke_only_command=False):
  """Add a resource argument for a spoke.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    vpc_spoke_only_command: bool, if the spoke resource arg is for a VPC
      spoke-specific command.
  """
  location_arguments = GetResourceLocationArguments(vpc_spoke_only_command)
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='spoke',
      concept_spec=GetSpokeResourceSpec(location_arguments),
      required=True,
      flag_name_overrides={'location': ''},
      group_help='Name of the spoke {}.'.format(verb),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def AddRegionResourceArg(parser, verb, vpc_spoke_only_command=False):
  """Add a resource argument for a region.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    vpc_spoke_only_command: bool, if the spoke resource arg is for a VPC
      spoke-specific command.
  """

  location_arguments = GetResourceLocationArguments(vpc_spoke_only_command)
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name='region',
      concept_spec=GetRegionResourceSpec(location_arguments),
      required=True,
      flag_name_overrides={'location': ''},
      group_help='The region of the spokes {}.'.format(verb),
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)
