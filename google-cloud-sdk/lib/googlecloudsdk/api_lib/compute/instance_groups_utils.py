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
"""Convenience functions and classes for dealing with instances groups."""
import abc
import sys
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import property_selector
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources as resource_exceptions


def ValidateInstanceInZone(instances, zone):
  """Validate if provided list in zone given as parameter.

  Args:
    instances: list of instances resources to be validated
    zone: a zone all instances must be in order to pass validation

  Raises:
    InvalidArgumentException: If any instance is in different zone
                              than given as parameter.
  """
  invalid_instances = [inst.SelfLink()
                       for inst in instances if inst.zone != zone]
  if any(invalid_instances):
    raise exceptions.InvalidArgumentException(
        'instances', 'The zone of instance must match the instance group zone. '
        'Following instances has invalid zone: %s'
        % ', '.join(invalid_instances))


def GetSortKey(sort_by, columns):
  """Gets the sort key from columns declaration based on sort_by parameter."""
  descending = False
  sort_key_fn = None
  if sort_by:
    if sort_by.startswith('~'):
      sort_by = sort_by[1:]
      descending = True
    sort_key_fn = dict(columns).get(sort_by, None)
    if sort_key_fn is not None:
      if isinstance(sort_key_fn, property_selector.PropertyGetter):
        sort_key_fn = sort_key_fn.Get
    else:
      sort_key_fn = None
  return sort_key_fn, descending


def _UnwrapResponse(responses, attr_name):
  """Extracts items stored in given attribute of instance group response."""
  for response in responses:
    for item in getattr(response, attr_name):
      yield item


class InstanceGroupDescribe(base_classes.ZonalDescriber,
                            base_classes.InstanceGroupDynamicProperiesMixin):
  """Describe an instance group."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDescriber.Args(parser)
    base_classes.AddFieldsFlag(parser, 'instanceGroups')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'

  def ComputeDynamicProperties(self, args, items):
    return self.ComputeInstanceGroupManagerMembership(
        items=items,
        filter_mode=base_classes.InstanceGroupFilteringMode.all_groups)

  detailed_help = {
      'brief': 'Describe an instance group',
      'DESCRIPTION': """\
          *{command}* displays detailed information about a Google Compute
          Engine instance group.
          """,
  }


class InstanceGroupListInstancesBase(base_classes.BaseCommand):
  """Base class for listing instances present in instance group."""

  # TODO(user): add support for --names parameter as in all List verbs

  _LIST_TABS = []
  _FIELD_TRANSFORMS = []

  @staticmethod
  def ListInstancesArgs(parser, multizonal=False):
    parser.add_argument(
        'name',
        help='The name of the instance group.')

    parser.add_argument(
        '--limit',
        type=arg_parsers.BoundedInt(1, sys.maxint),
        help='The maximum number of results.')

    sort_by = parser.add_argument(
        '--sort-by',
        help='A field to sort by.')
    sort_by.detailed_help = """\
        A field to sort by. To perform a descending-order sort, prefix
        the value of this flag with a tilde (``~'').
        """

    uri = parser.add_argument(
        '--uri',
        action='store_true',
        help='If provided, a list of URIs is printed instead of a table.')
    uri.detailed_help = """\
        If provided, the list command will only print URIs for the
        resources returned.  If this flag is not provided, the list
        command will print a human-readable table of useful resource
        data.
        """

    if multizonal:
      scope_parser = parser.add_mutually_exclusive_group()
      flags.AddRegionFlag(
          scope_parser,
          resource_type='instance group',
          operation_type='list instances in',
          explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)
      flags.AddZoneFlag(
          scope_parser,
          resource_type='instance group',
          operation_type='list instances in',
          explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT)
    else:
      flags.AddZoneFlag(
          parser,
          resource_type='instance group',
          operation_type='list instances in')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'

  @property
  def method(self):
    return 'ListInstances'

  @property
  def list_field(self):
    return 'items'

  def Run(self, args):
    sort_key_fn = None
    descending = False
    errors = []

    if args.uri:
      field_selector = None
    else:
      field_selector = property_selector.PropertySelector(
          properties=None,
          transformations=self._FIELD_TRANSFORMS)

    sort_key_fn, descending = GetSortKey(args.sort_by, self._LIST_TABS)
    responses, errors = self.GetResources(args)
    if errors:
      utils.RaiseToolException(errors)
    items = lister.ProcessResults(
        resources=list(_UnwrapResponse(responses, self.list_field)),
        field_selector=field_selector,
        sort_key_fn=sort_key_fn,
        reverse_sort=descending,
        limit=args.limit)

    for item in items:
      if args.uri:
        yield item['instance']
      else:
        yield item

  @abc.abstractmethod
  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    pass

  def Display(self, args, resources):
    if args.uri:
      for resource in resources:
        log.out.Print(resource)
    else:
      base_classes.PrintTable(resources, self._LIST_TABS)

  detailed_help = {
      'brief': 'List instances present in the instance group',
      'DESCRIPTION': """\
          *{command}* list instances in an instance group.
          """,
  }


class InstanceGroupListInstances(InstanceGroupListInstancesBase):
  """List Google Compute Engine instances present in instance group."""

  _LIST_TABS = [
      ('NAME', property_selector.PropertyGetter('instance')),
      ('STATUS', property_selector.PropertyGetter('status'))]

  _FIELD_TRANSFORMS = [('instance', path_simplifier.Name)]

  @staticmethod
  def Args(parser):
    InstanceGroupListInstancesBase.ListInstancesArgs(parser, multizonal=False)
    regexp = parser.add_argument(
        '--regexp', '-r',
        help='A regular expression to filter the names of the results on.')
    regexp.detailed_help = """\
        A regular expression to filter the names of the results on. Any names
        that do not match the entire regular expression will be filtered out.
        """

  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    group_ref = self.CreateZonalReference(args.name, args.zone)

    if args.regexp:
      filter_expr = 'instance eq {0}'.format(args.regexp)
    else:
      filter_expr = None

    request = self.service.GetRequestType(self.method)(
        instanceGroup=group_ref.Name(),
        instanceGroupsListInstancesRequest=(
            self.messages.InstanceGroupsListInstancesRequest()),
        zone=group_ref.zone,
        filter=filter_expr,
        project=self.context['project'])

    errors = []
    results = list(request_helper.MakeRequests(
        requests=[(self.service, self.method, request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    return results, errors


class InstanceGroupReferenceMixin(object):
  """Mixin with method resolving instance group references."""

  def CreateInstanceGroupReferences(
      self, names, region, zone,
      zonal_resource_type='instanceGroupManagers',
      regional_resource_type='regionInstanceGroupManagers'):
    """Creates references to instance group (zonal or regional)."""
    resolved_refs = {}
    unresolved_names = []
    for name in names:
      try:
        ref = self.resources.Parse(name,
                                   params={'region': region, 'zone': zone})
        resolved_refs[name] = ref
      except resource_exceptions.UnknownCollectionException:
        unresolved_names.append(name)
        resolved_refs[name] = None

    if unresolved_names:
      if region is not None:
        refs = self.CreateRegionalReferences(
            unresolved_names, region, resource_type=regional_resource_type)
      elif zone is not None:
        refs = self.CreateZonalReferences(
            unresolved_names, zone, resource_type=zonal_resource_type)
      else:
        refs = self.PromptForMultiScopedReferences(
            unresolved_names,
            scope_names=['zone', 'region'],
            scope_services=[self.compute.zones, self.compute.regions],
            resource_types=[zonal_resource_type, regional_resource_type],
            flag_names=['--zone', '--region'])
      for (name, ref) in zip(unresolved_names, refs):
        resolved_refs[name] = ref

    return [resolved_refs[name] for name in names]

  def CreateInstanceGroupReference(
      self, name, region, zone,
      zonal_resource_type='instanceGroupManagers',
      regional_resource_type='regionInstanceGroupManagers'):
    """Creates reference to instance group (zonal or regional)."""
    return self.CreateInstanceGroupReferences([name], region, zone,
                                              zonal_resource_type,
                                              regional_resource_type)[0]


class InstanceGroupGetNamedPorts(base_classes.BaseCommand):
  """Get named ports in Google Compute Engine instance groups."""

  _COLUMNS = [
      ('NAME', property_selector.PropertyGetter('name')),
      ('PORT', property_selector.PropertyGetter('port'))]

  @staticmethod
  def AddArgs(parser, multizonal):
    parser.add_argument(
        'name',
        help='The name of the instance group.')

    parser.add_argument(
        '--limit',
        type=arg_parsers.BoundedInt(1, sys.maxint),
        help='The maximum number of results.')

    sort_by = parser.add_argument(
        '--sort-by',
        help='A field to sort by.')
    sort_by.detailed_help = """\
        A field to sort by. To perform a descending-order sort, prefix
        the value of this flag with a tilde (``~'').
        """

    if multizonal:
      scope_parser = parser.add_mutually_exclusive_group()
      flags.AddRegionFlag(
          scope_parser,
          resource_type='instance or instance group',
          operation_type='get named ports for',
          explanation=flags.REGION_PROPERTY_EXPLANATION_NO_DEFAULT)
      flags.AddZoneFlag(
          scope_parser,
          resource_type='instance or instance group',
          operation_type='get named ports for',
          explanation=flags.ZONE_PROPERTY_EXPLANATION_NO_DEFAULT)
    else:
      flags.AddZoneFlag(
          parser,
          resource_type='instance or instance group',
          operation_type='get named ports for')

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'

  @property
  def method(self):
    return 'GetNamedPorts'

  def Run(self, args):
    field_selector = property_selector.PropertySelector(
        properties=None,
        transformations=[])

    sort_key_fn, descending = GetSortKey(args.sort_by, self._COLUMNS)
    responses, errors = self.GetResources(args)
    if errors:
      utils.RaiseToolException(errors)
    return lister.ProcessResults(
        resources=list(_UnwrapResponse(responses, 'namedPorts')),
        field_selector=field_selector,
        sort_key_fn=sort_key_fn,
        reverse_sort=descending,
        limit=args.limit)

  def GetResources(self, args):
    """Retrieves response with named ports."""
    group_ref = self.CreateZonalReference(args.name, args.zone)
    request = self.service.GetRequestType('Get')(
        instanceGroup=group_ref.Name(),
        zone=group_ref.zone,
        project=self.project)

    errors = []
    results = list(request_helper.MakeRequests(
        requests=[(self.service, 'Get', request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    return results, errors

  def Display(self, args, resources):
    base_classes.PrintTable(resources, self._COLUMNS)

  detailed_help = {
      'brief': 'Lists the named ports for an instance group resource',
      'DESCRIPTION': """\
          Named ports are key:value pairs metadata representing
          the service name and the port that it's running on. Named ports
          can be assigned to an instance group, which indicates that the service
          is available on all instances in the group. This information is used
          by the HTTP Load Balancing service.

          *{command}* lists the named ports (name and port tuples)
          for an instance group.
          """,
      'EXAMPLES': """\
          For example, to list named ports for an instance group:

            $ {command} example-instance-group --zone us-central1-a

          The above example lists named ports assigned to an instance
          group named 'example-instance-group' in the ``us-central1-a'' zone.
          """,
  }


class FingerprintFetchException(core_exceptions.Error):
  """Exception thrown when there is a problem with getting fingerprint."""


class InstanceGroupSetNamedPorts(base_classes.NoOutputAsyncMutator):
  """Sets named ports for instance groups."""

  @staticmethod
  def AddArgs(parser, multizonal):
    parser.add_argument(
        'group',
        help='The name of the instance group.')

    parser.add_argument(
        '--named-ports',
        required=True,
        type=arg_parsers.ArgList(),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='NAME:PORT',
        help="""\
            The comma-separated list of key:value pairs representing
            the service name and the port that it is running on.

            To clear the list of named ports pass empty list as flag value.
            For example:

              $ {command} example-instance-group --named-ports ""
            """)

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

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def method(self):
    return 'SetNamedPorts'

  @property
  def resource_type(self):
    return 'instanceGroups'

  def CreateRequests(self, args):
    group_ref = self.GetGroupReference(args)
    ports = []
    for named_port in args.named_ports:
      if named_port.count(':') != 1:
        raise exceptions.InvalidArgumentException(
            named_port, 'Named ports should follow NAME:PORT format.')
      host, port = named_port.split(':')
      if not port.isdigit():
        raise exceptions.InvalidArgumentException(
            named_port, 'Named ports should follow NAME:PORT format.')
      ports.append(self.messages.NamedPort(name=host, port=int(port)))

    # Instance group fingerprint will be used for optimistic locking. Each
    # modification of instance group changes the fingerprint. This request will
    # fail if instance group fingerprint does not match fingerprint sent in
    # request.
    fingerprint = self.GetGroupFingerprint(group=group_ref)
    request = self.CreateRequestForGroup(group_ref, ports, fingerprint)
    service = self.GetServiceForGroup(group_ref)

    return [(service, self.method, request)]

  def GetGroupReference(self, args):
    return self.CreateZonalReference(args.group, args.zone)

  def GetServiceForGroup(self, group_ref):
    _ = group_ref
    return self.compute.instanceGroups

  def CreateRequestForGroup(self, group_ref, ports, fingerprint):
    request_body = self.messages.InstanceGroupsSetNamedPortsRequest(
        fingerprint=fingerprint,
        namedPorts=ports)

    request = self.messages.ComputeInstanceGroupsSetNamedPortsRequest(
        instanceGroup=group_ref.Name(),
        instanceGroupsSetNamedPortsRequest=request_body,
        zone=group_ref.zone,
        project=self.project)

    return request

  def GetGroupFingerprint(self, group):
    """Gets fingerprint of given instance group."""
    get_request = self.messages.ComputeInstanceGroupsGetRequest(
        instanceGroup=group.Name(),
        zone=group.zone,
        project=self.project)

    errors = []
    resources = list(request_helper.MakeRequests(
        requests=[(
            self.compute.instanceGroups,
            'Get',
            get_request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    if errors:
      utils.RaiseException(
          errors,
          FingerprintFetchException,
          error_message='Could not set named ports for resource:')
    return resources[0].fingerprint

  detailed_help = {
      'brief': 'Sets the list of named ports for an instance group',
      'DESCRIPTION': """\
          Named ports are key:value pairs metadata representing
          the service name and the port that it's running on. Named ports
          can be assigned to an instance group, which
          indicates that the service is available on all instances in the
          group. This information is used by the HTTP Load Balancing
          service.

          *{command}* sets the list of named ports for all instances
          in an instance group.
          """,
      'EXAMPLES': """\
          For example, to apply the named ports to an entire instance group:

            $ {command} example-instance-group --named-ports example-service:1111 --zone us-central1-a

          The above example will assign a name 'example-service' for port 1111
          to the instance group called 'example-instance-group' in the
          ``us-central1-a'' zone. The command removes any named ports that are
          already set for this instance group.

          To clear named ports from instance group provide empty named ports
          list as parameter:

            $ {command} example-instance-group --named-ports "" --zone us-central1-a
          """,
  }


class InstancesReferenceMixin(object):
  """Creates reference to instances in instance group (zonal or regional)."""

  def CreateInstanceReferences(self, group_ref, instance_names, errors):
    if group_ref.Collection() == 'compute.instanceGroupManagers':
      instances_refs = self.CreateZonalReferences(
          instance_names, group_ref.zone, resource_type='instances')
      return [instance_ref.SelfLink() for instance_ref in instances_refs]
    else:
      service = self.compute.regionInstanceGroupManagers
      request = service.GetRequestType('ListManagedInstances')(
          instanceGroupManager=group_ref.Name(),
          region=group_ref.region,
          project=self.context['project'])
      results = list(request_helper.MakeRequests(
          requests=[(service, 'ListManagedInstances', request)],
          http=self.http,
          batch_url=self.batch_url,
          errors=errors,
          custom_get_requests=None))[0].managedInstances
      # here we assume that instances are uniquely named within RMIG
      return [instance_ref.instance for instance_ref in results
              if path_simplifier.Name(instance_ref.instance) in instance_names
              or instance_ref.instance in instance_names]
