# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Threat Detection utils."""
import enum

from googlecloudsdk.api_lib.run import k8s_object
from googlecloudsdk.core import resources


@enum.unique
class ThreatDetectionState(enum.Enum):
  """Threat Detection state."""

  DISABLED = enum.auto()
  ENABLED = enum.auto()
  REQUIRE_REDEPLOY = enum.auto()


def PrintThreatDetectionState(state: ThreatDetectionState) -> str:
  """Prints the threat detection state."""
  if state == ThreatDetectionState.DISABLED:
    return ''
  if state == ThreatDetectionState.ENABLED:
    return 'Enabled'
  if state == ThreatDetectionState.REQUIRE_REDEPLOY:
    return 'Redeploy revision to enable'
  raise ValueError(f'Unknown threat detection state: {state}')


def UpdateThreatDetectionState(service, client):
  """Util to update the threat detection state of a service.

  When the threat detection state is enabled on a service, this function ensures
  that it is also enabled on the latest revision. If not, it updates the
  service's threat_detection_state state to prompt the user to redeploy.

  Args:
    service: the service to update the threat detection state for.
    client: a connected serverless operations client to fetch the latest
      revision of the service.
  """
  if not service:
    return

  if not _HasThreatDetectionEnabled(service):
    service.threat_detection_state = ThreatDetectionState.DISABLED
    return

  service.threat_detection_state = ThreatDetectionState.ENABLED

  if not service.latest_created_revision:
    return

  revision_ref = resources.REGISTRY.Parse(
      service.latest_created_revision,
      params={'namespacesId': service.metadata.namespace},
      collection='run.namespaces.revisions',
  )
  revision = client.GetRevision(revision_ref)
  if revision and not _HasThreatDetectionEnabled(revision):
    service.threat_detection_state = ThreatDetectionState.REQUIRE_REDEPLOY


def _HasThreatDetectionEnabled(resource):
  """Returns true if threat detection is enabled on the resource."""
  return (
      resource.annotations.get(
          k8s_object.THREAT_DETECTION_ANNOTATION, ''
      ).lower()
      == 'true'
  )
