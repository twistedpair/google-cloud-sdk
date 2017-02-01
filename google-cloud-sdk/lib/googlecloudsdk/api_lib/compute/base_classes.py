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

"""Base classes for abstracting away common logic."""

import abc
import collections
import copy
import cStringIO
import json
import textwrap

from apitools.base.protorpclite import messages
from apitools.base.py import encoding

import enum
from googlecloudsdk.api_lib.compute import client_adapter
from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.compute import managed_instance_groups_utils
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import property_selector
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import resource_specs
from googlecloudsdk.api_lib.compute import scope_prompter
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resolvers
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import edit
from googlecloudsdk.core.util import text
import yaml


class ComputeApiHolder(object):
  """Convenience class to hold lazy initialized client and resources."""

  def __init__(self, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      self._api_version = 'alpha'
    elif release_track == base.ReleaseTrack.BETA:
      self._api_version = 'beta'
    else:
      self._api_version = 'v1'
    self._client = None
    self._resources = None

  @property
  def client(self):
    """Specifies the compute client."""
    if self._client is None:
      self._client = client_adapter.ClientAdapter(self._api_version)
    return self._client

  @property
  def resources(self):
    """Specifies the resources parser for compute resources."""
    if self._resources is None:
      _SetResourceParamDefaults()
      self._resources = resources.REGISTRY.Clone()
      self._resources.RegisterApiByName('compute', self._api_version)
    return self._resources


class ComputeUserAccountsApiHolder(object):
  """Convenience class to hold lazy initialized client and resources."""

  def __init__(self, release_track):
    if release_track == base.ReleaseTrack.ALPHA:
      self._api_version = 'alpha'
    else:
      self._api_version = 'beta'
    self._client = None
    self._resources = None

  @property
  def client(self):
    """Specifies the compute client."""
    if self._client is None:
      self._client = core_apis.GetClientInstance(
          'clouduseraccounts', self._api_version)
    return self._client

  @property
  def resources(self):
    """Specifies the resources parser for compute resources."""
    if self._resources is None:
      resources.REGISTRY.SetParamDefault(
          api='clouduseraccounts',
          collection=None,
          param='project',
          resolver=resolvers.FromProperty(properties.VALUES.core.project))
      self._resources = resources.REGISTRY.Clone()
      self._resources.RegisterApiByName('clouduseraccounts', self._api_version)
    return self._resources


class BaseCommand(base.Command, scope_prompter.ScopePrompter):
  """Base class for all compute subcommands."""

  def __init__(self, *args, **kwargs):
    super(BaseCommand, self).__init__(*args, **kwargs)

    self.__resource_spec = None
    self._project = properties.VALUES.core.project.Get(required=True)
    self._compute_holder = ComputeApiHolder(self.ReleaseTrack())
    self._user_accounts_holder = ComputeUserAccountsApiHolder(
        self.ReleaseTrack())

  @property
  def _resource_spec(self):
    if not self.resource_type:
      return None
    if self.__resource_spec is None:
      # Constructing the spec can be potentially expensive (e.g.,
      # generating the set of valid fields from the protobuf message),
      self.__resource_spec = resource_specs.GetSpec(
          self.resource_type, self.messages, self.compute_client.api_version)
    return self.__resource_spec

  @property
  def transformations(self):
    if self._resource_spec:
      return self._resource_spec.transformations
    else:
      return None

  @property
  def resource_type(self):
    """Specifies the name of the collection that should be printed."""
    return None

  @property
  def http(self):
    """Specifies the http client to be used for requests."""
    return self.compute_client.apitools_client.http

  @property
  def project(self):
    """Specifies the user's project."""
    return self._project

  @property
  def batch_url(self):
    """Specifies the API batch URL."""
    return self.compute_client.batch_url

  @property
  def compute_client(self):
    """Specifies the compute client."""
    return self._compute_holder.client

  @property
  def compute(self):
    """Specifies the compute client."""
    return self.compute_client.apitools_client

  @property
  def resources(self):
    """Specifies the resources parser for compute resources."""
    return self._compute_holder.resources

  @property
  def clouduseraccounts(self):
    return self._user_accounts_holder.client

  @property
  def clouduseraccounts_resources(self):
    return self._user_accounts_holder.resources

  @property
  def messages(self):
    """Specifies the API message classes."""
    return self.compute_client.messages

  def Collection(self):
    """Returns the resource collection path."""
    return 'compute.' + self.resource_type if self.resource_type else None


class BaseLister(base.ListCommand, BaseCommand):
  """Base class for the list subcommands."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='*',
        default=[],
        completion_resource='compute.instances',
        help=('If provided, show details for the specified names and/or URIs '
              'of resources.'))

    regexp = parser.add_argument(
        '--regexp', '-r',
        help='A regular expression to filter the names of the results on.')
    regexp.detailed_help = """\
        A regular expression to filter the names of the results on. Any names
        that do not match the entire regular expression will be filtered out.
        """

  @property
  def allowed_filtering_types(self):
    """The list of resource types that can be provided to filtering."""
    return [self.resource_type]

  @abc.abstractmethod
  def GetResources(self, args, errors):
    """Returns a generator of JSON-serializable resource dicts."""

  def GetFilterExpr(self, args):
    """Returns a filter expression if --regexp is provided."""
    if args.regexp:
      return 'name eq {0}'.format(args.regexp)
    else:
      return None

  def PopulateResourceFilteringStructures(self, args):
    """Processes the positional arguments for later filtering."""
    allowed_collections = ['compute.{0}'.format(resource_type)
                           for resource_type in self.allowed_filtering_types]
    for name in args.names:
      try:
        ref = self.resources.Parse(name)

        if ref.Collection() not in allowed_collections:
          raise calliope_exceptions.ToolException(
              'Resource URI must be of type {0}. Received [{1}].'.format(
                  ' or '.join('[{0}]'.format(collection)
                              for collection in allowed_collections),
                  ref.Collection()))

        self.self_links.add(ref.SelfLink())
        self.resource_refs.append(ref)
        continue
      except resources.UserError:
        pass

      self.names.add(name)

  def FilterResults(self, args, items):
    """Filters the list results by name and URI."""
    for item in items:
      # If no positional arguments were given, do no filtering.
      if not args.names:
        yield item

      # At this point, we have to do filtering because there was at
      # least one positional argument.
      elif item.selfLink in self.self_links or item.name in self.names:
        yield item

  def ComputeDynamicProperties(self, args, items):
    """Computes dynamic properties, which are not returned by GCE API."""
    _ = args
    return items

  def Run(self, args):
    """Yields JSON-serializable dicts of resources or self links."""
    # Data structures used to perform client-side filtering of
    # resources by their names and/or URIs.
    self.self_links = set()
    self.names = set()
    self.resource_refs = []

    # The field selector should be constructed before any resources
    # are fetched, so if there are any syntactic errors with the
    # fields, we can fail fast.
    field_selector = property_selector.PropertySelector(
        properties=None,
        transformations=self.transformations)

    errors = []

    self.PopulateResourceFilteringStructures(args)
    items = self.FilterResults(args, self.GetResources(args, errors))
    items = lister.ProcessResults(
        resources=items,
        field_selector=field_selector)
    items = self.ComputeDynamicProperties(args, items)

    for item in items:
      yield item

    if errors:
      utils.RaiseToolException(errors)


class GlobalLister(BaseLister):
  """Base class for listing global resources."""

  def GetResources(self, args, errors):
    return lister.GetGlobalResources(
        service=self.service,
        project=self.project,
        filter_expr=self.GetFilterExpr(args),
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)


def GetGlobalListerHelp(resource):
  """Returns the detailed help dict for a global list command."""
  return {
      'brief': 'List Google Compute Engine ' + resource,
      'DESCRIPTION': """\
          *{{command}}* displays all Google Compute Engine {0} in a project.
          """.format(resource),
      'EXAMPLES': """\
          To list all {0} in a project in table form, run:

            $ {{command}}

          To list the URIs of all {0} in a project, run:

            $ {{command}} --uri
            """.format(resource)
  }


class RegionalLister(BaseLister):
  """Base class for listing regional resources."""

  @staticmethod
  def Args(parser):
    BaseLister.Args(parser)
    parser.add_argument(
        '--regions',
        metavar='REGION',
        help='If provided, only resources from the given regions are queried.',
        type=arg_parsers.ArgList(min_length=1),
        default=[])

  def GetResources(self, args, errors):
    region_names = [
        self.CreateGlobalReference(region, resource_type='regions').Name()
        for region in args.regions]

    return lister.GetRegionalResources(
        service=self.service,
        project=self.project,
        requested_regions=region_names,
        filter_expr=self.GetFilterExpr(args),
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)


def GetRegionalListerHelp(resource):
  """Returns the detailed help dict for a regional list command."""
  return {
      'brief': 'List Google Compute Engine ' + resource,
      'DESCRIPTION': """\
          *{{command}}* displays all Google Compute Engine {0} in a project.

          By default, {0} from all regions are listed. The results can be
          narrowed down by providing the ``--regions'' flag.
          """.format(resource),
      'EXAMPLES': """\
          To list all {0} in a project in table form, run:

            $ {{command}}

          To list the URIs of all {0} in a project, run:

            $ {{command}} --uri

          To list all {0} in the ``us-central1'' and ``europe-west1'' regions,
          run:

            $ {{command}} --regions us-central1 europe-west1
            """.format(resource)
  }


class ZonalLister(BaseLister):
  """Base class for listing zonal resources."""

  @staticmethod
  def Args(parser):
    BaseLister.Args(parser)
    parser.add_argument(
        '--zones',
        metavar='ZONE',
        help='If provided, only resources from the given zones are queried.',
        type=arg_parsers.ArgList(min_length=1),
        completion_resource='compute.zones',
        default=[])

  def GetResources(self, args, errors):
    zone_names = [
        self.CreateGlobalReference(zone, resource_type='zones').Name()
        for zone in args.zones]
    return lister.GetZonalResources(
        service=self.service,
        project=self.project,
        requested_zones=zone_names,
        filter_expr=self.GetFilterExpr(args),
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)


def GetZonalListerHelp(resource):
  """Returns the detailed help dict for a zonal list command."""
  return {
      'brief': 'List Google Compute Engine ' + resource,
      'DESCRIPTION': """\
          *{{command}}* displays all Google Compute Engine {0} in a project.

          By default, {0} from all zones are listed. The results can be narrowed
          down by providing the ``--zones'' flag.
          """.format(resource),
      'EXAMPLES': """\
          To list all {0} in a project in table form, run:

            $ {{command}}

          To list the URIs of all {0} in a project, run:

            $ {{command}} --uri

          To list all {0} in the ``us-central1-b'' and ``europe-west1-d'' zones,
          run:

            $ {{command}} --zones us-central1-b europe-west1-d
            """.format(resource)
  }


class ScopeType(enum.Enum):
  """Scope type of compute resource."""
  global_scope = 1
  regional_scope = 2
  zonal_scope = 3


class MultiScopeLister(BaseLister):
  """Base class for listing global and regional resources."""

  @staticmethod
  def AddScopeArgs(parser, scopes):
    BaseLister.Args(parser)

    scope = parser.add_mutually_exclusive_group()

    if ScopeType.zonal_scope in scopes:
      scope.add_argument(
          '--zones',
          metavar='ZONE',
          help=('If provided, only zonal resources are shown. '
                'If arguments are provided, only resources from the given '
                'zones are shown.'),
          type=arg_parsers.ArgList())
    if ScopeType.regional_scope in scopes:
      scope.add_argument(
          '--regions',
          metavar='REGION',
          help=('If provided, only regional resources are shown. '
                'If arguments are provided, only resources from the given '
                'regions are shown.'),
          type=arg_parsers.ArgList())
    if ScopeType.global_scope in scopes:
      scope.add_argument(
          '--global',
          action='store_true',
          help='If provided, only global resources are shown.',
          default=False)

  @abc.abstractproperty
  def global_service(self):
    """The service used to list global resources."""

  @abc.abstractproperty
  def regional_service(self):
    """The service used to list regional resources."""

  @abc.abstractproperty
  def zonal_service(self):
    """The service used to list regional resources."""

  @abc.abstractproperty
  def aggregation_service(self):
    """The service used to get aggregated list of resources."""

  def GetResources(self, args, errors):
    """Yields zonal, regional and/or global resources."""
    has_regions = hasattr(args, 'regions') and args.regions
    has_zones = hasattr(args, 'zones') and args.zones
    has_global = hasattr(args, 'global') and getattr(args, 'global')

    # This is true if the user provided no flags indicating scope
    no_scope_flags = not has_regions and not has_zones and not has_global

    requests = []
    filter_expr = self.GetFilterExpr(args)
    max_results = constants.MAX_RESULTS_PER_PAGE
    project = self.project

    # If --regions is present with no arguments OR no scope flags are present
    # then we have to do an aggregated list
    # pylint:disable=g-explicit-bool-comparison
    if no_scope_flags and self.aggregation_service:
      requests.append(
          (self.aggregation_service,
           'AggregatedList',
           self.aggregation_service.GetRequestType('AggregatedList')(
               filter=filter_expr,
               maxResults=max_results,
               project=project)))
    # Else if some regions were provided then only list within them
    elif has_regions:
      region_names = set(
          self.CreateGlobalReference(region, resource_type='regions').Name()
          for region in args.regions)
      for region_name in sorted(region_names):
        requests.append(
            (self.regional_service,
             'List',
             self.regional_service.GetRequestType('List')(
                 filter=filter_expr,
                 maxResults=max_results,
                 region=region_name,
                 project=project)))
    # Else if some regions were provided then only list within them
    elif has_zones:
      zone_names = set(
          self.CreateGlobalReference(zone, resource_type='zones').Name()
          for zone in args.zones)
      for zone_name in sorted(zone_names):
        requests.append(
            (self.zonal_service,
             'List',
             self.zonal_service.GetRequestType('List')(
                 filter=filter_expr,
                 maxResults=max_results,
                 zone=zone_name,
                 project=project)))
    else:
      # Either --global was specified or we do not have aggregation service.
      # Note that --global, --region and --zone are mutually exclusive.
      requests.append(
          (self.global_service,
           'List',
           self.global_service.GetRequestType('List')(
               filter=filter_expr,
               maxResults=max_results,
               project=project)))

    return request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)


def GetMultiScopeListerHelp(resource, scopes):
  """Returns the detailed help dict for a global and regional list command."""

  zone_example_text = """\

          To list all {0} in zones ``us-central1-b'' and ``europe-west1-d'',
          run:

            $ {{command}} --zones us-central1,europe-west1
  """
  region_example_text = """\

          To list all {0} in the ``us-central1'' and ``europe-west1'' regions,
          run:

            $ {{command}} --regions us-central1,europe-west1
  """
  global_example_text = """\

          To list all global {0} in a project, run:

            $ {{command}} --global
  """

  allowed_flags = []
  default_result = []
  if ScopeType.global_scope in scopes:
    allowed_flags.append("``--global''")
    default_result.append('global ' + resource)
  if ScopeType.regional_scope in scopes:
    allowed_flags.append("``--regions''")
    default_result.append(resource + ' from all regions')
  if ScopeType.zonal_scope in scopes:
    allowed_flags.append("``--zones''")
    default_result.append(resource + ' from all zones')

  allowed_flags_text = (
      ', '.join(allowed_flags[:-1]) + ' or ' + allowed_flags[-1])
  default_result_text = (
      ', '.join(default_result[:-1]) + ' and ' + default_result[-1])

  return {
      'brief': 'List Google Compute Engine ' + resource,
      'DESCRIPTION': """\
          *{{command}}* displays all Google Compute Engine {0} in a project.

          By default, {1} are listed. The results can be narrowed down by
          providing the {2} flag.
          """.format(resource, default_result_text, allowed_flags_text),
      'EXAMPLES': ("""\
          To list all {0} in a project in table form, run:

            $ {{command}}

          To list the URIs of all {0} in a project, run:

            $ {{command}} --uri
          """ + (global_example_text
                 if ScopeType.global_scope in scopes else '')
                   + (region_example_text
                      if ScopeType.regional_scope in scopes else '')
                   + (zone_example_text
                      if ScopeType.zonal_scope in scopes else ''))
                  .format(resource),
  }


class GlobalRegionalLister(MultiScopeLister):
  """Base class for listing global and regional resources."""
  SCOPES = [ScopeType.regional_scope, ScopeType.global_scope]

  @staticmethod
  def Args(parser):
    MultiScopeLister.AddScopeArgs(parser, GlobalRegionalLister.SCOPES)

  @property
  def aggregation_service(self):
    return self.regional_service

  @property
  def zonal_service(self):
    return None


def GetGlobalRegionalListerHelp(resource):
  return GetMultiScopeListerHelp(resource, GlobalRegionalLister.SCOPES)


class BaseDescriber(base.DescribeCommand, BaseCommand):
  """Base class for the describe subcommands."""

  @staticmethod
  def Args(parser, resource=None, list_command_path=None):
    BaseDescriber.AddArgs(parser, resource, list_command_path)

  @staticmethod
  def AddArgs(parser, resource=None, list_command_path=None):
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource=resource,
        list_command_path=list_command_path,
        help='The name of the resource to fetch.')

  @property
  def method(self):
    return 'Get'

  def ScopeRequest(self, ref, request):
    """Adds a zone or region to the request object if necessary."""

  @abc.abstractmethod
  def CreateReference(self, args):
    pass

  def SetNameField(self, ref, request):
    """Sets the field in the request that corresponds to the object name."""
    name_field = self.service.GetMethodConfig(self.method).ordered_params[-1]
    setattr(request, name_field, ref.Name())

  def ComputeDynamicProperties(self, args, items):
    """Computes dynamic properties, which are not returned by GCE API."""
    _ = args
    return items

  def Run(self, args):
    """Yields JSON-serializable dicts of resources."""
    ref = self.CreateReference(args)

    get_request_class = self.service.GetRequestType(self.method)

    request = get_request_class(project=self.project)
    self.SetNameField(ref, request)
    self.ScopeRequest(ref, request)

    get_request = (self.service, self.method, request)

    errors = []
    objects = request_helper.MakeRequests(
        requests=[get_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)

    resource_list = lister.ProcessResults(objects, field_selector=None)
    resource_list = list(self.ComputeDynamicProperties(args, resource_list))

    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')
    return resource_list[0]


class GlobalDescriber(BaseDescriber):
  """Base class for describing global resources."""

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)


class RegionalDescriber(BaseDescriber):
  """Base class for describing regional resources."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseDescriber.AddArgs(parser, resource, command)
    flags.AddRegionFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateRegionalReference(args.name, args.region)

  def ScopeRequest(self, ref, request):
    request.region = ref.region


class ZonalDescriber(BaseDescriber):
  """Base class for describing zonal resources."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseDescriber.AddArgs(parser, resource, command)
    flags.AddZoneFlag(
        parser,
        resource_type='resource',
        operation_type='fetch')

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone


class MultiScopeDescriber(BaseDescriber):
  """Base class for describing global or regional resources."""

  @staticmethod
  def AddScopeArgs(parser, resource_type, scope_types, command=None):
    resource = resource_type
    BaseDescriber.AddArgs(parser, 'compute.' + resource, command)

    scope = parser.add_mutually_exclusive_group()

    if ScopeType.zonal_scope in scope_types:
      scope.add_argument(
          '--zone',
          help='The zone of the resource to fetch.',
          completion_resource='compute.zones',
          action=actions.StoreProperty(properties.VALUES.compute.zone))
    if ScopeType.regional_scope in scope_types:
      scope.add_argument(
          '--region',
          help='The region of the resource to fetch.',
          completion_resource='compute.regions',
          action=actions.StoreProperty(properties.VALUES.compute.region))
    if ScopeType.global_scope in scope_types:
      scope.add_argument(
          '--global',
          action='store_true',
          help=('If provided, it is assumed that the requested resource is '
                'global.'))

  @abc.abstractproperty
  def global_service(self):
    """The service used to list global resources."""

  @abc.abstractproperty
  def regional_service(self):
    """The service used to list regional resources."""

  @abc.abstractproperty
  def zonal_service(self):
    """The service used to list zonal resources."""

  @abc.abstractproperty
  def global_resource_type(self):
    """The type of global resources."""

  @abc.abstractproperty
  def regional_resource_type(self):
    """The type of regional resources."""

  @abc.abstractproperty
  def zonal_resource_type(self):
    """The type of regional resources."""

  @property
  def service(self):
    return self._service

  def CreateReference(self, args, default=None):
    has_region = hasattr(args, 'region') and args.region
    has_zone = hasattr(args, 'zone') and args.zone
    has_global = hasattr(args, 'global') and getattr(args, 'global')

    only_zone_prompt = hasattr(args, 'zone') and not hasattr(args, 'region')
    only_region_prompt = hasattr(args, 'region') and not hasattr(args, 'zone')

    if not (has_region or has_zone or has_global):
      if default == ScopeType.global_scope:
        has_global = True
      elif default == ScopeType.regional_scope:
        has_region = True
      elif default == ScopeType.zonal_scope:
        has_zone = True

    ref = None
    try:
      params = {}
      if has_region:
        params['region'] = args.region
      if has_zone:
        params['zone'] = args.zone
      ref = self.resources.Parse(args.name, params=params)
    except resources.UnknownCollectionException:
      ref = None

    if ref is None:
      if has_global:
        ref = self.CreateGlobalReference(
            args.name, resource_type=self.global_resource_type)
      elif has_region or only_region_prompt:
        ref = self.CreateRegionalReference(
            args.name, args.region, resource_type=self.regional_resource_type)
      elif has_zone or only_zone_prompt:
        ref = self.CreateZonalReference(
            args.name, args.zone, resource_type=self.zonal_resource_type)
      else:
        ref = self.PromptForMultiScopedReferences(
            [args.name],
            scope_names=['zone', 'region'],
            scope_services=[self.compute.zones, self.compute.regions],
            resource_types=[
                self.zonal_resource_type, self.regional_resource_type],
            flag_names=['--zone', '--region'])[0]

    valid_collections = ['compute.{0}'.format(resource_type)
                         for resource_type in [self.zonal_resource_type,
                                               self.regional_resource_type,
                                               self.global_resource_type]
                         if resource_type is not None]

    if ref.Collection() not in valid_collections:
      raise calliope_exceptions.ToolException(
          'You must pass in a reference to a global or regional resource.')

    ref_resource_type = utils.CollectionToResourceType(ref.Collection())
    if ref_resource_type == self.global_resource_type:
      self._service = self.global_service
    elif ref_resource_type == self.regional_resource_type:
      self._service = self.regional_service
    else:
      self._service = self.zonal_service
    return ref

  def ScopeRequest(self, ref, request):
    if ref.Collection() == 'compute.{0}'.format(self.regional_resource_type):
      request.region = ref.region
    if ref.Collection() == 'compute.{0}'.format(self.zonal_resource_type):
      request.zone = ref.zone


def GetMultiScopeDescriberHelp(resource, scopes):
  """Returns the detailed help dict for a multiscope describe command.

  Args:
    resource: resource name, singular form with no preposition
    scopes: global/regional/zonal or mix of them

  Returns:
    Help for multi-scope describe command.
  """
  article = text.GetArticle(resource)
  zone_example_text = """\

          To get details about a zonal {0} in the ``us-central1-b'' zone, run:

            $ {{command}} --zone us-central1-b
  """
  region_example_text = """\

          To get details about a regional {0} in the ``us-central1'' regions,
          run:

            $ {{command}} --region us-central1
  """
  global_example_text = """\

          To get details about a global {0}, run:

            $ {{command}} --global
  """
  return {
      'brief': ('Display detailed information about {0} {1}'
                .format(article, resource)),
      'DESCRIPTION': """\
          *{{command}}* displays all data associated with {0} {1} in a project.
          """.format(article, resource),
      'EXAMPLES': ("""\
          """ + (global_example_text
                 if ScopeType.global_scope in scopes else '')
                   + (region_example_text
                      if ScopeType.regional_scope in scopes else '')
                   + (zone_example_text
                      if ScopeType.zonal_scope in scopes else ''))
                  .format(resource),
  }


class GlobalRegionalDescriber(MultiScopeDescriber):
  """Base class for describing global or regional resources."""
  SCOPES = [ScopeType.regional_scope, ScopeType.global_scope]

  @staticmethod
  def Args(parser, resource, command=None):
    MultiScopeDescriber.AddScopeArgs(parser, resource,
                                     GlobalRegionalDescriber.SCOPES, command)

  @property
  def zonal_service(self):
    return None

  @property
  def zonal_resource_type(self):
    return None


class BaseAsyncMutator(BaseCommand):
  """Base class for subcommands that mutate resources."""

  @abc.abstractproperty
  def service(self):
    """The service that can mutate resources."""

  @abc.abstractproperty
  def method(self):
    """The method name on the service as a string."""

  @abc.abstractmethod
  def CreateRequests(self, args):
    """Creates the requests that perform the mutation.

    It is okay for this method to make calls to the API as long as the
    calls originating from this method do not cause any mutations.

    Args:
      args: The command-line arguments.

    Returns:
      A list of requests. Request could be one of:
        * protobuf - protobuf will be sent to self.service and self.method
        * (method, protobuf) - protobuf will be sent to self.service and
            provided method
        * (service, method, protobuf) - protobuf will be sent to
            provided service and method
    """

  def ComputeDynamicProperties(self, args, items):
    """Computes dynamic properties, which are not returned by GCE API."""
    _ = args
    return items

  def MakeRequests(self, requests_protobufs, errors):
    """Send requests to the API.

    Args:
      requests_protobufs: a list of requests as from CreateRequests.
      errors: output variable. Errors from underlying
          request_helper.MakeRequests

    Returns:
      Resource list
    """

    requests = TranslateRequestsProtobufs(requests_protobufs, self)
    # We want to run through the generator that MakeRequests returns in order to
    # actually make the requests, since these requests mutate resources.
    resource_list = list(request_helper.MakeRequests(
        requests=requests,
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))

    return resource_list

  def Run(self, args):
    errors = []
    resource_list = self.MakeRequests(self.CreateRequests(args), errors)

    resource_list = lister.ProcessResults(
        resources=resource_list,
        field_selector=property_selector.PropertySelector(
            properties=None,
            transformations=self.transformations))

    resource_list = self.ComputeDynamicProperties(args, resource_list)

    if errors:
      utils.RaiseToolException(errors)

    return resource_list


def TranslateRequestsProtobufs(requests_protobufs, command):
  """Translates requests protobufs into requests."""
  requests = []
  for request in requests_protobufs:
    if not isinstance(request, tuple):
      requests.append((command.service, command.method, request))
    elif len(request) == 2:
      method, proto = request
      requests.append((command.service, method, proto))
    elif len(request) == 3:
      requests.append(request)
    else:
      raise ValueError('Got request tuple of wrong size')
  return requests


class NoOutputMutator(base.SilentCommand, BaseCommand):
  """Base class for mutating subcommands that don't display resources."""


class NoOutputAsyncMutator(base.SilentCommand, BaseAsyncMutator):
  """Base class for mutating subcommands that don't display resources."""


class InstanceGroupManagerDynamicProperiesMixin(object):
  """Mixin class to compute dynamic information for instance groups."""

  def ComputeDynamicProperties(self, args, items):
    """Add Autoscaler information if Autoscaler is defined for the item."""
    _ = args
    # Items are expected to be IGMs.
    items = list(items)
    for mig in managed_instance_groups_utils.AddAutoscalersToMigs(
        migs_iterator=self.ComputeInstanceGroupSize(items=items),
        project=self.project,
        compute=self.compute,
        http=self.http,
        batch_url=self.batch_url,
        fail_when_api_not_supported=False):
      if 'autoscaler' in mig and mig['autoscaler'] is not None:
        if (hasattr(mig['autoscaler'], 'status') and mig['autoscaler'].status ==
            self.messages.Autoscaler.StatusValueValuesEnum.ERROR):
          mig['autoscaled'] = 'yes (*)'
          self._had_errors = True
        else:
          mig['autoscaled'] = 'yes'
      else:
        mig['autoscaled'] = 'no'
      yield mig

  def ComputeInstanceGroupSize(self, items):
    """Add information about Instance Group size."""
    errors = []
    items = list(items)
    zone_names = set([path_simplifier.Name(mig['zone'])
                      for mig in items if 'zone' in mig])
    region_names = set([path_simplifier.Name(mig['region'])
                        for mig in items if 'region' in mig])
    if zone_names:
      zonal_instance_groups = lister.GetZonalResources(
          service=self.compute.instanceGroups,
          project=self.project,
          requested_zones=zone_names,
          filter_expr=None,
          http=self.http,
          batch_url=self.batch_url,
          errors=errors)
    else:
      zonal_instance_groups = []

    if region_names and hasattr(self.compute, 'regionInstanceGroups'):
      regional_instance_groups = lister.GetRegionalResources(
          service=self.compute.regionInstanceGroups,
          project=self.project,
          requested_regions=region_names,
          filter_expr=None,
          http=self.http,
          batch_url=self.batch_url,
          errors=errors)
    else:
      regional_instance_groups = []

    instance_groups = (
        list(zonal_instance_groups) + list(regional_instance_groups))
    instance_group_ref_to_size = dict([
        (path_simplifier.ScopedSuffix(ig.selfLink), ig.size)
        for ig in instance_groups
    ])

    if errors:
      utils.RaiseToolException(errors)

    for item in items:
      self_link = item['selfLink']
      gm_self_link = self_link.replace(
          '/instanceGroupManagers/', '/instanceGroups/')
      scoped_suffix = path_simplifier.ScopedSuffix(gm_self_link)
      if scoped_suffix in instance_group_ref_to_size:
        size = instance_group_ref_to_size[scoped_suffix]
      else:
        size = ''

      item['size'] = str(size)
      yield item


class BaseAsyncCreator(BaseAsyncMutator):
  """Base class for subcommands that create resources.

  This class is a base.Command with base.ListCommand formatting.
  """

  def Format(self, args):
    return self.ListFormat(args)


class BaseDeleter(BaseAsyncMutator):
  """Base class for deleting resources."""

  @staticmethod
  def AddArgs(parser, resource, command=None):
    parser.add_argument(
        'names',
        metavar='NAME',
        nargs='+',
        completion_resource=resource,
        list_command_path=command,
        help='The resources to delete.')

  @abc.abstractproperty
  def resource_type(self):
    """The name of the collection that we will delete from."""

  @abc.abstractproperty
  def reference_creator(self):
    """A function that can construct resource reference objects."""

  @abc.abstractproperty
  def scope_name(self):
    """The name of the scope of the resource references."""

  @property
  def method(self):
    return 'Delete'

  @property
  def custom_prompt(self):
    """Allows subclasses to override the delete confirmation message."""
    return None

  def ScopeRequest(self, args, request):
    """Adds a zone or region to the request object if necessary."""

  def CreateRequests(self, args):
    """Returns a list of delete request protobufs."""
    delete_request_class = self.service.GetRequestType(self.method)
    name_field = self.service.GetMethodConfig(self.method).ordered_params[-1]

    # pylint:disable=too-many-function-args
    refs = self.reference_creator(args.names, args)
    utils.PromptForDeletion(
        refs, self.scope_name, prompt_title=self.custom_prompt)

    requests = []
    for ref in refs:
      request = delete_request_class(project=self.project)
      setattr(request, name_field, ref.Name())
      self.ScopeRequest(ref, request)
      requests.append(request)
    return requests


class ZonalDeleter(BaseDeleter):
  """Base class for deleting zonal resources."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseDeleter.AddArgs(parser, resource, command)
    flags.AddZoneFlag(
        parser, resource_type='resources', operation_type='delete')

  @property
  def reference_creator(self):
    return (lambda names, args: self.CreateZonalReferences(names, args.zone))

  def ScopeRequest(self, ref, request):
    request.zone = ref.zone

  @property
  def scope_name(self):
    return 'zone'


class RegionalDeleter(BaseDeleter):
  """Base class for deleting regional resources."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseDeleter.AddArgs(parser, resource, command)
    flags.AddRegionFlag(
        parser, resource_type='resources', operation_type='delete')

  @property
  def reference_creator(self):
    return (
        lambda names, args: self.CreateRegionalReferences(names, args.region))

  def ScopeRequest(self, ref, request):
    request.region = ref.region

  @property
  def scope_name(self):
    return 'region'


class GlobalDeleter(BaseDeleter):
  """Base class for deleting global resources."""

  @staticmethod
  def Args(parser, resource=None, command=None):
    BaseDeleter.AddArgs(parser, resource, command)

  @property
  def reference_creator(self):
    return (lambda names, _: self.CreateGlobalReferences(names))

  @property
  def scope_name(self):
    return None


class ReadWriteCommand(BaseCommand):
  """Base class for read->update->write subcommands."""

  @abc.abstractproperty
  def service(self):
    pass

  # TODO(user): Make this an abstractproperty once all
  # ReadWriteCommands support URIs and prompting.
  def CreateReference(self, args):
    """Returns a resources.Resource object for the object being mutated."""

  @abc.abstractmethod
  def GetGetRequest(self, args):
    """Returns a request for fetching the resource."""

  @abc.abstractmethod
  def GetSetRequest(self, args, replacement, existing):
    """Returns a request for setting the resource."""

  @abc.abstractmethod
  def Modify(self, args, existing):
    """Returns a modified resource."""

  def Run(self, args):
    self.ref = self.CreateReference(args)
    get_request = self.GetGetRequest(args)

    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[get_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='There was a problem fetching the resource:')

    new_object = self.Modify(args, objects[0])

    # If existing object is equal to the proposed object or if
    # Modify() returns None, then there is no work to be done, so we
    # print the resource and return.
    if not new_object or objects[0] == new_object:
      for resource in lister.ProcessResults(
          resources=[objects[0]],
          field_selector=property_selector.PropertySelector(
              properties=None,
              transformations=self.transformations)):
        log.status.Print(
            'No change requested; skipping update for [{0}].'.format(
                resource[u'name']))
        yield resource
      return

    resource_list = request_helper.MakeRequests(
        requests=[self.GetSetRequest(args, new_object, objects[0])],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors)

    resource_list = lister.ProcessResults(
        resources=resource_list,
        field_selector=property_selector.PropertySelector(
            properties=None,
            transformations=self.transformations))
    for resource in resource_list:
      yield resource

    if errors:
      utils.RaiseToolException(
          errors,
          error_message='There was a problem modifying the resource:')

  def Format(self, unused_args):
    # The none format does not print but it consumes the resource.
    return 'none'


class BaseMetadataAdder(ReadWriteCommand):
  """Base class for adding or modifying metadata entries."""

  @staticmethod
  def Args(parser):
    metadata_utils.AddMetadataArgs(parser, required=True)

  def Modify(self, args, existing):
    new_object = copy.deepcopy(existing)
    existing_metadata = getattr(existing, self.metadata_field, None)
    setattr(
        new_object,
        self.metadata_field,
        metadata_utils.ConstructMetadataMessage(
            self.messages,
            metadata=args.metadata,
            metadata_from_file=args.metadata_from_file,
            existing_metadata=existing_metadata))

    if metadata_utils.MetadataEqual(
        existing_metadata,
        getattr(new_object, self.metadata_field, None)):
      return None
    else:
      return new_object

  def Run(self, args):
    if not args.metadata and not args.metadata_from_file:
      raise calliope_exceptions.ToolException(
          'At least one of [--metadata] or [--metadata-from-file] must be '
          'provided.')

    return super(BaseMetadataAdder, self).Run(args)


class BaseMetadataRemover(ReadWriteCommand):
  """Base class for removing metadata entries."""

  @staticmethod
  def Args(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--all',
        action='store_true',
        default=False,
        help='If provided, all metadata entries are removed.')
    group.add_argument(
        '--keys',
        type=arg_parsers.ArgList(min_length=1),
        metavar='KEY',
        help='The keys of the entries to remove.')

  def Modify(self, args, existing):
    new_object = copy.deepcopy(existing)
    existing_metadata = getattr(existing, self.metadata_field, None)
    setattr(new_object,
            self.metadata_field,
            metadata_utils.RemoveEntries(
                self.messages,
                existing_metadata=existing_metadata,
                keys=args.keys,
                remove_all=args.all))

    if metadata_utils.MetadataEqual(
        existing_metadata,
        getattr(new_object, self.metadata_field, None)):
      return None
    else:
      return new_object

  def Run(self, args):
    if not args.all and not args.keys:
      raise calliope_exceptions.ToolException(
          'One of [--all] or [--keys] must be provided.')

    return super(BaseMetadataRemover, self).Run(args)


class InstanceMetadataMutatorMixin(ReadWriteCommand):
  """Mixin for mutating instance metadata."""

  @staticmethod
  def Args(parser):
    flags.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='set metadata on')
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource='compute.instances',
        help='The name of the instance whose metadata should be modified.')

  @property
  def resource_type(self):
    return 'instances'

  @property
  def service(self):
    return self.compute.instances

  @property
  def metadata_field(self):
    return 'metadata'

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def GetGetRequest(self, args):
    return (self.service,
            'Get',
            self.messages.ComputeInstancesGetRequest(
                instance=self.ref.Name(),
                project=self.project,
                zone=self.ref.zone))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'SetMetadata',
            self.messages.ComputeInstancesSetMetadataRequest(
                instance=self.ref.Name(),
                metadata=replacement.metadata,
                project=self.project,
                zone=self.ref.zone))


class InstanceTagsMutatorMixin(ReadWriteCommand):
  """Mixin for mutating instance tags."""

  @staticmethod
  def Args(parser):
    flags.AddZoneFlag(
        parser,
        resource_type='instance',
        operation_type='set tags on')
    parser.add_argument(
        'name',
        metavar='NAME',
        completion_resource='compute.instances',
        help='The name of the instance whose tags should be modified.')

  @property
  def resource_type(self):
    return 'instances'

  @property
  def service(self):
    return self.compute.instances

  def CreateReference(self, args):
    return self.CreateZonalReference(args.name, args.zone)

  def GetGetRequest(self, args):
    return (self.service,
            'Get',
            self.messages.ComputeInstancesGetRequest(
                instance=self.ref.Name(),
                project=self.project,
                zone=self.ref.zone))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'SetTags',
            self.messages.ComputeInstancesSetTagsRequest(
                instance=self.ref.Name(),
                tags=replacement.tags,
                project=self.project,
                zone=self.ref.zone))


class ProjectMetadataMutatorMixin(ReadWriteCommand):
  """Mixin for mutating project-level metadata."""

  @property
  def service(self):
    return self.compute.projects

  @property
  def metadata_field(self):
    return 'commonInstanceMetadata'

  def GetGetRequest(self, args):
    return (self.service,
            'Get',
            self.messages.ComputeProjectsGetRequest(
                project=self.project))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'SetCommonInstanceMetadata',
            self.messages.ComputeProjectsSetCommonInstanceMetadataRequest(
                metadata=replacement.commonInstanceMetadata,
                project=self.project))


_HELP = textwrap.dedent("""\
    You can edit the resource below. Lines beginning with "#" are
    ignored.

    If you introduce a syntactic error, you will be given the
    opportunity to edit the file again. You can abort by closing this
    file without saving it.

    At the bottom of this file, you will find an example resource.

    Only fields that can be modified are shown. The original resource
    with all of its fields is reproduced in the comment section at the
    bottom of this document.
    """)


def _SerializeDict(value, fmt):
  """Serializes value to either JSON or YAML."""
  if fmt == 'json':
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        separators=(',', ': '))
  else:
    yaml.add_representer(
        collections.OrderedDict,
        yaml.dumper.SafeRepresenter.represent_dict,
        Dumper=yaml.dumper.SafeDumper)
    return yaml.safe_dump(
        value,
        indent=2,
        default_flow_style=False,
        width=70)


def _DeserializeValue(value, fmt):
  """Parses the given JSON or YAML value."""
  if fmt == 'json':
    return json.loads(value)
  else:
    return yaml.load(value)


def _WriteResourceInCommentBlock(serialized_resource, title, buf):
  """Outputs a comment block with the given serialized resource."""
  buf.write('# ')
  buf.write(title)
  buf.write('\n# ')
  buf.write('-' * len(title))
  buf.write('\n#\n')
  for line in serialized_resource.splitlines():
    buf.write('#')
    if line:
      buf.write('   ')
      buf.write(line)
      buf.write('\n')


class BaseEdit(BaseCommand):
  """Base class for modifying resources using $EDITOR."""

  DEFAULT_FORMAT = 'yaml'

  @abc.abstractmethod
  def CreateReference(self, args):
    """Returns a resources.Resource object for the object being mutated."""

  @abc.abstractproperty
  def reference_normalizers(self):
    """Defines how to normalize resource references."""

  @abc.abstractproperty
  def service(self):
    pass

  @abc.abstractmethod
  def GetGetRequest(self, args):
    """Returns a request for fetching the resource."""

  @abc.abstractmethod
  def GetSetRequest(self, args, replacement, existing):
    """Returns a request for setting the resource."""

  @abc.abstractproperty
  def example_resource(self):
    pass

  def ProcessEditedResource(self, file_contents, args):
    """Returns an updated resource that was edited by the user."""

    # It's very important that we replace the characters of comment
    # lines with spaces instead of removing the comment lines
    # entirely. JSON and YAML deserialization give error messages
    # containing line, column, and the character offset of where the
    # error occurred. If the deserialization fails; we want to make
    # sure those numbers map back to what the user actually had in
    # front of him or her otherwise the errors will not be very
    # useful.
    non_comment_lines = '\n'.join(
        ' ' * len(line) if line.startswith('#') else line
        for line in file_contents.splitlines())

    modified_record = _DeserializeValue(non_comment_lines,
                                        args.format or BaseEdit.DEFAULT_FORMAT)

    # Normalizes all of the fields that refer to other
    # resource. (i.e., translates short names to URIs)
    reference_normalizer = property_selector.PropertySelector(
        transformations=self.reference_normalizers)
    modified_record = reference_normalizer.Apply(modified_record)

    if self.modifiable_record == modified_record:
      new_object = None

    else:
      modified_record['name'] = self.original_record['name']
      fingerprint = self.original_record.get('fingerprint')
      if fingerprint:
        modified_record['fingerprint'] = fingerprint

      new_object = encoding.DictToMessage(
          modified_record, self._resource_spec.message_class)

    # If existing object is equal to the proposed object or if
    # there is no new object, then there is no work to be done, so we
    # return the original object.
    if not new_object or self.original_object == new_object:
      return [self.original_object]

    errors = []
    resource_list = list(request_helper.MakeRequests(
        requests=[self.GetSetRequest(args, new_object, self.original_object)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not update resource:')

    return resource_list

  def Run(self, args):
    self.ref = self.CreateReference(args)
    get_request = self.GetGetRequest(args)

    errors = []
    objects = list(request_helper.MakeRequests(
        requests=[get_request],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors))
    if errors:
      utils.RaiseToolException(
          errors,
          error_message='Could not fetch resource:')

    self.original_object = objects[0]
    self.original_record = encoding.MessageToDict(self.original_object)

    # Selects only the fields that can be modified.
    field_selector = property_selector.PropertySelector(
        properties=self._resource_spec.editables)
    self.modifiable_record = field_selector.Apply(self.original_record)

    buf = cStringIO.StringIO()
    for line in _HELP.splitlines():
      buf.write('#')
      if line:
        buf.write(' ')
      buf.write(line)
      buf.write('\n')

    buf.write('\n')
    buf.write(_SerializeDict(self.modifiable_record,
                             args.format or BaseEdit.DEFAULT_FORMAT))
    buf.write('\n')

    example = _SerializeDict(
        encoding.MessageToDict(self.example_resource),
        args.format or BaseEdit.DEFAULT_FORMAT)
    _WriteResourceInCommentBlock(example, 'Example resource:', buf)

    buf.write('#\n')

    original = _SerializeDict(self.original_record,
                              args.format or BaseEdit.DEFAULT_FORMAT)
    _WriteResourceInCommentBlock(original, 'Original resource:', buf)

    file_contents = buf.getvalue()
    while True:
      try:
        file_contents = edit.OnlineEdit(file_contents)
      except edit.NoSaveException:
        raise calliope_exceptions.ToolException('Edit aborted by user.')
      try:
        resource_list = self.ProcessEditedResource(file_contents, args)
        break
      except (ValueError, yaml.error.YAMLError,
              messages.ValidationError,
              calliope_exceptions.ToolException) as e:
        if isinstance(e, ValueError):
          message = e.message
        else:
          message = str(e)

        if isinstance(e, calliope_exceptions.ToolException):
          problem_type = 'applying'
        else:
          problem_type = 'parsing'

        message = ('There was a problem {0} your changes: {1}'
                   .format(problem_type, message))
        if not console_io.PromptContinue(
            message=message,
            prompt_string='Would you like to edit the resource again?'):
          raise calliope_exceptions.ToolException('Edit aborted by user.')

    resource_list = lister.ProcessResults(
        resources=resource_list,
        field_selector=property_selector.PropertySelector(
            properties=None,
            transformations=self.transformations))
    for resource in resource_list:
      yield resource


def _SetResourceParamDefaults():
  """Sets resource parsing default parameters to point to properties."""
  core_values = properties.VALUES.core
  compute_values = properties.VALUES.compute
  for api, param, prop in (
      ('compute', 'project', core_values.project),
      ('resourceviews', 'projectName', core_values.project),
      ('compute', 'zone', compute_values.zone),
      ('resourceviews', 'zone', compute_values.zone),
      ('compute', 'region', compute_values.region),
      ('resourceviews', 'region', compute_values.region)):
    resources.REGISTRY.SetParamDefault(
        api=api,
        collection=None,
        param=param,
        resolver=resolvers.FromProperty(prop))
