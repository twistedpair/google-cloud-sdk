# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""API library for VPC Service Controls Service Perimeters."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.accesscontextmanager import util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import log
from googlecloudsdk.core import resources as core_resources


def _CreateServiceRestriction(restriction_message_type, mask_prefix,
                              enable_restriction, allowed_services):
  """Returns a service restriction message and its update mask."""
  if allowed_services is None and enable_restriction is None:
    return None, []

  message = restriction_message_type()
  update_mask = []

  if allowed_services is not None:
    message.allowedServices = allowed_services
    update_mask.append('allowedServices')

  if enable_restriction is not None:
    message.enableRestriction = enable_restriction
    update_mask.append('enableRestriction')

  return message, ['{}.{}'.format(mask_prefix, item) for item in update_mask]


def _CreateServicePerimeterConfig(messages, mask_prefix,
                                  include_unrestricted_services, resources,
                                  restricted_services, unrestricted_services,
                                  levels, vpc_allowed_services,
                                  enable_vpc_accessible_services):
  """Returns a ServicePerimeterConfig and its update mask."""

  config = messages.ServicePerimeterConfig()
  mask = []
  if resources is not None:
    mask.append('resources')
    config.resources = resources
  if include_unrestricted_services and unrestricted_services is not None:
    mask.append('unrestrictedServices')
    config.unrestrictedServices = unrestricted_services
  if restricted_services is not None:
    mask.append('restrictedServices')
    config.restrictedServices = restricted_services
  if levels is not None:
    mask.append('accessLevels')
    config.accessLevels = [l.RelativeName() for l in levels]

  if (enable_vpc_accessible_services is not None or
      vpc_allowed_services is not None):
    config.vpcAccessibleServices, mask_updates = _CreateServiceRestriction(
        messages.VpcAccessibleServices,
        'vpcAccessibleServices',
        enable_restriction=enable_vpc_accessible_services,
        allowed_services=vpc_allowed_services)
    mask += mask_updates

  if not mask:
    return None, []

  return config, ['{}.{}'.format(mask_prefix, item) for item in mask]


class Client(object):
  """High-level API client for VPC Service Controls Service Perimeters."""

  def __init__(self, client=None, messages=None, version='v1'):
    self.client = client or util.GetClient(version=version)
    self.messages = messages or self.client.MESSAGES_MODULE
    self.include_unrestricted_services = {
        'v1': False,
        'v1alpha': True,
        'v1beta': True
    }[version]

  def Get(self, zone_ref):
    return self.client.accessPolicies_servicePerimeters.Get(
        self.messages
        .AccesscontextmanagerAccessPoliciesServicePerimetersGetRequest(
            name=zone_ref.RelativeName()))

  def Patch(self,
            perimeter_ref,
            description=None,
            title=None,
            perimeter_type=None,
            resources=None,
            restricted_services=None,
            unrestricted_services=None,
            levels=None,
            vpc_allowed_services=None,
            enable_vpc_accessible_services=None,
            apply_to_dry_run_config=False,
            clear_dry_run=False):
    """Patch a service perimeter.

    Args:
      perimeter_ref: resources.Resource, reference to the perimeter to patch
      description: str, description of the zone or None if not updating
      title: str, title of the zone or None if not updating
      perimeter_type: PerimeterTypeValueValuesEnum type enum value for the level
        or None if not updating
      resources: list of str, the names of resources (for now, just
        'projects/...') in the zone or None if not updating.
      restricted_services: list of str, the names of services
        ('example.googleapis.com') that *are* restricted by the access zone or
        None if not updating.
      unrestricted_services: list of str, the names of services
        ('example.googleapis.com') that *are not* restricted by the access zone
        or None if not updating.
      levels: list of Resource, the access levels (in the same policy) that must
        be satisfied for calls into this zone or None if not updating.
      vpc_allowed_services: list of str, the names of services
        ('example.googleapis.com') that *are* allowed to be made within the
        access zone, or None if not updating.
      enable_vpc_accessible_services: bool, whether to restrict the set of APIs
        callable within the access zone, or None if not updating.
      apply_to_dry_run_config: When true, the configuration will be place in the
        'spec' field instead of the 'status' field of the Service Perimeter.
      clear_dry_run: When true, the ServicePerimeterConfig field for dry-run
        (i.e. 'spec') will be cleared and dryRun will be set to False.

    Returns:
      ServicePerimeter, the updated Service Perimeter.
    """
    m = self.messages
    perimeter = m.ServicePerimeter()

    update_mask = []

    if description is not None:
      update_mask.append('description')
      perimeter.description = description
    if title is not None:
      update_mask.append('title')
      perimeter.title = title
    if perimeter_type is not None:
      update_mask.append('perimeterType')
      perimeter.perimeterType = perimeter_type

    if not clear_dry_run:
      mask_prefix = 'status' if not apply_to_dry_run_config else 'spec'

      config, config_mask_additions = _CreateServicePerimeterConfig(
          m, mask_prefix, self.include_unrestricted_services, resources,
          restricted_services, unrestricted_services, levels,
          vpc_allowed_services, enable_vpc_accessible_services)

      if not apply_to_dry_run_config:
        perimeter.status = config
      else:
        perimeter.useExplicitDryRunSpec = True
        perimeter.spec = config

      update_mask += config_mask_additions

      if apply_to_dry_run_config and config_mask_additions:
        update_mask.append('useExplicitDryRunSpec')

    else:
      update_mask.append('spec')
      update_mask.append('useExplicitDryRunSpec')
      perimeter.spec = None
      perimeter.useExplicitDryRunSpec = False

    update_mask.sort()  # For ease-of-testing

    # No update mask implies no fields were actually edited, so this is a no-op.
    if not update_mask:
      log.warning(
          'The update specified results in an identical resource. Skipping request.'
      )
      return perimeter

    request_type = (
        m.AccesscontextmanagerAccessPoliciesServicePerimetersPatchRequest)
    request = request_type(
        servicePerimeter=perimeter,
        name=perimeter_ref.RelativeName(),
        updateMask=','.join(update_mask),
    )

    operation = self.client.accessPolicies_servicePerimeters.Patch(request)
    poller = util.OperationPoller(self.client.accessPolicies_servicePerimeters,
                                  self.client.operations, perimeter_ref)
    operation_ref = core_resources.REGISTRY.Parse(
        operation.name, collection='accesscontextmanager.operations')
    return waiter.WaitFor(
        poller, operation_ref,
        'Waiting for PATCH operation [{}]'.format(operation_ref.Name()))
