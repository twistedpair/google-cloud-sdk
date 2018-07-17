# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""API library for access context manager zones."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.accesscontextmanager import util
from googlecloudsdk.api_lib.util import waiter

from googlecloudsdk.core import resources as core_resources


class Client(object):
  """High-level API client for access context access zones."""

  def __init__(self, client=None, messages=None):
    self.client = client or util.GetClient()
    self.messages = messages or self.client.MESSAGES_MODULE

  def Get(self, zone_ref):
    return self.client.accessPolicies_accessZones.Get(
        self.messages.AccesscontextmanagerAccessPoliciesAccessZonesGetRequest(
            name=zone_ref.RelativeName()))

  def Patch(self, zone_ref, description=None, title=None, zone_type=None,
            resources=None, restricted_services=None,
            unrestricted_services=None, levels=None):
    """Patch an access zone.

    Any non-None fields will be included in the update mask.

    Args:
      zone_ref: resources.Resource, reference to the zone to patch
      description: str, description of the zone or None if not updating
      title: str, title of the zone or None if not updating
      zone_type: ZoneTypeValueValuesEnum, zone type enum value for
        the level or None if not updating
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

    Returns:
      AccessZone, the updated access zone
    """
    zone = self.messages.AccessZone()
    update_mask = []
    if description is not None:
      update_mask.append('description')
      zone.description = description
    if title is not None:
      update_mask.append('title')
      zone.title = title
    if zone_type is not None:
      update_mask.append('zoneType')
      zone.zoneType = zone_type
    if resources is not None:
      update_mask.append('resources')
      zone.resources = resources
    if unrestricted_services is not None:
      update_mask.append('unrestrictedServices')
      zone.unrestrictedServices = unrestricted_services
    if restricted_services is not None:
      update_mask.append('restrictedServices')
      zone.restrictedServices = restricted_services
    if levels is not None:
      update_mask.append('accessLevels')
      zone.accessLevels = [l.RelativeName() for l in levels]
    update_mask.sort()  # For ease-of-testing

    m = self.messages
    request_type = m.AccesscontextmanagerAccessPoliciesAccessZonesPatchRequest
    request = request_type(
        accessZone=zone,
        name=zone_ref.RelativeName(),
        updateMask=','.join(update_mask),
    )
    operation = self.client.accessPolicies_accessZones.Patch(request)

    poller = util.OperationPoller(self.client.accessPolicies_accessZones,
                                  self.client.operations, zone_ref)
    operation_ref = core_resources.REGISTRY.Parse(
        operation.name, collection='accesscontextmanager.operations')
    return waiter.WaitFor(
        poller, operation_ref,
        'Waiting for PATCH operation [{}]'.format(operation_ref.Name()))
