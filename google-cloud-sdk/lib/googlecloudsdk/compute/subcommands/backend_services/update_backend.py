# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for updating a backend in a backend service."""
import copy


from googlecloudsdk.api_lib.compute import backend_services_utils
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apis.compute.v1 import compute_v1_messages


class UpdateBackend(base_classes.ReadWriteCommand):
  """Update an existing backend in a backend service."""

  @staticmethod
  def Args(parser):
    backend_services_utils.AddUpdatableBackendArgs(parser, compute_v1_messages)

    parser.add_argument(
        'name',
        help='The name of the backend service to update.')

  @property
  def service(self):
    return self.compute.backendServices

  @property
  def resource_type(self):
    return 'backendServices'

  def CreateReference(self, args):
    return self.CreateGlobalReference(args.name)

  def GetGetRequest(self, args):
    return (self.service,
            'Get',
            self.messages.ComputeBackendServicesGetRequest(
                backendService=self.ref.Name(),
                project=self.project))

  def GetSetRequest(self, args, replacement, existing):
    return (self.service,
            'Update',
            self.messages.ComputeBackendServicesUpdateRequest(
                backendService=self.ref.Name(),
                backendServiceResource=replacement,
                project=self.project))

  def Modify(self, args, existing):
    replacement = copy.deepcopy(existing)

    group_ref = None
    if args.group is not None:
      log.warn('The --group flag is deprecated and will be removed. '
               'Please use --instance-group instead.')
      group_ref = self.CreateZonalReference(
          args.group, args.zone, resource_type='zoneViews')
    else:
      group_ref = self.CreateZonalReference(
          args.instance_group, args.zone, resource_type='instanceGroups')

    backend_to_update = None
    for backend in replacement.backends:
      if group_ref.SelfLink() == backend.group:
        backend_to_update = backend

    if not backend_to_update:
      raise exceptions.ToolException(
          'No backend with name [{0}] in zone [{1}] is part of the backend '
          'service [{2}].'.format(
              group_ref.Name(), group_ref.zone, self.ref.Name()))

    if args.description:
      backend_to_update.description = args.description
    elif args.description is not None:
      backend_to_update.description = None

    if args.balancing_mode:
      backend_to_update.balancingMode = (
          self.messages.Backend.BalancingModeValueValuesEnum(
              args.balancing_mode))

      # If the balancing mode is being changed to RATE, we must clear
      # the max utilization field, otherwise the server will reject
      # the request.
      if (backend_to_update.balancingMode ==
          self.messages.Backend.BalancingModeValueValuesEnum.RATE):
        backend_to_update.maxUtilization = None

    # Now, we set the parameters that control load balancing. The user
    # can still provide a control parameter that is incompatible with
    # the balancing mode; like the add-backend subcommand, we leave it
    # to the server to perform validation on this.
    #
    # TODO(user): In the future, we probably should do this
    # validation client-side, so we can produce better error messages.
    if args.max_utilization is not None:
      backend_to_update.maxUtilization = args.max_utilization

    if args.max_rate is not None:
      backend_to_update.maxRate = args.max_rate
      backend_to_update.maxRatePerInstance = None

    if args.max_rate_per_instance is not None:
      backend_to_update.maxRate = None
      backend_to_update.maxRatePerInstance = args.max_rate_per_instance

    if args.capacity_scaler is not None:
      backend_to_update.capacityScaler = args.capacity_scaler

    return replacement

  def Run(self, args):
    if not any([
        args.description is not None,
        args.balancing_mode,
        args.max_utilization is not None,
        args.max_rate is not None,
        args.max_rate_per_instance is not None,
        args.capacity_scaler is not None,
    ]):
      raise exceptions.ToolException('At least one property must be modified.')

    return super(UpdateBackend, self).Run(args)


UpdateBackend.detailed_help = {
    'brief': 'Update an existing backend in a backend service',
    'DESCRIPTION': """
        *{command}* updates a backend that is part of a backend
        service. This is useful for changing the way a backend
        behaves. Example changes that can be made include changing the
        load balancing policy and ``draining'' a backend by setting
        its capacity scaler to zero.

        Backends are named by their associated instances groups, and one
        of the ``--group'' or ``--instance-group'' flags is required to
        identify the backend that you are modifying.  You cannot "change"
        the instance group associated with a backend, but you can accomplish
        something similar with ``backend-services remove-backend'' and
        ``backend-services add-backend''.

        'gcloud compute backend-services edit' can also be used to
        update a backend if the use of a text editor is desired.
        """,
}
