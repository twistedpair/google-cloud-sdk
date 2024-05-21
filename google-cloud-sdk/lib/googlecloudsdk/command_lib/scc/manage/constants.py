# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Management API gcloud constants."""

import dataclasses
from typing import Dict, List, Optional

# TODO: b/308433842 - This can be deleted once gcloud python migration to
# 3.12 is complete
# pylint: disable=g-importing-member, g-import-not-at-top, g-bad-import-order
# pyformat: disable
import sys
if sys.version_info >= (3, 11):
  from enum import StrEnum
else:
  # in 3.11+, using the below class in an f-string would put the enum
  # name instead of its value
  from enum import Enum

  class StrEnum(str, Enum):
    pass
# pyformat: enable
# pylint: enable=g-importing-member, g-import-not-at-top, g-bad-import-order

# DELETE UP TO HERE


class CustomModuleType(StrEnum):
  SHA = 'securityHealthAnalyticsCustomModules'
  ETD = 'eventThreatDetectionCustomModules'
  EFFECTIVE_ETD = 'effectiveEventThreatDetectionCustomModules'
  EFFECTIVE_SHA = 'effectiveSecurityHealthAnalyticsCustomModules'


SERVICE_RESOURCE_PLURAL_NAME = 'securityCenterServices'


@dataclasses.dataclass(frozen=True)
class SecurityCenterService:
  """Dataclass that reprsesents a Security Center Service."""

  name: str
  abbreviation: Optional[str] = None

  def __str__(self) -> str:
    if self.abbreviation is not None:
      return f'{self.name} (can be abbreviated as {self.abbreviation})'
    else:
      return self.name

  def __eq__(self, other: 'SecurityCenterService') -> bool:
    if isinstance(other, SecurityCenterService):
      is_same_name = self.name == other.name
      is_same_abbreviation = (
          self.abbreviation == other.abbreviation
          and self.abbreviation is not None
      )

      return is_same_name or is_same_abbreviation
    else:
      return False


def make_service_inventory(
    services: List[SecurityCenterService],
) -> Dict[str, SecurityCenterService]:
  """Maps a list of SecurityCenterService objects to an immutable dictionary.

  The dictionary will contain a mapping between each service name and service
  object as well as service abbreviation to service object if the service has
  an abbreviation.

  Args:
    services: list of service objects to add to the dictionary.

  Returns:
    an immutable dictionary mapping service names and abbreviations to services.

  Raises:
    KeyError: if there are duplicate entries for any service name or
    abbreviation.
  """
  for i in range(len(services)):
    for j in range(i + 1, len(services)):
      if services[i] == services[j]:
        raise KeyError(
            f'Duplicate entries in service inventory: {services[i]} at index'
            f' {i} and {services[j]} at index {j} in service inventory. Both'
            ' service names and abbreviations must be unique.'
        )

  abbreviated_services = [
      service for service in services if service.abbreviation is not None
  ]

  names_to_services = {service.name: service for service in services}
  abbreviations_to_services = {
      service.abbreviation: service for service in abbreviated_services
  }

  return {**names_to_services, **abbreviations_to_services}

SUPPORTED_SERVICES = (
    SecurityCenterService('security-health-analytics', abbreviation='sha'),
    SecurityCenterService('event-threat-detection', abbreviation='etd'),
    SecurityCenterService('container-threat-detection', abbreviation='ctd'),
    SecurityCenterService('vm-threat-detection', abbreviation='vmtd'),
    SecurityCenterService('web-security-scanner', abbreviation='wss'),
)

SERVICE_INVENTORY: Dict[str, SecurityCenterService] = make_service_inventory(
    SUPPORTED_SERVICES
)
