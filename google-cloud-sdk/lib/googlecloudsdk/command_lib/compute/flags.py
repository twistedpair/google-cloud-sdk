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

import functools
import operator
import enum

from googlecloudsdk.api_lib.compute.regions import service as regions_service
from googlecloudsdk.api_lib.compute.zones import service as zones_service
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.credentials import gce as c_gce


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


class UnderSpecifiedResourceError(exceptions.Error):
  """Raised when argument is required additional scope to be resolved."""

  def __init__(self, underspecified_names, flag_names):
    phrases = ('one of ', 'flags') if len(flag_names) > 1 else ('', 'flag')
    super(UnderSpecifiedResourceError, self).__init__(
        'Underspecified resource [{3}]. Specify {0}the [{1}] {2}.'
        .format(phrases[0],
                ', '.join(sorted(flag_names)),
                phrases[1],
                ', '.join(underspecified_names)))


class ScopeEnum(enum.Enum):
  ZONE = ('zone')
  REGION = ('region')
  GLOBAL = ('global')

  def __init__(self, flag_name):
    # Collection parameter name matches command line file in this case.
    self.param_name = flag_name
    self.flag_name = flag_name


class ResourceStub(object):
  """Interface used by scope listing to report scope names."""

  def __init__(self, name, deprecated=None):
    self.name = name
    self.deprecated = deprecated


def GetDefaultScopeLister(compute_client, project):
  """Constructs default zone/region lister."""
  # TODO(user): Zones can be extracted from regions.
  scope_func = {
      ScopeEnum.ZONE:
          functools.partial(zones_service.List, compute_client, project),
      ScopeEnum.REGION:
          functools.partial(regions_service.List, compute_client, project),
      ScopeEnum.GLOBAL: lambda: [ResourceStub(name='')]
  }
  def Lister(scopes, _):
    results = {}
    for scope in scopes:
      results[scope] = scope_func[scope]()
    return results
  return Lister


class ResourceArgScope(object):
  """Facilitates mapping of scope, flag and collection."""

  def __init__(self, scope, flag_prefix, collection):
    self.scope_enum = scope
    if flag_prefix:
      flag_prefix = flag_prefix.replace('-', '_')
      if scope is ScopeEnum.GLOBAL:
        self.flag_name = scope.flag_name + '_' + flag_prefix
      else:
        self.flag_name = flag_prefix + '_' + scope.flag_name
    else:
      self.flag_name = scope.flag_name
    self.flag = '--' + self.flag_name.replace('_', '-')
    self.collection = collection


class ResourceArgScopes(object):
  """Represents chosen set of scopes."""

  def __init__(self, flag_prefix):
    self.flag_prefix = flag_prefix
    self.scopes = {}

  def AddScope(self, scope, collection):
    self.scopes[scope] = ResourceArgScope(scope, self.flag_prefix, collection)

  def SpecifiedByArgs(self, args):
    """Given argparse args return selected scope and its value."""
    for resource_scope in self.scopes.itervalues():
      scope_value = getattr(args, resource_scope.flag_name, None)
      if scope_value is not None:
        return resource_scope, scope_value
    return None, None

  def GetImplicitScope(self, default_scope=None):
    """See if there is no ambiguity even if scope is not known from args."""
    if len(self.scopes) == 1:
      return next(self.scopes.itervalues())
    return default_scope

  def __iter__(self):
    return iter(self.scopes.itervalues())

  def __contains__(self, scope):
    return scope in self.scopes

  def __getitem__(self, scope):
    return self.scopes[scope]

  def __len__(self):
    return len(self.scopes)


class ResourceArgument(object):
  """Encapsulates concept of compute resource as command line argument.

  Basic Usage:
    class MyCommand(base.Command):
      _BACKEND_SERVICE_ARG = flags.ResourceArgument(
          resource_name='backend service',
          completion_resource_id='compute.backendService',
          regional_collection='compute.regionBackendServices',
          global_collection='compute.backendServices')
      _INSTANCE_GROUP_ARG = flags.ResourceArgument(
          resource_name='instance group',
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
            args, api_resource_registry, default_scope=flags.ScopeEnum.GLOBAL)
        instance_group_ref = _INSTANCE_GROUP_ARG.ResolveAsResource(
            args, api_resource_registry, default_scope=flags.ScopeEnum.ZONE)
        ...

    In the above example the following five arguments/flags will be defined:
      NAME - positional for backend service
      --region REGION to qualify backend service
      --global  to qualify backend service
      --instance-group INSTANCE_GROUP name for the instance group
      --instance-group-zone INSTANCE_GROUP_ZONE further qualifies instance group

    More generally this construct can simultaneously support global, regional
    and zonal qualifiers (or any combination of) for each resource.
  """

  # TODO(user): replace collection arguments with single map argument.
  def __init__(self, name=None,
               resource_name=None,
               completion_resource_id=None,
               plural=False, required=True, zonal_collection=None,
               regional_collection=None, global_collection=None,
               region_explanation=None, zone_explanation=None,
               short_help=None, detailed_help=None):

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
      region_explanation: str, long help that will be given for region flag,
                               empty by default.
      zone_explanation: str, long help that will be given for zone flag, empty
                             by default.
      short_help: str, help for the flag being added, if not provided help text
                       will be 'The name[s] of the ${resource_name}[s].'.
      detailed_help: str, detailed help for the flag being added, if not
                          provided there will be no detailed help for the flag.
    Raises:
      exceptions.Error: if there some inconsistency in arguments.
    """
    self.name_arg = name or 'name'
    self._short_help = short_help
    self._detailed_help = detailed_help

    if self.name_arg.startswith('--'):
      self.is_flag = True
      self.name = self.name_arg[2:].replace('-', '_')
      self.scopes = ResourceArgScopes(flag_prefix=self.name_arg[2:])

    else:  # positional
      self.scopes = ResourceArgScopes(flag_prefix=None)
      self.name = self.name_arg  # arg name is same as its spec.
    self.resource_name = resource_name
    self.completion_resource_id = completion_resource_id
    self.plural = plural
    self.required = required
    if not (zonal_collection or regional_collection or global_collection):
      raise exceptions.Error('Must specify at least one resource type zonal, '
                             'regional or global')
    if zonal_collection:
      self.scopes.AddScope(ScopeEnum.ZONE, collection=zonal_collection)
    if regional_collection:
      self.scopes.AddScope(ScopeEnum.REGION, collection=regional_collection)
    if global_collection:
      self.scopes.AddScope(ScopeEnum.GLOBAL, collection=global_collection)
    self._region_explanation = region_explanation or ''
    self._zone_explanation = zone_explanation or ''

  def AddArgument(self, parser):
    """Add this set of arguments to argparse parser."""

    params = dict(
        metavar=self.name.upper(),
        completion_resource=self.completion_resource_id,
    )

    if self._short_help:
      params['help'] = self._short_help
    else:
      params['help'] = 'The name{0} of the {1}{0}.'.format(
          's' if self.plural else '', self.resource_name)

    if self.name_arg.startswith('--'):
      params['required'] = self.required
      if self.plural:
        params['type'] = arg_parsers.ArgList(min_length=1)
    else:
      if self.required:
        if self.plural:
          params['nargs'] = '+'
      else:
        params['nargs'] = '*' if self.plural else '?'

    argument = parser.add_argument(self.name_arg, **params)

    if self._detailed_help:
      argument.detailed_help = self._detailed_help

    if len(self.scopes) > 1:
      scope = parser.add_mutually_exclusive_group()
    else:
      scope = parser

    if ScopeEnum.ZONE in self.scopes:
      AddZoneFlag(
          scope,
          flag_prefix=self.scopes.flag_prefix,
          resource_type=self.resource_name,
          operation_type='operate on',
          explanation=self._zone_explanation)

    if ScopeEnum.REGION in self.scopes:
      AddRegionFlag(
          scope,
          flag_prefix=self.scopes.flag_prefix,
          resource_type=self.resource_name,
          operation_type='operate on',
          explanation=self._region_explanation)

    if ScopeEnum.GLOBAL in self.scopes and len(self.scopes) > 1:
      scope.add_argument(
          self.scopes[ScopeEnum.GLOBAL].flag,
          action='store_true',
          default=None,
          help='If provided, it is assumed the {0} is global.'
          .format(self.resource_name))

  def ResolveAsResource(self, args,
                        api_resource_registry,
                        default_scope=ScopeEnum.GLOBAL,
                        scope_lister=None):
    """Resolve this resource against the arguments.

    Args:
      args: Namespace, argparse.Namespace.
      api_resource_registry: instance of core.resources.Registry.
      default_scope: ScopeEnum, ZONE, REGION, or GLOBAL, when resolving name
          and scope was not specified use this as default.
      scope_lister: func(scope, underspecified_names), a callback which returns
        list of items (with 'name' attribute) for given scope.
    Returns:
      Resource reference or list of references if plural.
    """
    if default_scope is not None:
      if default_scope not in self.scopes:
        raise exceptions.Error(
            'Unexpected value for default_scope {0}, expected None or {1}'
            .format(default_scope,
                    ' or '.join([s.scope_enum.name for s in self.scopes])))
      default_scope = self.scopes[default_scope]
    names = self._GetResourceNames(args)
    resource_scope, scope_value = self.scopes.SpecifiedByArgs(args)
    params = {}
    if scope_value is not None:
      # Complain if scope was specified without actual resource(s).
      if not self.required and not names:
        raise exceptions.Error('Can\'t specify --zone, --region or --global'
                               ' without specifying resource via {0}'
                               .format(self.name))
      params[resource_scope.scope_enum.param_name] = scope_value
    else:
      resource_scope = self.scopes.GetImplicitScope(default_scope)

    collection = resource_scope and resource_scope.collection

    # See if we can resolve names with so far deduced scope and its value.
    refs = []
    underspecified_names = []
    for name in names:
      try:
        # Make each element an array so that we can do in place updates.
        ref = [api_resource_registry.Parse(name, params=params,
                                           collection=collection,
                                           enforce_collection=False)]
      except (resources.UnknownCollectionException,
              resources.UnknownFieldException):
        if scope_value:
          raise
        ref = [name]
        underspecified_names.append(ref)
      refs.append(ref)

    # If we still have some resources which need to be resolve see if we can
    # prompt the user and try to resolve these again.
    if underspecified_names:
      resource_scope, scope_value = self._PromptForScope(
          [n[0] for n in underspecified_names], default_scope, scope_lister)
      for name in underspecified_names:
        name[0] = api_resource_registry.Parse(
            name[0],
            params={resource_scope.scope_enum.param_name: scope_value},
            collection=resource_scope.collection,
            enforce_collection=True)
    # Now unpack each element.
    refs = [ref[0] for ref in refs]

    # Make sure correct collection was given for each resource, for example
    # URLs have implicit collections.
    expected_collections = [scope.collection for scope in self.scopes]
    for ref in refs:
      if ref.Collection() not in expected_collections:
        raise resources.WrongResourceCollectionException(
            expected=','.join(expected_collections),
            got=ref.Collection(),
            path=ref.SelfLink())

    if self.plural:
      return refs
    if refs:
      return refs[0]
    return None

  def _GetResourceNames(self, args):
    """Return list of resource names specified by args."""
    if self.plural:
      return getattr(args, self.name)

    name_value = getattr(args, self.name)
    if name_value is not None:
      return [name_value]
    return []

  def _PromptForScope(self, underspecified_names, default_scope, scope_lister):
    """Prompt user to specify a scope.

    Args:
      underspecified_names: list(str), names which lack scope context.
      default_scope: ResourceArgScope, force this scope to be used.
      scope_lister: func(scope, underspecified_names), callback to provide
          possible values for given scope.
    Returns:
      chosen scope and scope value.
    Raises:
      UnderSpecifiedResourceError: if scope could not be determined.
    """
    if not console_io.CanPrompt():
      raise UnderSpecifiedResourceError(underspecified_names,
                                        [s.flag for s in self.scopes])
    implicit_scope = self.scopes.GetImplicitScope(default_scope)
    if implicit_scope:
      suggested_value = _GetSuggestedScopeValue(implicit_scope.scope_enum)
      if suggested_value is not None:
        if _PromptDidYouMeanScope(self.resource_name, underspecified_names,
                                  implicit_scope, suggested_value):
          return implicit_scope, suggested_value

    if not scope_lister:
      raise UnderSpecifiedResourceError(underspecified_names,
                                        [s.flag_name for s in self.scopes])
    scope_value_choices = scope_lister(
        # Sort to make it deterministic.
        sorted([s.scope_enum for s in self.scopes],
               key=operator.attrgetter('name')),
        underspecified_names)

    resource_scope_enum, scope_value = _PromptWithScopeChoices(
        self.resource_name, underspecified_names, scope_value_choices)
    return self.scopes[resource_scope_enum], scope_value


def _PromptDidYouMeanScope(resource_name, underspecified_names, scope,
                           suggested_resource):
  """Prompts "did you mean <scope>".  Returns str or None."""

  names = ['[{0}]'.format(name) for name in underspecified_names]
  message = 'Did you mean {0} [{1}] for {2}: [{3}]'.format(
      scope.scope_enum.flag_name, suggested_resource,
      resource_name, ','.join(names))

  if console_io.PromptContinue(prompt_string=message, default=True,
                               throw_if_unattended=True):
    return suggested_resource
  return None


def _PromptWithScopeChoices(resource_name, underspecified_names,
                            scope_value_choices):
  """Queries user to choose scope and its value."""
  # Print deprecation state for choices.
  choice_names = []
  choice_mapping = []
  for scope in sorted(scope_value_choices.keys(),
                      key=operator.attrgetter('flag_name')):
    for choice_resource in sorted(scope_value_choices[scope],
                                  key=operator.attrgetter('name')):
      deprecated = getattr(choice_resource, 'deprecated', None)
      if deprecated is not None:
        choice_name = '{0} ({1})'.format(
            choice_resource.name, deprecated.state)
      else:
        choice_name = choice_resource.name

      if len(scope_value_choices) > 1:
        if choice_name:
          choice_name = '{0}: {1}'.format(scope.flag_name, choice_name)
        else:
          choice_name = scope.flag_name

      choice_mapping.append((scope, choice_resource.name))
      choice_names.append(choice_name)

  title = ('For the following {0}:\n {1}\n'
           .format(resource_name,
                   '\n '.join('- [{0}]'.format(n)
                              for n in sorted(underspecified_names))))
  idx = console_io.PromptChoice(
      options=choice_names,
      message='{0}choose a {1}:'.format(
          title,
          ' or '.join(sorted([s.flag_name
                              for s in scope_value_choices.keys()]))))
  if idx is None:
    return None, None
  else:
    return choice_mapping[idx]


def _GetSuggestedScopeValue(scope):
  if scope == ScopeEnum.ZONE:
    return _GetGCEZone()
  if scope == ScopeEnum.REGION:
    return _GetGCERegion()
  return True


def _GetGCERegion():
  if properties.VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().Region()
  return None


def _GetGCEZone():
  if properties.VALUES.core.check_gce_metadata.GetBool():
    return c_gce.Metadata().Zone()
  return None
