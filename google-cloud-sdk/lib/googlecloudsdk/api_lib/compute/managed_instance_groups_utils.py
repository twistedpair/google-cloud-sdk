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
from googlecloudsdk.api_lib.compute import path_simplifier
from googlecloudsdk.api_lib.compute import request_helper
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions


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
  parser.add_argument('--cool-down-period', type=arg_parsers.Duration(),
                      help='Number of seconds Autoscaler will wait between '
                      'resizing collection. Note: The Autoscaler waits '
                      '10 minutes before scaling down, the value entered here '
                      'is in addition to the initial 10 minute period.')
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
  custom_metric_utilization = parser.add_argument(
      '--custom-metric-utilization',
      type=arg_parsers.ArgDict(
          spec={
              'metric': str,
              'utilization-target': float,
              'utilization-target-type': str,
          },
      ),
      action='append',
      help=('Autoscaler will maintain the target value of a Google Cloud '
            'Monitoring metric.'),
  )
  custom_metric_utilization.detailed_help = """
   Adds a target metric value for the to the Autoscaler.

   *metric*::: Protocol-free URL of a Google Cloud Monitoring metric.

   *utilization-target*::: Value of the metric Autoscaler will aim to maintain
   (greater than 0.0).

   *utilization-target-type*::: How target is expressed. Valid values: {0}.
  """.format(', '.join(_ALLOWED_UTILIZATION_TARGET_TYPES))

  if queue_scaling_enabled:
    cloud_pub_sub_spec = parser.add_argument(
        '--queue-scaling-cloud-pub-sub',
        type=arg_parsers.ArgDict(
            spec={
                'topic': str,
                'subscription': str,
            },
        ),
        help='Scaling based on Cloud Pub/Sub queuing system.',
    )
    cloud_pub_sub_spec.detailed_help = """
     Specifies queue-based scaling based on a Cloud Pub/Sub queuing system.
     Both topic and subscription are required.

     *topic*::: Topic specification. Can be just a name or a partial URL
     (starting with "projects/..."). Topic must belong to the same project as
     Autoscaler.

     *subscription*::: Subscription specification. Can be just a name or a
     partial URL (starting with "projects/..."). Subscription must belong to the
     same project as Autoscaler and must be connected to the specified topic.
    """
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


def AutoscalersForZones(zones, project, compute, http, batch_url,
                        fail_when_api_not_supported=True):
  """Finds all Autoscalers defined for a given project and zones."""

  return AutoscalersForLocations(
      zones=zones,
      regions=None,
      project=project,
      compute=compute,
      http=http,
      batch_url=batch_url,
      fail_when_api_not_supported=fail_when_api_not_supported)


def AutoscalersForLocations(zones, regions,
                            project, compute, http, batch_url,
                            fail_when_api_not_supported=True):
  """Finds all Autoscalers defined for a given project and locations.

  Args:
    zones: target zones
    regions: target regions
    project: project owning resources.
    compute: module representing compute api.
    http: communication channel.
    batch_url: batch url.
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
  if zones:
    requests += lister.FormatListRequests(
        service=compute.autoscalers,
        project=project,
        scopes=zones,
        scope_name='zone',
        filter_expr=None)

  if regions:
    if hasattr(compute, 'regionAutoscalers'):
      requests += lister.FormatListRequests(
          service=compute.regionAutoscalers,
          project=project,
          scopes=regions,
          scope_name='region',
          filter_expr=None)
    else:
      if fail_when_api_not_supported:
        errors.append((None, 'API does not support regional autoscaling'))

  autoscalers = list(request_helper.MakeRequests(
      requests=requests,
      http=http,
      batch_url=batch_url,
      errors=errors))

  if errors:
    utils.RaiseToolException(
        errors,
        error_message='Could not check if the Managed Instance Group is '
        'Autoscaled.')

  return autoscalers


def AutoscalersForMigs(migs, autoscalers, project):
  """Finds Autoscalers with target amongst given IGMs.

  Args:
    migs: List of triples (IGM name, scope type, scope name).
    autoscalers: A list of Autoscalers to search among.
    project: Project owning resources.
  Returns:
    A list of all Autoscalers with target on mig_names list.
  """
  igm_url_regexes = []
  for (name, scope_type, scope_name) in migs:
    igm_url_regexes.append(
        '/projects/{project}/{scopeType}/{scopeName}/'
        'instanceGroupManagers/{name}$'
        .format(project=project,
                scopeType=(scope_type + 's'),
                scopeName=scope_name,
                name=name))
  igm_url_regex = re.compile('(' + ')|('.join(igm_url_regexes) + ')')
  result = [
      autoscaler for autoscaler in autoscalers
      if igm_url_regex.search(autoscaler.target)
  ]
  return result


def AutoscalerForMig(mig_name, autoscalers, project, scope_name, scope_type):
  """Finds Autoscaler targetting given IGM.

  Args:
    mig_name: Name of MIG targetted by Autoscaler.
    autoscalers: A list of Autoscalers to search among.
    project: Project owning resources.
    scope_name: Target scope.
    scope_type: Target scope type.
  Returns:
    Autoscaler object for autoscaling the given Instance Group Manager or None
    when such Autoscaler does not exist.
  """
  autoscalers = AutoscalersForMigs(
      [(mig_name, scope_type, scope_name)], autoscalers, project)
  if autoscalers:
    # For each Instance Group Manager there can be at most one Autoscaler having
    # the Manager as a target, so when one is found it can be returned as it is
    # the only one.
    if len(autoscalers) == 1:
      return autoscalers[0]
    else:
      raise exceptions.ToolException(
          'More than one Autoscaler with given targe.')
  return None


def AddAutoscalersToMigs(migs_iterator, project, compute, http,
                         batch_url, fail_when_api_not_supported=True):
  """Add Autoscaler to each IGM object if autoscaling is enabled for it."""
  migs = list(migs_iterator)
  zone_names = set([path_simplifier.Name(mig['zone'])
                    for mig in migs if 'zone' in mig])
  region_names = set([path_simplifier.Name(mig['region'])
                      for mig in migs if 'region' in mig])
  autoscalers = {}
  all_autoscalers = AutoscalersForLocations(
      zones=zone_names,
      regions=region_names,
      project=project,
      compute=compute,
      http=http,
      batch_url=batch_url,
      fail_when_api_not_supported=fail_when_api_not_supported)

  for scope_name in list(zone_names) + list(region_names):
    autoscalers[scope_name] = []

  for autoscaler in all_autoscalers:
    autoscaler_scope = None
    if autoscaler.zone is not None:
      autoscaler_scope = path_simplifier.Name(autoscaler.zone)
    if hasattr(autoscaler, 'region') and autoscaler.region is not None:
      autoscaler_scope = path_simplifier.Name(autoscaler.region)
    if autoscaler_scope is not None:
      autoscalers.setdefault(autoscaler_scope, [])
      autoscalers[autoscaler_scope].append(autoscaler)

  for mig in migs:
    scope_name = None
    scope_type = None
    if 'region' in mig:
      scope_name = path_simplifier.Name(mig['region'])
      scope_type = 'region'
    elif 'zone' in mig:
      scope_name = path_simplifier.Name(mig['zone'])
      scope_type = 'zone'

    autoscaler = None
    if scope_name and scope_type:
      autoscaler = AutoscalerForMig(
          mig_name=mig['name'],
          autoscalers=autoscalers[scope_name],
          project=project,
          scope_name=scope_name,
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


def BuildAutoscaler(args, messages, igm_ref, name, zone=None, region=None):
  """Builds autoscaler message protocol buffer."""
  autoscaler = messages.Autoscaler(
      autoscalingPolicy=_BuildAutoscalerPolicy(args, messages),
      description=args.description,
      name=name,
      target=igm_ref.SelfLink(),
  )
  if zone:
    autoscaler.zone = zone
  if region:
    autoscaler.region = region
  return autoscaler


def AddAutohealingArgs(parser):
  """Adds autohealing-related commandline arguments to parser."""
  health_check_group = parser.add_mutually_exclusive_group()
  health_check_group.add_argument(
      '--http-health-check',
      help=('Specifies the HTTP health check object used for autohealing '
            'instances in this group.'))
  health_check_group.add_argument(
      '--https-health-check',
      help=('Specifies the HTTPS health check object used for autohealing '
            'instances in this group.'))
  initial_delay = parser.add_argument(
      '--initial-delay',
      type=arg_parsers.Duration(),
      help=('Specifies the length of the period during which the instance '
            'is known to be initializing and should not be autohealed even '
            'if unhealthy.'))
  initial_delay.detailed_help = """\
      Specifies the length of the period during which the instance is known to
      be initializing and should not be autohealed even if unhealthy.
      Valid units for this flag are ``s'' for seconds, ``m'' for minutes and
      ``h'' for hours. If no unit is specified, seconds is assumed. This value
      cannot be greater than 1 hour.
      """


def CreateAutohealingPolicies(resources, messages, args):
  """Creates autohealing policy list from args."""
  if hasattr(args, 'http_health_check'):  # alpha or beta
    if args.http_health_check or args.https_health_check or args.initial_delay:
      policy = messages.InstanceGroupManagerAutoHealingPolicy()
      if args.http_health_check:
        health_check_ref = resources.Parse(
            args.http_health_check,
            collection='compute.httpHealthChecks')
        policy.healthCheck = health_check_ref.SelfLink()
      elif args.https_health_check:
        health_check_ref = resources.Parse(
            args.https_health_check,
            collection='compute.httpsHealthChecks')
        policy.healthCheck = health_check_ref.SelfLink()
      if args.initial_delay:
        policy.initialDelaySec = args.initial_delay
      return [policy]
  return []


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
