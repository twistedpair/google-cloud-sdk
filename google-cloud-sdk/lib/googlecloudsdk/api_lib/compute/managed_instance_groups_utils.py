# Copyright 2014 Google Inc. All Rights Reserved.
"""Common utility functions for Autoscaler processing."""

import argparse
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
from googlecloudsdk.third_party.apis.compute.alpha import compute_alpha_messages

# TODO(jbartosik): Use generated list of possible enum values.
_ALLOWED_UTILIZATION_TARGET_TYPES = sorted(
    compute_alpha_messages.AutoscalingPolicyCustomMetricUtilization
    .UtilizationTargetTypeValueValuesEnum.to_dict().keys())
_MAX_AUTOSCALER_NAME_LENGTH = 63
# 4 character chosen from between lowercase letters and numbers give >1.6M
# possibilities with no more than 100 Autoscalers in one Zone and Project
# so probability that adding an autoscaler will fail because of name conflict
# is about 6e-5.
_NUM_RANDOM_CHARACTERS_IN_AS_NAME = 4


class ResourceNotFoundException(exceptions.ToolException):
  pass


def AddAutoscalerArgs(parser):
  """Adds commandline arguments to parser."""
  parser.add_argument('--cool-down-period', type=arg_parsers.Duration(),
                      help='Number of seconds Autoscaler will wait between '
                      'resizing collection.')
  parser.add_argument('--description', help='Notes about Autoscaler.')
  parser.add_argument('--min-num-replicas',
                      type=arg_parsers.BoundedInt(0, sys.maxint),
                      help='Minimum number of replicas Autoscaler will set.')
  parser.add_argument('--max-num-replicas',
                      type=arg_parsers.BoundedInt(0, sys.maxint), required=True,
                      help='Maximum number of replicas Autoscaler will set.')
  parser.add_argument('--scale-based-on-cpu',
                      action='store_true',
                      help='Use autoscaling based on cpu utilization.')
  parser.add_argument('--scale-based-on-load-balancing',
                      action='store_true',
                      help=('Use autoscaling based on load balancing '
                            'utilization.'))
  parser.add_argument('--target-cpu-utilization', type=float,
                      help='CPU utilization level Autoscaler will aim to '
                      'maintain (0.0 to 1.0).')
  parser.add_argument('--target-load-balancing-utilization', type=float,
                      help='Load balancing utilization level Autoscaler will '
                      'aim to maintain (greater than 0.0).')
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
   Adds a target metric value for the to the Autoscaler.

   *metric*::: Protocol-free URL of a Google Cloud Monitoring metric.

   *utilization-target*::: Value of the metric Autoscaler will aim to maintain
   (greater than 0.0).

   *utilization-target-type*::: How target is expressed. Valid values: {0}.
  """.format(', '.join(_ALLOWED_UTILIZATION_TARGET_TYPES))


def ValidateAutoscalerArgs(args):
  """Validates args."""
  if args.min_num_replicas and args.max_num_replicas:
    if args.min_num_replicas > args.max_num_replicas:
      raise exceptions.InvalidArgumentException(
          '--max-num-replicas', 'can\'t be less than min num replicas.')

  if args.scale_based_on_cpu or args.target_cpu_utilization:
    if args.target_cpu_utilization:
      if args.target_cpu_utilization > 1.:
        raise exceptions.InvalidArgumentException(
            '--target-cpu-utilization', 'can\'t be grater than 1.')
      if args.target_cpu_utilization < 0.:
        raise exceptions.InvalidArgumentException(
            '--target-cpu-utilization', 'can\'t be lesser than 0.')

  if args.custom_metric_utilization:
    for custom_metric_utilization in args.custom_metric_utilization:
      for field in ('utilization-target', 'metric', 'utilization-target-type'):
        if field not in custom_metric_utilization:
          raise exceptions.InvalidArgumentException(
              '--custom-metric-utilization', field + ' not present.')
      if custom_metric_utilization['utilization-target'] < 0:
        raise exceptions.InvalidArgumentException(
            '--custom-metric-utilization utilization-target', 'less than 0.')

  if (args.scale_based_on_load_balancing or
      args.target_load_balancing_utilization):
    if (args.target_load_balancing_utilization and
        args.target_load_balancing_utilization <= 0):
      raise exceptions.InvalidArgumentException(
          '--target-load-balancing-utilization', 'less than 0.')


def AssertInstanceGroupManagerExists(igm_ref, project, messages, compute,
                                     http, batch_url):
  """Makes sure the given Instance Group Manager exists.

  Args:
    igm_ref: reference to the Instance Group Manager.
    project: project owning resources.
    messages: module containing message classes.
    compute: module representing compute api.
    http: communication channel.
    batch_url: batch url.
  """
  request = messages.ComputeInstanceGroupManagersGetRequest(project=project)
  request.zone = igm_ref.zone
  request.instanceGroupManager = igm_ref.Name()

  errors = []
  # Run throught the generator to actually make the requests and get potential
  # errors.
  igm_details = list(request_helper.MakeRequests(
      requests=[(compute.instanceGroupManagers, 'Get', request)],
      http=http,
      batch_url=batch_url,
      errors=errors,
      custom_get_requests=None,
  ))

  if errors or len(igm_details) != 1:
    utils.RaiseException(errors, ResourceNotFoundException,
                         error_message='Could not fetch resource:')


def AutoscalersForZones(zones, project, compute, http, batch_url,
                        fail_when_api_not_supported=True):
  """Finds all Autoscalers defined for a given project and zones.

  Args:
    zones: target zones
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

  if hasattr(compute, 'autoscalers'):
    # Explicit list() is required to unwind the generator and make sure errors
    # are detected at this level.
    autoscalers = list(lister.GetZonalResources(
        service=compute.autoscalers,
        project=project,
        requested_zones=zones,
        http=http,
        batch_url=batch_url,
        errors=errors,
        filter_expr=None,
    ))
  else:
    autoscalers = []
    if fail_when_api_not_supported:
      errors.append((None, 'API does not support autoscaling'))

  if errors:
    utils.RaiseToolException(
        errors,
        error_message='Could not check if the Managed Instance Group is '
        'Autoscaled.')

  return autoscalers


def AutoscalersForMigs(migs, autoscalers, project):
  """Finds Autoscalers with target amongst given IGMs.

  Args:
    migs: List of pairs (IGM name, zone).
    autoscalers: A list of Autoscalers to search among.
    project: Project owning resources.
  Returns:
    A list of all Autoscalers with target on mig_names list.
  """
  igm_url_regexes = []
  for (name, zone) in migs:
    igm_url_regexes.append(
        '/projects/{project}/zones/{zone}/instanceGroupManagers/{name}'
        .format(project=project, zone=zone, name=name))
  igm_url_regex = re.compile('(' + ')|('.join(igm_url_regexes) + ')')
  result = [
      autoscaler for autoscaler in autoscalers
      if igm_url_regex.search(autoscaler.target)
  ]
  return result


def AutoscalerForMig(mig_name, autoscalers, project, zone):
  """Finds Autoscaler targetting given IGM.

  Args:
    mig_name: Name of MIG targetted by Autoscaler.
    autoscalers: A list of Autoscalers to search among.
    project: Project owning resources.
    zone: Target zone.
  Returns:
    Autoscaler object for autoscaling the given Instance Group Manager or None
    when such Autoscaler does not exist.
  """
  autoscalers = AutoscalersForMigs([(mig_name, zone)], autoscalers, project)
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
                    for mig in migs])
  autoscalers = {}
  for zone_name in zone_names:
    autoscalers[zone_name] = AutoscalersForZones(
        zones=[zone_name],
        project=project,
        compute=compute,
        http=http,
        batch_url=batch_url,
        fail_when_api_not_supported=fail_when_api_not_supported)
  for mig in migs:
    zone_name = path_simplifier.Name(mig['zone'])
    autoscaler = AutoscalerForMig(
        mig_name=mig['name'],
        autoscalers=autoscalers[zone_name],
        project=project,
        zone=zone_name)
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
  """Builds customMetricUtilizations list from args.

  Args:
    args: command line arguments.
    messages: module containing message classes.
  Returns:
    customMetricUtilizations list.
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


def _BuildAutoscalerPolicy(args, messages):
  return messages.AutoscalingPolicy(
      coolDownPeriodSec=args.cool_down_period,
      cpuUtilization=_BuildCpuUtilization(args, messages),
      customMetricUtilizations=_BuildCustomMetricUtilizations(args, messages),
      loadBalancingUtilization=_BuildLoadBalancingUtilization(args, messages),
      maxNumReplicas=args.max_num_replicas,
      minNumReplicas=args.min_num_replicas,
  )


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


def BuildAutoscaler(args, messages, autoscaler_ref, igm_ref):
  return messages.Autoscaler(
      autoscalingPolicy=_BuildAutoscalerPolicy(args, messages),
      description=args.description,
      name=autoscaler_ref.Name(),
      target=igm_ref.SelfLink(),
      zone=autoscaler_ref.zone,
  )


def AddAutohealingArgs(parser, help_hidden=False):
  """Adds autohealing-related commandline arguments to parser."""
  health_check_group = parser.add_mutually_exclusive_group()
  if not help_hidden:
    health_check_group.add_argument(
        '--http-health-check',
        help=('Specifies the HTTP health check object used for autohealing '
              'instances in this group.'))
    health_check_group.add_argument(
        '--https-health-check',
        help=('Specifies the HTTPS health check object used for autohealing '
              'instances in this group.'))
  else:
    # TODO(witek, b/22996767): Remove this branch after autohealing beta launch.
    health_check_group.add_argument(
        '--http-health-check',
        help=argparse.SUPPRESS)
    health_check_group.add_argument(
        '--https-health-check',
        help=argparse.SUPPRESS)


def CreateAutohealingPolicies(cmd, args):
  """Creates autohealing policy list from args."""
  if hasattr(args, 'http_health_check'):  # alpha or beta
    if args.http_health_check or args.https_health_check:
      if args.http_health_check:
        health_check_ref = cmd.CreateGlobalReference(
            args.http_health_check,
            resource_type='httpHealthChecks')
      else:
        health_check_ref = cmd.CreateGlobalReference(
            args.https_health_check,
            resource_type='httpsHealthChecks')
      return [
          cmd.messages.InstanceGroupManagerAutoHealingPolicy(
              healthCheck=health_check_ref.SelfLink())]
  return []
