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
"""Flags and helpers for the compute instance groups commands."""

from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags


def MakeZonalInstanceGroupArg(plural=False):
  return flags.ResourceArgument(
      resource_name='instance group',
      completion_resource_id='compute.instanceGroups',
      plural=plural,
      zonal_collection='compute.instanceGroups',
      zone_explanation=flags.ZONE_PROPERTY_EXPLANATION)

MULTISCOPE_INSTANCE_GROUP_ARG = flags.ResourceArgument(
    resource_name='instance group',
    completion_resource_id='compute.instanceGroups',
    zonal_collection='compute.instanceGroups',
    regional_collection='compute.regionInstanceGroups',
    zone_explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT,
    region_explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)

ZONAL_INSTANCE_GROUP_MANAGER_ARG = flags.ResourceArgument(
    resource_name='managed instance group',
    completion_resource_id='compute.instanceGroupManagers',
    zonal_collection='compute.instanceGroupManagers',
    zone_explanation=flags.ZONE_PROPERTY_EXPLANATION)

ZONAL_INSTANCE_GROUP_MANAGERS_ARG = flags.ResourceArgument(
    resource_name='managed instance group',
    plural=True,
    name='names',
    completion_resource_id='compute.instanceGroupManagers',
    zonal_collection='compute.instanceGroupManagers',
    zone_explanation=flags.ZONE_PROPERTY_EXPLANATION)

MULTISCOPE_INSTANCE_GROUP_MANAGER_ARG = flags.ResourceArgument(
    resource_name='managed instance group',
    completion_resource_id='compute.regionInstanceGroupManagers',
    zonal_collection='compute.instanceGroupManagers',
    regional_collection='compute.regionInstanceGroupManagers',
    zone_explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT,
    region_explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)

MULTISCOPE_INSTANCE_GROUP_MANAGERS_ARG = flags.ResourceArgument(
    resource_name='managed instance group',
    plural=True,
    name='names',
    completion_resource_id='compute.regionInstanceGroupManagers',
    zonal_collection='compute.instanceGroupManagers',
    regional_collection='compute.regionInstanceGroupManagers',
    zone_explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT,
    region_explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)


def AddGroupArg(parser):
  parser.add_argument(
      'group',
      help='The name of the instance group.')


def AddNamedPortsArgs(parser):
  """Adds flags for handling named ports."""
  parser.add_argument(
      '--named-ports',
      required=True,
      type=arg_parsers.ArgList(),
      metavar='NAME:PORT',
      help="""\
          The comma-separated list of key:value pairs representing
          the service name and the port that it is running on.

          To clear the list of named ports pass empty list as flag value.
          For example:

            $ {command} example-instance-group --named-ports ""
          """)


def AddScopeArgs(parser, multizonal):
  """Adds flags for group scope."""
  if multizonal:
    scope_parser = parser.add_mutually_exclusive_group()
    flags.AddRegionFlag(
        scope_parser,
        resource_type='instance group',
        operation_type='set named ports for',
        explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)
    flags.AddZoneFlag(
        scope_parser,
        resource_type='instance group',
        operation_type='set named ports for',
        explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT)
  else:
    flags.AddZoneFlag(
        parser,
        resource_type='instance group',
        operation_type='set named ports for')


def AddZonesFlag(parser):
  """Add flags for choosing zones for regional managed instance group."""
  parser.add_argument(
      '--zones',
      metavar='ZONE',
      help="""\
          If this flag is specified a regional managed instance group will be
          created. The managed instance group will be in the same region as
          specified zones and will spread instances in it between specified
          zones.

          All zones must belong to the same region. You may specify --region
          flag but it must be the region to which zones belong. This flag is
          mutually exclusive with --zone flag.""",
      hidden=True,
      type=arg_parsers.ArgList(min_length=1),
      completion_resource='compute.zones',
      default=[])


# TODO(b/62898965): Use ResourcceResolver instead of resources.Parse().
def ValidateManagedInstanceGroupScopeArgs(args, resources):
  """Validate arguments specifying scope of the managed instance group."""
  ignored_required_params = {'project': 'fake'}
  if args.zones and args.zone:
    raise exceptions.ConflictingArgumentsException('--zone', '--zones')
  zone_names = []
  for zone in args.zones:
    zone_ref = resources.Parse(
        zone, collection='compute.zones', params=ignored_required_params)
    zone_names.append(zone_ref.Name())

  zone_regions = set([utils.ZoneNameToRegionName(z) for z in zone_names])
  if len(zone_regions) > 1:
    raise exceptions.InvalidArgumentException(
        '--zones', 'All zones must be in the same region.')
  elif len(zone_regions) == 1 and args.region:
    zone_region = zone_regions.pop()
    region_ref = resources.Parse(args.region, collection='compute.regions',
                                 params=ignored_required_params)
    region = region_ref.Name()
    if zone_region != region:
      raise exceptions.InvalidArgumentException(
          '--zones', 'Specified zones not in specified region.')
