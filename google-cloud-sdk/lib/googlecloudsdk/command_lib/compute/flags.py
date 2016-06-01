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

"""Flags and helpers for the compute related commands."""

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


ZONE_PROPERTY_EXPLANATION = """\
If not specified, you will be prompted to select a zone.

To avoid prompting when this flag is omitted, you can set the
``compute/zone'' property:

  $ gcloud config set compute/zone ZONE

A list of zones can be fetched by running:

  $ gcloud compute zones list

To unset the property, run:

  $ gcloud config unset compute/zone

Alternatively, the zone can be stored in the environment variable
``CLOUDSDK_COMPUTE_ZONE''.
"""

ZONE_PROPERTY_EXPLANATION_NO_DEFAULT = """\
If not specified, you will be prompted to select a zone.

A list of zones can be fetched by running:

  $ gcloud compute zones list
"""

REGION_PROPERTY_EXPLANATION = """\
If not specified, you will be prompted to select a region.

To avoid prompting when this flag is omitted, you can set the
``compute/region'' property:

  $ gcloud config set compute/region REGION

A list of regions can be fetched by running:

  $ gcloud compute regions list

To unset the property, run:

  $ gcloud config unset compute/region

Alternatively, the region can be stored in the environment
variable ``CLOUDSDK_COMPUTE_REGION''.
"""

REGION_PROPERTY_EXPLANATION_NO_DEFAULT = """\
If not specified, you will be prompted to select a region.

A list of regions can be fetched by running:

  $ gcloud compute regions list
"""


def AddZoneFlag(parser, resource_type, operation_type, flag_prefix=None,
                explanation=ZONE_PROPERTY_EXPLANATION):
  """Adds a --zone flag to the given parser.

  Args:
    parser: argparse parser.
    resource_type: str, human readable name for the resource type this flag is
                   qualifying, for example "instance group".
    operation_type: str, human readable name for the operation, for example
                    "update" or "delete".
    flag_prefix: str, flag will be named --{flag_prefix}-zone.
    explanation: str, detailed explanation of the flag.
  """
  short_help = 'The zone of the {0} to {1}.'.format(
      resource_type, operation_type)
  flag_name = 'zone'
  if flag_prefix is not None:
    flag_name = flag_prefix + '-' + flag_name
  zone = parser.add_argument(
      '--' + flag_name,
      help=short_help,
      completion_resource='compute.zones',
      action=actions.StoreProperty(properties.VALUES.compute.zone))
  zone.detailed_help = '{0} {1}'.format(
      short_help, explanation)


def AddRegionFlag(parser, resource_type, operation_type,
                  flag_prefix=None,
                  explanation=REGION_PROPERTY_EXPLANATION):
  """Adds a --region flag to the given parser.

  Args:
    parser: argparse parser.
    resource_type: str, human readable name for the resource type this flag is
                   qualifying, for example "instance group".
    operation_type: str, human readable name for the operation, for example
                    "update" or "delete".
    flag_prefix: str, flag will be named --{flag_prefix}-region.
    explanation: str, detailed explanation of the flag.
  """
  short_help = 'The region of the {0} to {1}.'.format(
      resource_type, operation_type)
  flag_name = 'region'
  if flag_prefix is not None:
    flag_name = flag_prefix + '-' + flag_name
  region = parser.add_argument(
      '--' + flag_name,
      help=short_help,
      completion_resource='compute.regions',
      action=actions.StoreProperty(properties.VALUES.compute.region))
  region.detailed_help = '{0} {1}'.format(
      short_help, explanation)


class ResourceArgument(object):
  """Encapsulates concept of compute resource as command line argument.

  Basic Usage:
    class MyCommand(base.Command):
      _BACKEND_SERVICE_ARG = flags.ResourceArgument(
          resource_name='backend service',
          completion_resource_id='compute.backendService',
          regional_collection='compute.regionalBackendServices',
          global_collection='compute.backendServices')
      _INSTANCE_GROUP_ARG = flags.ResourceArgument(
          resource_name='instance_group',
          completion_resource_id='compute.InstanceGroup',
          zonal_collection='compute.instanceGroups',)

      @staticmethod
      def Args(parser):
        MyCommand._BACKEND_SERVICE_ARG.AddArgument(parser)
        MyCommand._INSTANCE_GROUP_ARG.AddArgument(parser)

      def Run(args):
        api_resource_registry = resources.REGISTRY.CloneAndSwitch(
            api_tools_client)
        backend_service_ref = _BACKEND_SERVICE_ARG.ResolveAsResource(
            args, api_resource_registry, default_scope='global')
        instance_group_ref = _INSTANCE_GROUP_ARG.ResolveAsResource(
            args, api_resource_registry, default_scope='global')
        ...

    In the above example the following five arguments/flags will be defined:
      NAME - postional for backend service
      --region REGION to qualify backend service
      --global  to qualify backend service
      --instance-group INSTANCE_GROUP name for the instance group
      --instance-group-zone INSTANCE_GROUP_ZONE further qualifies instance group

    More generally this construct can simultaniously support global, regional
    and zonal qualifiers (or any combination of) for each resource.
  """

  def __init__(self, name=None,
               resource_name=None,
               completion_resource_id=None,
               plural=False, required=True, zonal_collection=None,
               regional_collection=None, global_collection=None):

    """Constructor.

    Args:
      name: str, argument name.
      resource_name: str, human readable name for resources eg "instance group".
      completion_resource_id: str, id of registered resource.
      plural: bool, whether to accept multiple values.
      required: bool, whether this argument is required.
      zonal_collection: str, include zone flag and use this collection
                             to resolve it.
      regional_collection: str, include region flag and use this collection
                                to resolve it.
      global_collection: str, if also zonal and/or regional adds global flag
                              and uses this collection to resolve as
                              global resource.
    Raises:
      exceptions.Error: if there some inconsistency in arguments.
    """
    self.name_arg = name or 'name'
    self.zone_flag = 'zone'
    self.region_flag = 'region'
    self.global_flag = 'global'

    if self.name_arg.startswith('--'):
      self.is_flag = True
      self.name = self.name_arg[2:].replace('-', '_')
      self.zone_flag = self.name + '_' + self.zone_flag
      self.region_flag = self.name + '_' + self.region_flag
      self.global_flag = self.global_flag + '_' + self.name
    else:  # positional
      self.name = self.name_arg  # arg name is same as its spec.
    self.resource_name = resource_name
    self.completion_resource_id = completion_resource_id
    self.plural = plural
    self.required = required
    if not (zonal_collection or regional_collection or global_collection):
      raise exceptions.Error('Must specify at least one resource type zonal, '
                             'regional or global')
    self.zonal_collection = zonal_collection
    self.regional_collection = regional_collection
    self.global_collection = global_collection

  def AddArgument(self, parser):
    """Add this set of arguments to argparse parser."""

    params = dict(
        metavar=self.name.upper(),
        completion_resource=self.completion_resource_id,
        help='The name{0} of the {1}{0}.'
        .format('s' if self.plural else '', self.resource_name)
    )

    if self.name_arg.startswith('--'):
      prefix = self.name_arg[2:]
      params['required'] = self.required
      if self.plural:
        params['type'] = arg_parsers.ArgList(min_length=1)
    else:
      prefix = None
      if self.required:
        if self.plural:
          params['nargs'] = '+'
      else:
        params['nargs'] = '*' if self.plural else '?'

    parser.add_argument(self.name_arg, **params)

    num_scopes = (bool(self.global_collection) + bool(self.regional_collection)
                  + bool(self.zonal_collection))
    if num_scopes > 1:
      scope = parser.add_mutually_exclusive_group()
    else:
      scope = parser

    if self.zonal_collection:
      AddZoneFlag(
          scope,
          flag_prefix=prefix,
          resource_type=self.resource_name,
          operation_type='operate on')

    if self.regional_collection:
      AddRegionFlag(
          scope,
          flag_prefix=prefix,
          resource_type=self.resource_name,
          operation_type='operate on')

    # Only add global flag if there can be other scopes.
    if self.global_collection and (self.regional_collection
                                   or self.zonal_collection):
      scope.add_argument(
          '--' + self.global_flag.replace('_', '-'),
          action='store_true',
          help='If provided, it is assumed the {0} is global.'
          .format(self.resource_name))

  # TODO(b/28909484): add scope prompting.
  def ResolveAsResource(self, args,
                        api_resource_registry,
                        default_scope='global'):
    """Resolve this resource against the arguments.

    Args:
      args: Namespace, argparse.Namespace.
      api_resource_registry: instance of core.resources.Registry.
      default_scope: str, 'zone', 'region', 'global', when resolving name
          and scope was not specified use this as default.
    Returns:
      Resource reference or list of references if plural.
    """
    if default_scope not in ['zone', 'region', 'global', None]:
      raise exceptions.Error('Unexpected value for default_scope')
    scope = self._DetermineScope(args, default_scope)
    scope_value = self._GetScopeValue(args, scope)
    names = self._GetResourceNames(args)

    # Complain if scope was specified without actual resource(s).
    if not self.required and not names and scope_value is not None:
      raise exceptions.Error('Can\'t specify --zone, --region or --global'
                             ' without specifying resource via {0}'
                             .format(self.name))

    params = {}
    if scope is 'zone':
      params['zone'] = scope_value
      collection = self.zonal_collection
    elif scope is 'region':
      params['region'] = scope_value
      collection = self.regional_collection
    else:
      collection = self.global_collection

    refs = []
    for name in names:
      ref = api_resource_registry.Parse(name, params=params,
                                        collection=collection)
      if ref:
        refs.append(ref)

    if self.plural:
      return refs
    if refs:
      return refs[0]
    return None

  def _DetermineScope(self, args, default_scope):
    """Determine from arguments what scope was scpecified.

    Args:
      args: Namespace, argparse.Namespace.
      default_scope: str, 'zone', 'region' or 'global'.
    Returns:
      str: 'zone', 'region' or 'global' which is derived from args,
        default_scope, or if this object supports only single scope pick that.
    """
    # See if scope argument was given
    if getattr(args, self.zone_flag, None):
      return 'zone'
    if getattr(args, self.region_flag, None):
      return 'region'
    if getattr(args, self.global_flag, None):
      return 'global'

    # If there was no scope argument try to deduce one.
    if (default_scope == 'global' and not self.global_collection or
        default_scope == 'region' and not self.regional_collection or
        default_scope == 'zone' and not self.zonal_collection):
      raise exceptions.Error('Can\'t specify default scope "{0}" without '
                             'matching collection'.format(default_scope))
    if default_scope:
      return default_scope

    if (bool(self.global_collection) + bool(self.regional_collection) +
        bool(self.zonal_collection) != 1):
      raise exceptions.Error('default_scope was not provided, and one '
                             'cannot be deremined.')

    if self.zonal_collection:
      return 'zone'
    if self.regional_collection:
      return 'region'

    return 'global'

  def _GetScopeValue(self, args, scope):
    """Get value specified in args for given scope."""
    # TODO(b/28909484): prompt user if we cant get scope_value.
    arg_value = None
    if scope is 'zone':
      arg_value = getattr(args, self.zone_flag, None)
      if arg_value is None:
        raise calliope_exceptions.RequiredArgumentException(
            '--' + self.zone_flag.replace('_', '-'),
            'needed for zonal resource')

    elif scope is 'region':
      arg_value = getattr(args, self.region_flag, None)
      if arg_value is None:
        raise calliope_exceptions.RequiredArgumentException(
            '--' + self.region_flag.replace('_', '-'),
            'needed for regional resource')
    elif scope is 'global' and hasattr(args, self.global_flag):
      arg_value = getattr(args, self.global_flag)
      if arg_value is None:
        raise calliope_exceptions.RequiredArgumentException(
            '--' + self.global_flag.replace('_', '-'),
            'needed for global resource')
    # If none of the above cases matched (like scope==global but no global flag)
    # return None. This is important as later we want to correlate scope flag
    # with name argument, and fail if scope is specified but name is not.
    return arg_value

  def _GetResourceNames(self, args):
    """Return list of resource names specified by args."""
    if self.plural:
      return getattr(args, self.name)

    name_value = getattr(args, self.name)
    if name_value is not None:
      return [name_value]
    return []
