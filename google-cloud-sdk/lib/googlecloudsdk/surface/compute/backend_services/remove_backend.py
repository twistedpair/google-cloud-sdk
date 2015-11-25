# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for removing a backend from a backend service."""
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.third_party.py27 import py27_copy as copy


class RemoveBackend(base_classes.ReadWriteCommand):
  """Remove a backend from a backend service.

  *{command}* is used to remove a backend from a backend
  service.

  Before removing a backend, it is a good idea to "drain" the
  backend first. A backend can be drained by setting its
  capacity scaler to zero through 'gcloud compute
  backend-services edit'.
  """

  @staticmethod
  def Args(parser):
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument(
        '--group',
        help=('The name of the legacy instance group '
              '(deprecated resourceViews API) to remove. '
              'Use --instance-group flag instead.'))
    g.add_argument(
        '--instance-group',
        help='The name or URI of the instance group to remove.')

    utils.AddZoneFlag(
        parser,
        resource_type='instance group',
        operation_type='remove from the backend service')

    parser.add_argument(
        'name',
        help='The name of the backend service.')

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

    group_uri = group_ref.SelfLink()

    backend_idx = None
    for i, backend in enumerate(existing.backends):
      if group_uri == backend.group:
        backend_idx = i

    if backend_idx is None:
      raise exceptions.ToolException(
          'Backend [{0}] in zone [{1}] is not a backend of backend service '
          '[{2}].'.format(args.group, args.zone, args.name))
    else:
      replacement.backends.pop(backend_idx)

    return replacement
