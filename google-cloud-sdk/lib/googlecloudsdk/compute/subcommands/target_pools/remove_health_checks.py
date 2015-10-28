# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for removing health checks from target pools."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils


class RemoveHealthChecks(base_classes.NoOutputAsyncMutator):
  """Remove an HTTP health check from a target pool.

  *{command}* is used to remove an HTTP health check
  from a target pool. Health checks are used to determine
  the health status of instances in the target pool. For more
  information on health checks and load balancing, see
  link:https://cloud.google.com/compute/docs/load-balancing-and-autoscaling/[].
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--http-health-check',
        help=('Specifies an HTTP health check object to remove from the '
              'target pool.'),
        metavar='HEALTH_CHECK',
        completion_resource='httpHealthChecks',
        required=True)

    utils.AddRegionFlag(
        parser,
        resource_type='target pool',
        operation_type='remove health checks from')

    parser.add_argument(
        'name',
        completion_resource='targetPools',
        help=('The name of the target pool from which to remove the '
              'health check.'))

  @property
  def service(self):
    return self.compute.targetPools

  @property
  def method(self):
    return 'RemoveHealthCheck'

  @property
  def resource_type(self):
    return 'targetPools'

  def CreateRequests(self, args):
    http_health_check_ref = self.CreateGlobalReference(
        args.http_health_check, resource_type='httpHealthChecks')

    target_pool_ref = self.CreateRegionalReference(args.name, args.region)
    request = self.messages.ComputeTargetPoolsRemoveHealthCheckRequest(
        region=target_pool_ref.region,
        project=self.project,
        targetPool=target_pool_ref.Name(),
        targetPoolsRemoveHealthCheckRequest=(
            self.messages.TargetPoolsRemoveHealthCheckRequest(
                healthChecks=[self.messages.HealthCheckReference(
                    healthCheck=http_health_check_ref.SelfLink())])))

    return [request]
