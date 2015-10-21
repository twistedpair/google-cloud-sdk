# Copyright 2014 Google Inc. All Rights Reserved.
"""Common utility functions for Autoscaler processing.

This is meant for use by the `gcloud alpha compute autoscaler` command group.
For `gcloud compute instance-groups managed`, see
`managed_instance_groups_utils.py`.
"""

import argparse
import json
import time

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.console import console_io

# TODO(jbartosik): Use generated list of possible enum values.
ALLOWED_UTILIZATION_TARGET_TYPES = ['GAUGE', 'DELTA_PER_SECOND',
                                    'DELTA_PER_MINUTE']


def WaitForOperation(autoscaler_client, operation_ref, message):
  """Waits for operation to finish, displays a progress bar.

  Args:
    autoscaler_client: Client used to fetch operation.
    operation_ref: Operation for completion of which the function will wait.
    message: message Displayed with progress bar.

  Returns:
    True iff operation was completed. False otherwise.

  Forked from //cloud/sdk/sql/util.py
  """
  with console_io.ProgressTracker(message, autotick=False) as pt:
    while True:
      op = autoscaler_client.zoneOperations.Get(operation_ref.Request())
      pt.Tick()
      # TODO(jbartosik): Make sure we recognize operation failures as well.
      if op.status == 'DONE':
        return True
      if op.status == 'UNKNOWN':
        return False
      time.sleep(2)


def AddAutoscalerArgs(parser):
  """Adds commandline arguments to parser."""
  parser.add_argument('--scale-based-on-load-balancing',
                      action='store_true',
                      help=('Sets autoscaling based on load balancing '
                            'utilization.'),)
  parser.add_argument('--scale-based-on-cpu',
                      action='store_true',
                      help='Sets autoscaling based on cpu utilization.',)
  parser.add_argument('--target', help='The managed instance group to scale, '
                      'either the fully-qualified URL or the managed instance '
                      'group name.',
                      required=True,)
  parser.add_argument('--cool-down-period', type=arg_parsers.Duration(),
                      help='The number of seconds to wait after a virtual '
                      'machine has been started before the autoscaler starts '
                      'collecting information from it. This accounts '
                      'for the amount of time it may take for a virtual '
                      'machine to initialize, during which the collected usage '
                      'information is not reliable for autoscaling. It is '
                      'recommended that you set this to at least the amount of '
                      'time it takes for your virtual machine and applications '
                      'to start.',)
  parser.add_argument('--description', help='An optional description for this '
                      'autoscaler.',)
  parser.add_argument('--min-num-replicas', type=int,
                      help='Sets the minimum number of instances the '
                      'autoscaler will maintain. The autoscaler will never '
                      'scale the number of instances below this number. If not '
                      'provided, the default is 2.',)
  parser.add_argument('--max-num-replicas', type=int,
                      help='Sets the maximum number of instances the '
                      'autoscaler will maintain for the managed instance '
                      'group.',
                      required=True,)
  parser.add_argument('--target-cpu-utilization', type=float,
                      help='The CPU utilization the autoscaler will aim to '
                      'maintain. Must be a float between 0.0 to 1.0, '
                      'exclusive',)
  parser.add_argument('--custom-metric', type=str, help='Sets a Google Cloud '
                      'Monitoring instance metric to scale based on (see '
                      'https://developers.google.com/cloud-monitoring/metrics'
                      ').',)
  parser.add_argument('--target-custom-metric-utilization', type=float,
                      help='The custom metric level the autoscaler will aim to '
                      'maintain. This can be a float that is greater than '
                      '0.0.',)
  parser.add_argument('--custom-metric-utilization-target-type', type=str,
                      help='The type of your custom metric. Choose from '
                      'the following: {0}.'.format(
                          ', '.join(ALLOWED_UTILIZATION_TARGET_TYPES)),)
  parser.add_argument('--target-load-balancer-utilization', type=float,
                      help='The HTTP load balancer utilization level the '
                      'autoscaler will maintain. This must be a float greater '
                      'than 0.0.',)
  custom_metric_utilization = parser.add_argument(
      '--custom-metric-utilization',
      type=arg_parsers.ArgDict(
          spec={
              'metric': str,
              'utilization-target': float,
              'utilization-target-type': str
          },
      ),
      # pylint:disable=protected-access
      action=arg_parsers.FloatingListValuesCatcher(argparse._AppendAction),
      help=('Adds target value of a Google Cloud Monitoring metric Autoscaler '
            'will aim to maintain.'),
      metavar='PROPERTY=VALUE',
  )
  custom_metric_utilization.detailed_help = """
  Adds target value of a Google Cloud Monitoring metric Autoscaler will aim to
  maintain.

  *metric*::: Protocol-free URL of a Google Cloud Monitoring metric.

  *utilization-target*::: Value of the metric Autoscaler will aim to maintain
  on the average (greater than 0.0).

  *utilization-target-type*::: How target is expressed. You can choose from the
  following: {0}.
  """.format(', '.join(ALLOWED_UTILIZATION_TARGET_TYPES))


_FLAGS_CONFLICTING_WITH_CUSTOM_METRIC_UTILIZATION = [
    '--custom-metric',
    '--target-custom-metric-utilization',
    '--custom-metric-utilization-target-type',
]


def _ValidateUtilizationTargetType(utilization_target_type, identifier):
  if utilization_target_type not in ALLOWED_UTILIZATION_TARGET_TYPES:
    raise exceptions.ToolException(
        'Unexpected value for {0}: '
        '{1!r}, expected one of: {2}'.format(
            identifier,
            utilization_target_type,
            ', '.join(ALLOWED_UTILIZATION_TARGET_TYPES)),)


def _ValidateArgs(args):
  """Validates args."""
  if args.min_num_replicas and args.min_num_replicas < 0:
    raise exceptions.ToolException('min num replicas can\'t be negative.')

  if args.max_num_replicas and args.max_num_replicas < 0:
    raise exceptions.ToolException('max num replicas can\'t be negative.')

  if args.min_num_replicas and args.max_num_replicas:
    if args.min_num_replicas > args.max_num_replicas:
      raise exceptions.ToolException(
          'max num replicas can\'t be less than min num replicas.')

  if args.scale_based_on_cpu or args.target_cpu_utilization:
    if args.target_cpu_utilization:
      if args.target_cpu_utilization > 1.:
        raise exceptions.ToolException(
            'target cpu utilization can\'t be grater than 1.')
      if args.target_cpu_utilization < 0.:
        raise exceptions.ToolException(
            'target cpu utilization can\'t be lesser than 0.')

  if (args.custom_metric or args.target_custom_metric_utilization or
      args.custom_metric_utilization_target_type):
    if (args.custom_metric and args.target_custom_metric_utilization and
        args.custom_metric_utilization_target_type):
      if args.target_custom_metric_utilization <= 0.:
        raise exceptions.ToolException(
            'target custom metric utilization can\'t be lesser than 0.')
      _ValidateUtilizationTargetType(
          args.custom_metric_utilization_target_type,
          '--custom-metric-utilization-target-type',
      )
    else:
      raise exceptions.ToolException(
          'you need to provide all three: --custom-metric, '
          '--target-custom-metric-utilization and '
          '--custom-metric-utilization-target-type.',)

  if (args.scale_based_on_load_balancing or
      args.target_load_balancer_utilization):
    if (args.target_load_balancer_utilization and
        args.target_load_balancer_utilization <= 0):
      raise exceptions.ToolException(
          'target load balancer utilization can\'t be lesser than 0.',)

  if args.custom_metric_utilization:
    for flag in _FLAGS_CONFLICTING_WITH_CUSTOM_METRIC_UTILIZATION:
      if getattr(args, flag[2:].replace('-', '_')):
        raise exceptions.ToolException(
            'You can\'t provide both {0} and {1} flags.'
            .format('--custom-metric-utilization', flag))


def _PolicyFromArgs(args, messages):
  """Build autoscaling policy from args."""
  result = messages.AutoscalingPolicy()
  if args.cool_down_period:
    result.coolDownPeriodSec = args.cool_down_period
  if args.max_num_replicas:
    result.maxNumReplicas = args.max_num_replicas
  if args.min_num_replicas:
    result.minNumReplicas = args.min_num_replicas
  if args.custom_metric:
    result.customMetricUtilizations = [
        messages.AutoscalingPolicyCustomMetricUtilization()]
    result.customMetricUtilizations[0].utilizationTarget = (
        args.target_custom_metric_utilization)
    result.customMetricUtilizations[0].metric = (args.custom_metric)
    (result.customMetricUtilizations[0].utilizationTargetType) = (
        args.custom_metric_utilization_target_type)
  if args.target_cpu_utilization:
    result.cpuUtilization = (messages.AutoscalingPolicyCpuUtilization())
    result.cpuUtilization.utilizationTarget = (args.target_cpu_utilization)
  if (args.scale_based_on_load_balancing or
      args.target_load_balancer_utilization):
    result.loadBalancingUtilization = (
        messages.AutoscalingPolicyLoadBalancingUtilization())
    if args.target_load_balancer_utilization:
      result.loadBalancingUtilization.utilizationTarget = (
          args.target_load_balancer_utilization)
  if args.custom_metric_utilization:
    result.customMetricUtilizations = []
    for custom_metric_utilization in args.custom_metric_utilization:
      result.customMetricUtilizations += [
          messages.AutoscalingPolicyCustomMetricUtilization(
              utilizationTarget=custom_metric_utilization['utilization-target'],
              metric=custom_metric_utilization['metric'],
              utilizationTargetType=custom_metric_utilization[
                  'utilization-target-type'],
          )
      ]
  return result


def GetErrorMessage(error):
  content_obj = json.loads(error.content)
  return content_obj.get('error', {}).get('message', '')


def PrepareAutoscaler(args, messages, resources):
  """Validate args and build autoscaler from them."""
  _ValidateArgs(args)

  result = messages.Autoscaler()
  if args.description:
    result.description = args.description
  if args.target:
    # Target will be validated by Autoscaler frontend so there is no need to
    # check if provided URL is valid.
    if args.target.startswith('http://') or args.target.startswith('https://'):
      url = args.target
    else:
      igm_ref = resources.Parse(
          args.target, collection='replicapool.instanceGroupManagers')
      url = igm_ref.SelfLink()
    result.target = url

  result.autoscalingPolicy = _PolicyFromArgs(args, messages)
  return result
