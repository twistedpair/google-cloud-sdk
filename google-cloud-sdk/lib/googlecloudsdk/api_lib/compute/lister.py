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
"""Facilities for getting a list of Cloud resources."""

import itertools

from googlecloudsdk.api_lib.compute import constants
from googlecloudsdk.api_lib.compute import filter_rewrite
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import completers
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_expr_rewrite
from googlecloudsdk.core.resource import resource_projector


def _ConvertProtobufsToDicts(resources):
  for resource in resources:
    if resource is None:
      continue

    yield resource_projector.MakeSerializable(resource)


def ProcessResults(resources, field_selector, sort_key_fn=None,
                   reverse_sort=False, limit=None):
  """Process the results from the list query.

  Args:
    resources: The list of returned resources.
    field_selector: Select the primary key for sorting.
    sort_key_fn: Sort the key using this comparison function.
    reverse_sort: Sort the resources in reverse order.
    limit: Limit the number of resourses returned.
  Yields:
    The resource.
  """
  resources = _ConvertProtobufsToDicts(resources)
  if sort_key_fn:
    resources = sorted(resources, key=sort_key_fn, reverse=reverse_sort)

  if limit > 0:
    resources = itertools.islice(resources, limit)
  for resource in resources:
    if field_selector:
      yield field_selector.Apply(resource)
    else:
      yield resource


def FormatListRequests(service, project, scopes, scope_name,
                       filter_expr):
  """Helper for generating list requests."""
  requests = []

  if scopes:
    for scope in scopes:
      request = service.GetRequestType('List')(
          filter=filter_expr,
          project=project,
          maxResults=constants.MAX_RESULTS_PER_PAGE)
      setattr(request, scope_name, scope)
      requests.append((service, 'List', request))

  elif not scope_name:
    requests.append((
        service,
        'List',
        service.GetRequestType('List')(
            filter=filter_expr,
            project=project,
            maxResults=constants.MAX_RESULTS_PER_PAGE)))

  else:
    requests.append((
        service,
        'AggregatedList',
        service.GetRequestType('AggregatedList')(
            filter=filter_expr,
            project=project,
            maxResults=constants.MAX_RESULTS_PER_PAGE)))

  return requests


def _GetResources(service, project, scopes, scope_name,
                  filter_expr, http, batch_url, errors, make_requests):
  """Helper for the Get{Zonal,Regional,Global}Resources functions."""
  requests = FormatListRequests(service, project, scopes, scope_name,
                                filter_expr)

  return make_requests(
      requests=requests,
      http=http,
      batch_url=batch_url,
      errors=errors)


def GetZonalResources(service, project, requested_zones,
                      filter_expr, http, batch_url, errors):
  """Lists resources that are scoped by zone.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_zones: A list of zone names that can be used to control
      the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_zones,
      scope_name='zone',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetZonalResourcesDicts(service, project, requested_zones, filter_expr, http,
                           batch_url, errors):
  """Lists resources that are scoped by zone and returns them as dicts.

  It has the same functionality as GetZonalResouces but skips translating
  JSON to messages saving lot of CPU cycles.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_zones: A list of zone names that can be used to control
      the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_zones,
      scope_name='zone',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)


def GetRegionalResources(service, project, requested_regions,
                         filter_expr, http, batch_url, errors):
  """Lists resources that are scoped by region.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_regions: A list of region names that can be used to
      control the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_regions,
      scope_name='region',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetRegionalResourcesDicts(service, project, requested_regions, filter_expr,
                              http, batch_url, errors):
  """Lists resources that are scoped by region and returns them as dicts.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    requested_regions: A list of region names that can be used to
      control the scope of the list call.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=requested_regions,
      scope_name='region',
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)


def GetGlobalResources(service, project, filter_expr, http,
                       batch_url, errors):
  """Lists resources in the global scope.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A generator that yields JSON-serializable dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=None,
      scope_name=None,
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.MakeRequests)


def GetGlobalResourcesDicts(service, project, filter_expr, http, batch_url,
                            errors):
  """Lists resources in the global scope and returns them as dicts.

  Args:
    service: An apitools service object.
    project: The Compute Engine project name for which listing should be
      performed.
    filter_expr: A filter to pass to the list API calls.
    http: An httplib2.Http-like object.
    batch_url: The handler for making batch requests.
    errors: A list for capturing errors.

  Returns:
    A list of dicts representing the results.
  """
  return _GetResources(
      service=service,
      project=project,
      scopes=None,
      scope_name=None,
      filter_expr=filter_expr,
      http=http,
      batch_url=batch_url,
      errors=errors,
      make_requests=request_helper.ListJson)


def _GroupByProject(locations):
  """Group locations by project field."""
  result = {}
  for location in locations or []:
    if location.project not in result:
      result[location.project] = []
    result[location.project].append(location)
  return result


def Invoke(frontend, implementation):
  return implementation(frontend)


def ComposeSyncImplementation(generator, executor):

  def Implementation(frontend):
    return executor(generator(frontend), frontend)

  return Implementation


class GlobalScope(set):
  pass


class ZoneSet(set):
  pass


class RegionSet(set):
  pass


class AllScopes(object):
  """Holds information about wildcard use of list command."""

  def __init__(self, projects, zonal, regional):
    self.projects = projects
    self.zonal = zonal
    self.regional = regional

  def __eq__(self, other):
    if not isinstance(other, AllScopes):
      return False  # AllScopes is not suited for inheritance
    return (self.projects == other.projects and self.zonal == other.zonal and
            self.regional == other.regional)

  def __ne__(self, other):
    return not self == other

  def __hash__(self):
    return hash(self.projects) ^ hash(self.zonal) ^ hash(self.regional)

  def __repr__(self):
    return 'AllScopes(projects={}, zonal={}, regional={})'.format(
        repr(self.projects), repr(self.zonal), repr(self.regional))


class ListException(exceptions.ToolException):
  pass


# TODO(b/38256601) - Drop these flags
def AddBaseListerArgs(parser):
  """Add arguments defined by base_classes.BaseLister."""
  parser.add_argument(
      'names',
      action=actions.DeprecationAction(
          'names',
          warn='This argument is deprecated. '
          'Use `--filter="name =( NAME ... )"` instead.'),
      metavar='NAME',
      nargs='*',
      default=[],
      completer=completers.DeprecatedInstancesCompleter,
      help=('If provided, show details for the specified names and/or URIs of '
            'resources.'))

  parser.add_argument(
      '--regexp',
      '-r',
      action=actions.DeprecationAction(
          'regexp',
          warn='This flag is deprecated. '
          'Use `--filter="name ~ REGEXP"` instead.'),
      help="""\
        A regular expression to filter the names of the results  on. Any names
        that do not match the entire regular expression will be filtered out.\
        """)


# TODO(b/38256601) - Drop these flags
def AddZonalListerArgs(parser):
  """Add arguments defined by base_classes.ZonalLister."""
  AddBaseListerArgs(parser)
  parser.add_argument(
      '--zones',
      action=actions.DeprecationAction(
          'zones',
          warn='This flag is deprecated. '
          'Use ```--filter="zone :( *ZONE ... )"``` instead.'),
      metavar='ZONE',
      help='If provided, only resources from the given zones are queried.',
      type=arg_parsers.ArgList(min_length=1),
      completer=completers.ZonesCompleter,
      default=[])


class _Frontend(object):
  """Example of conforming Frontend implementation."""

  def __init__(self, filter_expr=None, maxResults=None, scopeSet=None):
    self._filter_expr = filter_expr
    self._max_results = maxResults
    self._scope_set = scopeSet

  @property
  def filter(self):
    return self._filter_expr

  @property
  def max_results(self):
    return self._max_results

  @property
  def scope_set(self):
    return self._scope_set


def _GetListCommandFrontendPrototype(args):
  """Make Frontend suitable for ListCommand argument namespace.

  Generated filter is a pair (client-side filter, server-side filter).

  Args:
    args: The argument namespace of ListCommand.

  Returns:
    Frontend initialized with information from ListCommand argument namespace.
    Both client-side and server-side filter is returned.
  """
  filter_expr = filter_rewrite.Rewriter().Rewrite(args.filter)
  max_results = int(args.page_size) if args.page_size else None
  if args.limit and (max_results is None or max_results > args.limit):
    max_results = args.limit
  return _Frontend(filter_expr=filter_expr, maxResults=max_results)


def _GetBaseListerFrontendPrototype(args):
  """Make Frontend suitable for BaseLister argument namespace.

  Generated client-side filter is stored to args.filter. Generated server-side
  filter is None. Client-side filter should be processed using
  filter_rewrite.Rewriter before use to take advantage of possible server-side
  filtering.

  Args:
    args: The argument namespace of BaseLister.

  Returns:
    Frontend initialized with information from BaseLister argument namespace.
    Server-side filter is None.
  """
  frontend = _GetListCommandFrontendPrototype(args)
  filter_args = []
  if args.filter:
    filter_args.append('('+args.filter+')')
  if args.regexp:
    filter_args.append('(name ~ {})'.format(resource_expr_rewrite.BackendBase()
                                            .Quote(args.regexp)))
  if args.names:
    name_regexp = ' '.join([
        resource_expr_rewrite.BackendBase().Quote(name) for name in args.names
        if not name.startswith('https://')
    ])
    selflink_regexp = ' '.join([
        resource_expr_rewrite.BackendBase().Quote(name) for name in args.names
        if name.startswith('https://')
    ])
    if not selflink_regexp:
      filter_args.append('(name =({}))'.format(name_regexp))
    elif not name_regexp:
      filter_args.append('(selfLink =({}))'.format(selflink_regexp))
    else:
      filter_args.append('((name =({})) OR (selfLink =({})))'.format(
          name_regexp, selflink_regexp))
  # Refine args.filter specification to reuse gcloud filtering logic
  # for filtering based on instance names
  args.filter = ' AND '.join(filter_args)

  return _Frontend(None, frontend.max_results, frontend.scope_set)


def ParseZonalFlags(args, resources):
  """Make Frontend suitable for ZonalLister argument namespace.

  Generated client-side filter is stored to args.filter.

  Args:
    args: The argument namespace of BaseLister.
    resources: resources.Registry, The resource registry

  Returns:
    Frontend initialized with information from BaseLister argument namespace.
    Server-side filter is None.
  """
  frontend = _GetBaseListerFrontendPrototype(args)
  filter_expr = frontend.filter
  if args.zones:
    scope_set = ZoneSet([
        resources.Parse(
            z,
            params={'project': properties.VALUES.core.project.GetOrFail},
            collection='compute.zones') for z in args.zones
    ])
    # Refine args.filter specification to reuse gcloud filtering logic
    # for filtering based on zones
    filter_arg = '({}) AND '.format(args.filter) if args.filter else ''
    # How to escape '*' in zone and what are special characters for
    # simple pattern?
    zone_regexp = ' '.join(['*'+ zone for zone in args.zones])
    zone_arg = '(zone :({}))'.format(zone_regexp)
    args.filter = filter_arg + zone_arg
    args.filter, filter_expr = filter_rewrite.Rewriter().Rewrite(args.filter)
  else:
    scope_set = AllScopes(
        [
            resources.Parse(
                properties.VALUES.core.project.GetOrFail(),
                collection='compute.projects')
        ],
        zonal=True,
        regional=False)
  frontend = _Frontend(filter_expr, frontend.max_results, scope_set)
  return frontend


class ZonalLister(object):
  """Implementation for former base_classes.ZonalLister subclasses.

  This implementation should be used only for porting from base_classes.

  Attributes:
    client: The compute client.
    service: Zonal service whose resources will be listed.
  """
  # Quick and dirty implementation based on GetZonalResources defined above

  def __init__(self, client, service):
    self.client = client
    self.service = service

  def __deepcopy__(self, memodict=None):
    return self  # ZonalLister is immutable

  def __eq__(self, other):
    if not isinstance(other, ZonalLister):
      return False  # ZonalLister is not suited for inheritance
    return self.client == other.client and self.service == other.service

  def __ne__(self, other):
    return not self == other

  def __hash__(self):
    return hash(self.client) ^ hash(self.service)

  def __repr__(self):
    return 'ZonalLister({}, {})'.format(repr(self.client), repr(self.service))

  def __call__(self, frontend):
    errors = []
    scope_set = frontend.scope_set
    filter_expr = frontend.filter
    if isinstance(scope_set, ZoneSet):
      for project, zones in _GroupByProject(
          sorted(list(scope_set))).iteritems():
        for item in GetZonalResourcesDicts(
            service=self.service,
            project=project,
            requested_zones=[zone_ref.zone for zone_ref in zones],
            filter_expr=filter_expr,
            http=self.client.apitools_client.http,
            batch_url=self.client.batch_url,
            errors=errors):
          yield item
    else:
      # scopeSet is AllScopes
      # generate AggregatedList
      for project_ref in sorted(list(scope_set.projects)):
        for item in GetZonalResourcesDicts(
            service=self.service,
            project=project_ref.project,
            requested_zones=[],
            filter_expr=filter_expr,
            http=self.client.apitools_client.http,
            batch_url=self.client.batch_url,
            errors=errors):
          yield item
    if errors:
      utils.RaiseException(errors, ListException)
