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
import enum

from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import resources as resource_exceptions


def IsZonalGroup(group_ref):
  """Checks if group reference is zonal."""
  return group_ref.Collection() == 'compute.instanceGroups'


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


def _UnwrapResponse(responses, attr_name):
  """Extracts items stored in given attribute of instance group response."""
  for response in responses:
    for item in getattr(response, attr_name):
      yield item


class InstanceGroupDescribe(base_classes.ZonalDescriber):
  """Describe an instance group."""

  @staticmethod
  def Args(parser):
    base_classes.ZonalDescriber.Args(parser)

  @property
  def service(self):
    return self.compute.instanceGroups

  @property
  def resource_type(self):
    return 'instanceGroups'

  def ComputeDynamicProperties(self, args, items):
    return ComputeInstanceGroupManagerMembership(
        compute=self.compute,
        project=self.project,
        http=self.http,
        batch_url=self.batch_url,
        items=items,
        filter_mode=InstanceGroupFilteringMode.ALL_GROUPS)

  detailed_help = {
      'brief': 'Describe an instance group',
      'DESCRIPTION': """\
          *{command}* displays detailed information about a Google Compute
          Engine instance group.
          """,
  }


class InstanceGroupListInstancesBase(base_classes.BaseLister):
  """Base class for listing instances present in instance group."""

  # TODO(user): add support for --names parameter as in all List verbs

  @staticmethod
  def ListInstancesArgs(parser, multizonal=False):
    parser.add_argument(
        'name',
        help='The name of the instance group.')

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
    errors = []

    responses, errors = self.GetResources(args)
    if errors:
      utils.RaiseToolException(errors)
    items = lister.ProcessResults(
        resources=list(_UnwrapResponse(responses, self.list_field)),
        field_selector=None,
        limit=args.limit)

    for item in items:
      yield item

  @abc.abstractmethod
  def GetResources(self, args):
    """Retrieves response with instance in the instance group."""
    pass

  @staticmethod
  def GetUriCacheUpdateOp():
    """This command class does not update the URI cache."""
    return None

  def GetUriFunc(self):

    def _GetUri(resource):
      return resource['instance']

    return _GetUri

  def Format(self, unused_args):
    return 'table(instance.basename():label=NAME, status)'

  detailed_help = {
      'brief': 'List instances present in the instance group',
      'DESCRIPTION': """\
          *{command}* list instances in an instance group.
          """,
  }


class InstanceGroupListInstances(InstanceGroupListInstancesBase):
  """List Google Compute Engine instances present in instance group."""

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
        project=group_ref.project)

    errors = []
    results = list(request_helper.MakeRequests(
        requests=[(self.service, self.method, request)],
        http=self.http,
        batch_url=self.batch_url,
        errors=errors,
        custom_get_requests=None))

    return results, errors


def CreateInstanceGroupReferences(
    scope_prompter, compute, resources, names, region, zone,
    zonal_resource_type='instanceGroupManagers',
    regional_resource_type='regionInstanceGroupManagers'):
  """Creates references to instance group (zonal or regional).

  Args:
    scope_prompter: scope prompter (for creating zonal/regional references),
    compute: compute API object,
    resources: GCE resources object,
    names: resource names,
    region: region to resolve unscoped references,
    zone: zone to resolve unscoped references,,
    zonal_resource_type: type for zonal resource,
    regional_resource_type: type for regional resource,

  Returns:
    list of resource references
  """

  resolved_refs = {}
  unresolved_names = []
  for name in names:
    try:
      ref = resources.Parse(name, params={'region': region, 'zone': zone})
      resolved_refs[name] = ref
    except resource_exceptions.UnknownCollectionException:
      unresolved_names.append(name)
      resolved_refs[name] = None

  if unresolved_names:
    if region is not None:
      refs = scope_prompter.CreateRegionalReferences(
          unresolved_names, region, resource_type=regional_resource_type)
    elif zone is not None:
      refs = scope_prompter.CreateZonalReferences(
          unresolved_names, zone, resource_type=zonal_resource_type)
    else:
      refs = scope_prompter.PromptForMultiScopedReferences(
          unresolved_names,
          scope_names=['zone', 'region'],
          scope_services=[compute.zones, compute.regions],
          resource_types=[zonal_resource_type, regional_resource_type],
          flag_names=['--zone', '--region'])
    for (name, ref) in zip(unresolved_names, refs):
      resolved_refs[name] = ref

  return [resolved_refs[name] for name in names]


def CreateInstanceGroupReference(
    scope_prompter, compute, resources, name, region, zone,
    zonal_resource_type='instanceGroupManagers',
    regional_resource_type='regionInstanceGroupManagers'):
  """Creates single reference to instance group (zonal or regional).

  Args:
    scope_prompter: scope prompter (for creating zonal/regional references),
    compute: compute API object,
    resources: GCE resources object,
    name: resource name,
    region: region to resolve unscoped references,
    zone: zone to resolve unscoped references,,
    zonal_resource_type: type for zonal resource,
    regional_resource_type: type for regional resource,

  Returns:
    list of resource references
  """

  return CreateInstanceGroupReferences(scope_prompter, compute, resources,
                                       [name], region, zone,
                                       zonal_resource_type,
                                       regional_resource_type)[0]


class InstanceGroupGetNamedPortsBase(
    base.ListCommand, base_classes.BaseCommand):
  """Get named ports in Google Compute Engine instance groups."""

  @staticmethod
  def AddArgs(parser, multizonal):
    parser.add_argument(
        'name',
        help='The name of the instance group.')

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

  @staticmethod
  def GetUriCacheUpdateOp():
    """This command class does not update the URI cache."""
    return None

  def Format(self, unused_args):
    return 'table(name, port)'

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


def OutputNamedPortsForGroup(group_ref, compute_client):
  """Gets the request to fetch instance group."""
  compute = compute_client.apitools_client
  if group_ref.Collection() == 'compute.instanceGroups':
    service = compute.instanceGroups
    request = service.GetRequestType('Get')(
        instanceGroup=group_ref.Name(),
        zone=group_ref.zone,
        project=group_ref.project)
  else:
    service = compute.regionInstanceGroups
    request = service.GetRequestType('Get')(
        instanceGroup=group_ref.Name(),
        region=group_ref.region,
        project=group_ref.project)
  results = compute_client.MakeRequests(requests=[(service, 'Get', request)])
  return list(_UnwrapResponse(results, 'namedPorts'))


class FingerprintFetchException(core_exceptions.Error):
  """Exception thrown when there is a problem with getting fingerprint."""


def _GetGroupFingerprint(compute_client, group_ref):
  """Gets fingerprint of given instance group."""
  compute = compute_client.apitools_client
  if IsZonalGroup(group_ref):
    service = compute.instanceGroups
  else:
    service = compute.regionInstanceGroups

  errors = []
  resources = compute_client.MakeRequests(
      requests=[(service, 'Get', group_ref.Request())],
      errors_to_collect=errors)

  if errors:
    utils.RaiseException(
        errors,
        FingerprintFetchException,
        error_message='Could not set named ports for resource:')
  return resources[0].fingerprint


def GetSetNamedPortsRequestForGroup(compute_client, group_ref, ports):
  """Returns a request to get named ports and service to send request.

  Args:
    compute_client: GCE API client,
    group_ref: reference to instance group (zonal or regional),
    ports: list of named ports to set

  Returns:
    request, message to send in order to set named ports on instance group,
    service, service where request should be sent
      - regionInstanceGroups for regional groups
      - instanceGroups for zonal groups
  """
  compute = compute_client.apitools_client
  messages = compute_client.messages
  # Instance group fingerprint will be used for optimistic locking. Each
  # modification of instance group changes the fingerprint. This request will
  # fail if instance group fingerprint does not match fingerprint sent in
  # request.
  fingerprint = _GetGroupFingerprint(compute_client, group_ref)
  if IsZonalGroup(group_ref):
    request_body = messages.InstanceGroupsSetNamedPortsRequest(
        fingerprint=fingerprint,
        namedPorts=ports)
    return messages.ComputeInstanceGroupsSetNamedPortsRequest(
        instanceGroup=group_ref.Name(),
        instanceGroupsSetNamedPortsRequest=request_body,
        zone=group_ref.zone,
        project=group_ref.project), compute.instanceGroups
  else:
    request_body = messages.RegionInstanceGroupsSetNamedPortsRequest(
        fingerprint=fingerprint,
        namedPorts=ports)
    return messages.ComputeRegionInstanceGroupsSetNamedPortsRequest(
        instanceGroup=group_ref.Name(),
        regionInstanceGroupsSetNamedPortsRequest=request_body,
        region=group_ref.region,
        project=group_ref.project), compute.regionInstanceGroups


def ValidateAndParseNamedPortsArgs(messages, named_ports):
  """Validates named ports flags."""
  ports = []
  for named_port in named_ports:
    if named_port.count(':') != 1:
      raise exceptions.InvalidArgumentException(
          named_port, 'Named ports should follow NAME:PORT format.')
    host, port = named_port.split(':')
    if not port.isdigit():
      raise exceptions.InvalidArgumentException(
          named_port, 'Named ports should follow NAME:PORT format.')
    ports.append(messages.NamedPort(name=host, port=int(port)))
  return ports


SET_NAMED_PORTS_HELP = {
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


def CreateInstanceReferences(
    scope_prompter, compute_client, group_ref, instance_names):
  """Creates reference to instances in instance group (zonal or regional)."""
  compute = compute_client.apitools_client
  if group_ref.Collection() == 'compute.instanceGroupManagers':
    instances_refs = scope_prompter.CreateZonalReferences(
        instance_names, group_ref.zone, resource_type='instances')
    return [instance_ref.SelfLink() for instance_ref in instances_refs]
  else:
    service = compute.regionInstanceGroupManagers
    request = service.GetRequestType('ListManagedInstances')(
        instanceGroupManager=group_ref.Name(),
        region=group_ref.region,
        project=group_ref.project)
    results = compute_client.MakeRequests(requests=[
        (service, 'ListManagedInstances', request)])[0].managedInstances
    # here we assume that instances are uniquely named within RMIG
    return [instance_ref.instance for instance_ref in results
            if path_simplifier.Name(instance_ref.instance) in instance_names
            or instance_ref.instance in instance_names]


class InstanceGroupFilteringMode(enum.Enum):
  """Filtering mode for Instance Groups based on dynamic properties."""
  ALL_GROUPS = 1
  ONLY_MANAGED_GROUPS = 2
  ONLY_UNMANAGED_GROUPS = 3


def ComputeInstanceGroupManagerMembership(
    compute, project, http, batch_url, items,
    filter_mode=(InstanceGroupFilteringMode.ALL_GROUPS)):
  """Add information if instance group is managed.

  Args:
    compute: GCE Compute API client,
    project: str, project name
    http: http client,
    batch_url: str, batch url
    items: list of instance group messages,
    filter_mode: InstanceGroupFilteringMode, managed/unmanaged filtering options
  Returns:
    list of instance groups with computed dynamic properties
  """
  errors = []
  items = list(items)
  zone_names = set([path_simplifier.Name(ig['zone'])
                    for ig in items if 'zone' in ig])
  region_names = set([path_simplifier.Name(ig['region'])
                      for ig in items if 'region' in ig])

  if zone_names:
    zonal_instance_group_managers = lister.GetZonalResources(
        service=compute.instanceGroupManagers,
        project=project,
        requested_zones=zone_names,
        filter_expr=None,
        http=http,
        batch_url=batch_url,
        errors=errors)
  else:
    zonal_instance_group_managers = []

  if region_names and hasattr(compute, 'regionInstanceGroups'):
    # regional instance groups are just in 'alpha' API
    regional_instance_group_managers = lister.GetRegionalResources(
        service=compute.regionInstanceGroupManagers,
        project=project,
        requested_regions=region_names,
        filter_expr=None,
        http=http,
        batch_url=batch_url,
        errors=errors)
  else:
    regional_instance_group_managers = []

  instance_group_managers = (
      list(zonal_instance_group_managers)
      + list(regional_instance_group_managers))
  instance_group_managers_refs = set([
      path_simplifier.ScopedSuffix(igm.selfLink)
      for igm in instance_group_managers])

  if errors:
    utils.RaiseToolException(errors)

  results = []
  for item in items:
    self_link = item['selfLink']
    igm_self_link = self_link.replace(
        '/instanceGroups/', '/instanceGroupManagers/')
    scoped_suffix = path_simplifier.ScopedSuffix(igm_self_link)
    is_managed = scoped_suffix in instance_group_managers_refs

    if (is_managed and
        filter_mode == InstanceGroupFilteringMode.ONLY_UNMANAGED_GROUPS):
      continue
    elif (not is_managed and
          filter_mode == InstanceGroupFilteringMode.ONLY_MANAGED_GROUPS):
      continue

    item['isManaged'] = ('Yes' if is_managed else 'No')
    if is_managed:
      item['instanceGroupManagerUri'] = igm_self_link
    results.append(item)

  return results

