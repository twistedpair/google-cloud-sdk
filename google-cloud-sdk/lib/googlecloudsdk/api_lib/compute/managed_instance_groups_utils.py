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
"""Common functions and classes for dealing with managed instances groups."""

import random
import re
import string
import sys

from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties


_ALLOWED_UTILIZATION_TARGET_TYPES = [
    'DELTA_PER_MINUTE', 'DELTA_PER_SECOND', 'GAUGE']

_MAX_AUTOSCALER_NAME_LENGTH = 63
# 4 character chosen from between lowercase letters and numbers give >1.6M
# possibilities with no more than 100 Autoscalers in one Zone and Project
# so probability that adding an autoscaler will fail because of name conflict
# is about 6e-5.
_NUM_RANDOM_CHARACTERS_IN_AS_NAME = 4

CLOUD_PUB_SUB_VALID_RESOURCE_RE = r'^[A-Za-z][A-Za-z0-9-_.~+%]{2,}$'


class ResourceNotFoundException(exceptions.ToolException):
  pass


def ArgsSupportQueueScaling(args):
  return 'queue_scaling_acceptable_backlog_per_instance' in args


def AddAutoscalerArgs(parser, queue_scaling_enabled=False):
  """Adds commandline arguments to parser."""
  parser.add_argument(
      '--cool-down-period',
      type=arg_parsers.Duration(),
      help=('The time period that the autoscaler should wait before it starts '
            'collecting information from a new instance. This prevents the '
            'autoscaler from collecting information when the instance is '
            'initializing, during which the collected usage would not be '
            'reliable. The default is 60 seconds.'))
  parser.add_argument('--description', help='Notes about Autoscaler.')
  parser.add_argument('--min-num-replicas',
                      type=arg_parsers.BoundedInt(0, sys.maxint),
                      help='Minimum number of replicas Autoscaler will set.')
  parser.add_argument('--max-num-replicas',
                      type=arg_parsers.BoundedInt(0, sys.maxint), required=True,
                      help='Maximum number of replicas Autoscaler will set.')
  parser.add_argument('--scale-based-on-cpu',
                      action='store_true',
                      help='Autoscaler will be based on CPU utilization.')
  parser.add_argument('--scale-based-on-load-balancing',
                      action='store_true',
                      help=('Use autoscaling based on load balancing '
                            'utilization.'))
  parser.add_argument('--target-cpu-utilization',
                      type=arg_parsers.BoundedFloat(0.0, 1.0),
                      help='Autoscaler will aim to maintain CPU utilization at '
                      'target level (0.0 to 1.0).')
  parser.add_argument('--target-load-balancing-utilization',
                      type=arg_parsers.BoundedFloat(0.0, None),
                      help='Autoscaler will aim to maintain the load balancing '
                      'utilization level (greater than 0.0).')
  parser.add_argument(
      '--custom-metric-utilization',
      type=arg_parsers.ArgDict(
          spec={
              'metric': str,
              'utilization-target': float,
              'utilization-target-type': str,
          },
      ),
      action='append',
      help="""\
      Adds a target metric value for the to the Autoscaler.

      *metric*::: Protocol-free URL of a Google Cloud Monitoring metric.

      *utilization-target*::: Value of the metric Autoscaler will aim to
      maintain (greater than 0.0).

      *utilization-target-type*::: How target is expressed. Valid values: {0}.
      """.format(', '.join(_ALLOWED_UTILIZATION_TARGET_TYPES))
  )

  if queue_scaling_enabled:
    parser.add_argument(
        '--queue-scaling-cloud-pub-sub',
        type=arg_parsers.ArgDict(
            spec={
                'topic': str,
                'subscription': str,
            },
        ),
        help="""\
        Specifies queue-based scaling based on a Cloud Pub/Sub queuing system.
        Both topic and subscription are required.

        *topic*::: Topic specification. Can be just a name or a partial URL
        (starting with "projects/..."). Topic must belong to the same project as
        Autoscaler.

        *subscription*::: Subscription specification. Can be just a name or a
        partial URL (starting with "projects/..."). Subscription must belong to
        the same project as Autoscaler and must be connected to the specified
        topic.
        """
    )
    parser.add_argument('--queue-scaling-acceptable-backlog-per-instance',
                        type=arg_parsers.BoundedFloat(0.0, None),
                        help='Queue-based scaling target: autoscaler will aim '
                        'to assure that average number of tasks in the queue '
                        'is no greater than this value.',)
    parser.add_argument('--queue-scaling-single-worker-throughput',
                        type=arg_parsers.BoundedFloat(0.0, None),
                        help='Hint the autoscaler for queue-based scaling on '
                        'how much throughput a single worker instance is able '
                        'to consume.')


def _ValidateCloudPubSubResource(pubsub_spec_dict, expected_resource_type):
  """Validate Cloud Pub/Sub resource spec format."""
  def RaiseInvalidArgument(message):
    raise exceptions.InvalidArgumentException(
        '--queue-scaling-cloud-pub-sub:{0}'.format(expected_resource_type),
        message)

  if expected_resource_type not in pubsub_spec_dict:
    raise exceptions.ToolException(
        'Both topic and subscription are required for Cloud Pub/Sub '
        'queue scaling specification.')
  split_resource = pubsub_spec_dict[expected_resource_type].split('/')

  if len(split_resource) == 1:
    resource_name = split_resource[0]
  elif len(split_resource) == 4:
    (project_prefix, unused_project_name,
     resource_prefix, resource_name) = split_resource
    if project_prefix != 'projects':
      RaiseInvalidArgument(
          'partial-URL format for Cloud PubSub resource does not start with '
          '"projects/"')
    if resource_prefix != '{0}s'.format(expected_resource_type):
      RaiseInvalidArgument('not in valid resource types: topic, subscription.')
  else:
    RaiseInvalidArgument(
        'Cloud PubSub resource must either be just a name or a partial '
        'URL (starting with "projects/").')
  if not re.match(CLOUD_PUB_SUB_VALID_RESOURCE_RE, resource_name):
    RaiseInvalidArgument('resource name not valid.')


def ValidateAutoscalerArgs(args):
  """Validates args."""
  if args.min_num_replicas and args.max_num_replicas:
    if args.min_num_replicas > args.max_num_replicas:
      raise exceptions.InvalidArgumentException(
          '--max-num-replicas', 'can\'t be less than min num replicas.')

  if args.custom_metric_utilization:
    for custom_metric_utilization in args.custom_metric_utilization:
      for field in ('utilization-target', 'metric', 'utilization-target-type'):
        if field not in custom_metric_utilization:
          raise exceptions.InvalidArgumentException(
              '--custom-metric-utilization', field + ' not present.')
      if custom_metric_utilization['utilization-target'] < 0:
        raise exceptions.InvalidArgumentException(
            '--custom-metric-utilization utilization-target', 'less than 0.')

  if ArgsSupportQueueScaling(args):
    queue_spec_found = False
    queue_target_found = False
    if args.queue_scaling_cloud_pub_sub:
      _ValidateCloudPubSubResource(
          args.queue_scaling_cloud_pub_sub, 'topic')
      _ValidateCloudPubSubResource(
          args.queue_scaling_cloud_pub_sub, 'subscription')
      queue_spec_found = True

    if args.queue_scaling_acceptable_backlog_per_instance is not None:
      queue_target_found = True

    if queue_spec_found != queue_target_found:
      raise exceptions.ToolException(
          'Both queue specification and queue scaling target must be provided '
          'for queue-based autoscaling.')


def GetInstanceGroupManagerOrThrow(igm_ref, client):
  """Retrieves the given Instance Group Manager if possible.

  Args:
    igm_ref: reference to the Instance Group Manager.
    client: The compute client.
  Returns:
    Instance Group Manager object.
  """
  if hasattr(igm_ref, 'region'):
    service = client.apitools_client.regionInstanceGroupManagers
    request_type = service.GetRequestType('Get')
  if hasattr(igm_ref, 'zone'):
    service = client.apitools_client.instanceGroupManagers
    request_type = service.GetRequestType('Get')
  request = request_type(**igm_ref.AsDict())

  errors = []
  # Run throught the generator to actually make the requests and get potential
  # errors.
  igm_details = client.MakeRequests([(service, 'Get', request)],
                                    errors_to_collect=errors)

  if errors or len(igm_details) != 1:
    utils.RaiseException(errors, ResourceNotFoundException,
                         error_message='Could not fetch resource:')
  return igm_details[0]


def CreateZoneRef(resources, data):
  """Create zone reference from object with project and zone fields."""
  return resources.Parse(
      None,
      params={'project': data.project,
              'zone': data.zone},
      collection='compute.zones')


def CreateRegionRef(resources, data):
  """Create region reference from object with project and region fields."""
  return resources.Parse(
      None,
      params={'project': data.project,
              'region': data.region},
      collection='compute.regions')


def GroupByProject(locations):
  """Group locations by project field."""
  result = {}
  for location in locations or []:
    if location.project not in result:
      result[location.project] = []
    result[location.project].append(location)
  return result


def AutoscalersForLocations(zones, regions, client,
                            fail_when_api_not_supported=True):
  """Finds all Autoscalers defined for a given project and locations.

  Args:
    zones: iterable of target zone references
    regions: iterable of target region references
    client: The compute client.
    fail_when_api_not_supported: If true, raise tool exception if API does not
        support autoscaling.
  Returns:
    A list of Autoscaler objects.
  """
  # Errors is passed through library calls and modified with
  # (ERROR_CODE, ERROR_MESSAGE) tuples.
  errors = []

  # Explicit list() is required to unwind the generator and make sure errors
  # are detected at this level.
  requests = []
  for project, zones in GroupByProject(zones).iteritems():
    requests += lister.FormatListRequests(
        service=client.apitools_client.autoscalers,
        project=project,
        scopes=sorted(set([zone_ref.zone for zone_ref in zones])),
        scope_name='zone',
        filter_expr=None)

  if regions:
    if hasattr(client.apitools_client, 'regionAutoscalers'):
      for project, regions in GroupByProject(regions).iteritems():
        requests += lister.FormatListRequests(
            service=client.apitools_client.regionAutoscalers,
            project=project,
            scopes=sorted(set([region_ref.region for region_ref in regions])),
            scope_name='region',
            filter_expr=None)
    else:
      if fail_when_api_not_supported:
        errors.append((None, 'API does not support regional autoscaling'))

  autoscalers = client.MakeRequests(
      requests=requests,
      errors_to_collect=errors)

  if errors:
    utils.RaiseToolException(
        errors,
        error_message='Could not check if the Managed Instance Group is '
        'Autoscaled.')

  return autoscalers


def AutoscalersForMigs(migs, autoscalers):
  """Finds Autoscalers with target amongst given IGMs.

  Args:
    migs: List of triples (IGM name, scope type, location reference).
    autoscalers: A list of Autoscalers to search among.
  Returns:
    A list of all Autoscalers with target on mig_names list.
  """
  igm_url_regexes = []
  for (name, scope_type, location) in migs:
    igm_url_regexes.append(
        '/projects/{project}/{scopeType}/{scopeName}/'
        'instanceGroupManagers/{name}$'
        .format(project=location.project,
                scopeType=(scope_type + 's'),
                scopeName=getattr(location, scope_type),
                name=name))
  igm_url_regex = re.compile('(' + ')|('.join(igm_url_regexes) + ')')
  result = [
      autoscaler for autoscaler in autoscalers
      if igm_url_regex.search(autoscaler.target)
  ]
  return result


def AutoscalerForMig(mig_name, autoscalers, location, scope_type):
  """Finds Autoscaler targetting given IGM.

  Args:
    mig_name: Name of MIG targetted by Autoscaler.
    autoscalers: A list of Autoscalers to search among.
    location: Target location reference.
    scope_type: Target scope type.
  Returns:
    Autoscaler object for autoscaling the given Instance Group Manager or None
    when such Autoscaler does not exist.
  """
  autoscalers = AutoscalersForMigs(
      [(mig_name, scope_type, location)], autoscalers)
  if autoscalers:
    # For each Instance Group Manager there can be at most one Autoscaler having
    # the Manager as a target, so when one is found it can be returned as it is
    # the only one.
    if len(autoscalers) == 1:
      return autoscalers[0]
    else:
      raise exceptions.ToolException(
          'More than one Autoscaler with given target.')
  return None


def AddAutoscalersToMigs(migs_iterator,
                         client,
                         resources,
                         fail_when_api_not_supported=True):
  """Add Autoscaler to each IGM object if autoscaling is enabled for it."""
  def ParseZone(zone_link):
    return resources.Parse(
        zone_link,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.zones')

  def ParseRegion(region_link):
    return resources.Parse(
        region_link,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.regions')

  migs = list(migs_iterator)
  zones = set([ParseZone(mig['zone']) for mig in migs if 'zone' in mig])
  regions = set(
      [ParseRegion(mig['region']) for mig in migs if 'region' in mig])
  autoscalers = {}
  all_autoscalers = AutoscalersForLocations(
      zones=zones,
      regions=regions,
      client=client,
      fail_when_api_not_supported=fail_when_api_not_supported)

  for location in list(zones) + list(regions):
    autoscalers[location.Name()] = []

  for autoscaler in all_autoscalers:
    autoscaler_scope = None
    if autoscaler.zone is not None:
      autoscaler_scope = ParseZone(autoscaler.zone)
    if hasattr(autoscaler, 'region') and autoscaler.region is not None:
      autoscaler_scope = ParseRegion(autoscaler.region)
    if autoscaler_scope is not None:
      autoscalers.setdefault(autoscaler_scope.Name(), [])
      autoscalers[autoscaler_scope.Name()].append(autoscaler)

  for mig in migs:
    location = None
    scope_type = None
    if 'region' in mig:
      location = ParseRegion(mig['region'])
      scope_type = 'region'
    elif 'zone' in mig:
      location = ParseZone(mig['zone'])
      scope_type = 'zone'

    autoscaler = None
    if location and scope_type:
      autoscaler = AutoscalerForMig(
          mig_name=mig['name'],
          autoscalers=autoscalers[location.Name()],
          location=location,
          scope_type=scope_type)
    if autoscaler:
      mig['autoscaler'] = autoscaler
    yield mig


def _BuildCpuUtilization(args, messages):
  if args.target_cpu_utilization:
    return messages.AutoscalingPolicyCpuUtilization(
        utilizationTarget=args.target_cpu_utilization,
    )
  if args.scale_based_on_cpu:
    return messages.AutoscalingPolicyCpuUtilization()
  return None


def _BuildCustomMetricUtilizations(args, messages):
  """Builds custom metric utilization policy list from args.

  Args:
    args: command line arguments.
    messages: module containing message classes.
  Returns:
    AutoscalingPolicyCustomMetricUtilization list.
  """
  result = []
  if args.custom_metric_utilization:
    for custom_metric_utilization in args.custom_metric_utilization:
      result.append(
          messages.AutoscalingPolicyCustomMetricUtilization(
              utilizationTarget=custom_metric_utilization[
                  'utilization-target'],
              metric=custom_metric_utilization['metric'],
              utilizationTargetType=(
                  messages
                  .AutoscalingPolicyCustomMetricUtilization
                  .UtilizationTargetTypeValueValuesEnum(
                      custom_metric_utilization['utilization-target-type'],
                  )
              ),
          )
      )
  return result


def _BuildLoadBalancingUtilization(args, messages):
  if args.target_load_balancing_utilization:
    return messages.AutoscalingPolicyLoadBalancingUtilization(
        utilizationTarget=args.target_load_balancing_utilization,
    )
  if args.scale_based_on_load_balancing:
    return messages.AutoscalingPolicyLoadBalancingUtilization()
  return None


def _BuildQueueBasedScaling(args, messages):
  """Builds queue based scaling policy from args.

  Args:
    args: command line arguments.
    messages: module containing message classes.
  Returns:
    AutoscalingPolicyQueueBasedScaling message object or None.
  """
  if not ArgsSupportQueueScaling(args):
    return None

  queue_policy_dict = {}
  if args.queue_scaling_cloud_pub_sub:
    queue_policy_dict['cloudPubSub'] = (
        messages.AutoscalingPolicyQueueBasedScalingCloudPubSub(
            topic=args.queue_scaling_cloud_pub_sub['topic'],
            subscription=args.queue_scaling_cloud_pub_sub['subscription']))
  else:
    return None  # No queue spec.

  if args.queue_scaling_acceptable_backlog_per_instance is not None:
    queue_policy_dict['acceptableBacklogPerInstance'] = (
        args.queue_scaling_acceptable_backlog_per_instance)
  else:
    return None  # No queue target.

  if args.queue_scaling_single_worker_throughput is not None:
    queue_policy_dict['singleWorkerThroughputPerSec'] = (
        args.queue_scaling_single_worker_throughput)

  return messages.AutoscalingPolicyQueueBasedScaling(**queue_policy_dict)


def _BuildAutoscalerPolicy(args, messages):
  """Builds AutoscalingPolicy from args.

  Args:
    args: command line arguments.
    messages: module containing message classes.
  Returns:
    AutoscalingPolicy message object.
  """
  policy_dict = {
      'coolDownPeriodSec': args.cool_down_period,
      'cpuUtilization': _BuildCpuUtilization(args, messages),
      'customMetricUtilizations': _BuildCustomMetricUtilizations(args,
                                                                 messages),
      'loadBalancingUtilization': _BuildLoadBalancingUtilization(args,
                                                                 messages),
      'queueBasedScaling': _BuildQueueBasedScaling(args, messages),
      'maxNumReplicas': args.max_num_replicas,
      'minNumReplicas': args.min_num_replicas,
  }
  return messages.AutoscalingPolicy(
      **dict((key, value) for key, value in policy_dict.iteritems()
             if value is not None))  # Filter out None values.


def AdjustAutoscalerNameForCreation(autoscaler_resource):
  trimmed_name = autoscaler_resource.name[
      0:(_MAX_AUTOSCALER_NAME_LENGTH - _NUM_RANDOM_CHARACTERS_IN_AS_NAME - 1)]
  random_characters = [
      random.choice(string.lowercase + string.digits)
      for _ in range(_NUM_RANDOM_CHARACTERS_IN_AS_NAME)
  ]
  random_suffix = ''.join(random_characters)
  new_name = '{0}-{1}'.format(trimmed_name, random_suffix)
  autoscaler_resource.name = new_name


def BuildAutoscaler(args, messages, igm_ref, name):
  """Builds autoscaler message protocol buffer."""
  autoscaler = messages.Autoscaler(
      autoscalingPolicy=_BuildAutoscalerPolicy(args, messages),
      description=args.description,
      name=name,
      target=igm_ref.SelfLink(),
  )
  return autoscaler


def CreateAutohealingPolicies(messages, health_check, initial_delay):
  """Creates autohealing policy list from args."""
  if health_check is None and initial_delay is None:
    return []
  policy = messages.InstanceGroupManagerAutoHealingPolicy()
  if health_check:
    policy.healthCheck = health_check
  if initial_delay:
    policy.initialDelaySec = initial_delay
  return [policy]


def _GetInstanceTemplatesSet(*versions_lists):
  versions_set = set()
  for versions_list in versions_lists:
    versions_set.update(versions_list)
  return versions_set


def ValidateVersions(igm_info, new_versions, force=False):
  """Validates whether versions provided by user are consistent.

  Args:
    igm_info: instance group manager resource.
    new_versions: list of new versions.
    force: if true, we allow any combination of instance templates, as long as
    they are different. If false, only the following transitions are allowed:
    X -> Y, X -> (X, Y), (X, Y) -> X, (X, Y) -> Y, (X, Y) -> (X, Y)
  """
  if (len(new_versions) == 2
      and new_versions[0].instanceTemplate == new_versions[1].instanceTemplate):
    raise exceptions.ToolException(
        'Provided instance templates must be different.')
  if force:
    return

  # Only X -> Y, X -> (X, Y), (X, Y) -> X, (X, Y) -> Y, (X, Y) -> (X, Y)
  # are allowed in gcloud (unless --force)
  # Equivalently, at most two versions in old and new versions set union
  if igm_info.versions:
    igm_templates = [version.instanceTemplate for version in igm_info.versions]
  elif igm_info.instanceTemplate:
    igm_templates = [igm_info.instanceTemplate]
  else:
    raise exceptions.ToolException(
        'Either versions or instance template must be specified for '
        'managed instance group.')

  new_templates = [version.instanceTemplate for version in new_versions]
  version_count = len(_GetInstanceTemplatesSet(igm_templates, new_templates))
  if version_count > 2:
    raise exceptions.ToolException(
        'Update inconsistent with current state. '
        'The only allowed transitions between versions are: '
        'X -> Y, X -> (X, Y), (X, Y) -> X, (X, Y) -> Y, (X, Y) -> (X, Y). '
        'Please check versions templates or use --force.')


def AddAutoscaledPropertyToMigs(migs, client, resources):
  """Add Autoscaler information if Autoscaler is defined for the MIGs.

  Issue additional queries to detect if any given Instange Group Manager is
  a target of some autoscaler and add this information to in 'autoscaled'
  property.

  Args:
    migs: list of dicts, List of IGM resources converted to dictionaries
    client: a GCE client
    resources: a GCE resource registry

  Returns:
    Pair of:
    - boolean - True iff any autoscaler has an error
    - Copy of migs list with additional property 'autoscaled' set to 'No'/'Yes'/
    'Yes (*)' for each MIG depending on look-up result.
  """

  augmented_migs = []
  had_errors = False
  for mig in AddAutoscalersToMigs(
      migs_iterator=_ComputeInstanceGroupSize(migs, client, resources),
      client=client,
      resources=resources,
      fail_when_api_not_supported=False):
    if 'autoscaler' in mig and mig['autoscaler'] is not None:
      # status is present in autoscaler iff Autoscaler message has embedded
      # StatusValueValuesEnum defined.
      if (getattr(mig['autoscaler'], 'status', False) and mig['autoscaler']
          .status == client.messages.Autoscaler.StatusValueValuesEnum.ERROR):
        mig['autoscaled'] = 'yes (*)'
        had_errors = True
      else:
        mig['autoscaled'] = 'yes'
    else:
      mig['autoscaled'] = 'no'
    augmented_migs.append(mig)
  return (had_errors, augmented_migs)


def _ComputeInstanceGroupSize(items, client, resources):
  """Add information about Instance Group size."""
  errors = []
  zone_refs = [
      resources.Parse(
          mig['zone'],
          params={'project': properties.VALUES.core.project.GetOrFail},
          collection='compute.zones') for mig in items if 'zone' in mig
  ]
  region_refs = [
      resources.Parse(
          mig['region'],
          params={'project': properties.VALUES.core.project.GetOrFail},
          collection='compute.regions') for mig in items if 'region' in mig
  ]

  zonal_instance_groups = []
  for project, zone_refs in GroupByProject(zone_refs).iteritems():
    zonal_instance_groups.extend(
        lister.GetZonalResources(
            service=client.apitools_client.instanceGroups,
            project=project,
            requested_zones=set([zone.zone for zone in zone_refs]),
            filter_expr=None,
            http=client.apitools_client.http,
            batch_url=client.batch_url,
            errors=errors))

  regional_instance_groups = []
  if getattr(client.apitools_client, 'regionInstanceGroups', None):
    for project, region_refs in GroupByProject(region_refs).iteritems():
      regional_instance_groups.extend(
          lister.GetRegionalResources(
              service=client.apitools_client.regionInstanceGroups,
              project=project,
              requested_regions=set([region.region for region in region_refs]),
              filter_expr=None,
              http=client.apitools_client.http,
              batch_url=client.batch_url,
              errors=errors))

  instance_groups = zonal_instance_groups + regional_instance_groups
  instance_group_uri_to_size = {ig.selfLink: ig.size for ig in instance_groups}

  if errors:
    utils.RaiseToolException(errors)

  for item in items:
    self_link = item['selfLink']
    gm_self_link = self_link.replace('/instanceGroupManagers/',
                                     '/instanceGroups/')

    item['size'] = str(instance_group_uri_to_size.get(gm_self_link, ''))
    yield item


def GetHealthCheckUri(resources, args, health_check_parser=None):
  """Creates health check reference from args."""
  if args.health_check:
    ref = health_check_parser.ResolveAsResource(args, resources)
    return ref.SelfLink()
  if args.http_health_check:
    return resources.Parse(
        args.http_health_check,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.httpHealthChecks').SelfLink()
  if args.https_health_check:
    return resources.Parse(
        args.https_health_check,
        params={'project': properties.VALUES.core.project.GetOrFail},
        collection='compute.httpsHealthChecks').SelfLink()
