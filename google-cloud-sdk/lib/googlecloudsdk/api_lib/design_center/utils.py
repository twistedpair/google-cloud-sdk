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
"""Util for Design Center Cloud SDK."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding as apitools_encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


VERSION_MAP = {
    base.ReleaseTrack.ALPHA: 'v1alpha',
    # TODO(b/430098857): Add GA release track
    # base.ReleaseTrack.BETA: 'v1beta',
    # base.ReleaseTrack.GA: 'v1',
}

OPERATIONS_COLLECTION = 'designcenter.projects.locations.operations'


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetMessagesModule('designcenter', api_version)


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  api_version = VERSION_MAP.get(release_track)
  return apis.GetClientInstance('designcenter', api_version)


def GetLocationRef(args):
  """Returns a location reference."""
  location_ref = args.CONCEPTS.location.Parse()
  if not location_ref.Name():
    raise exceptions.InvalidArgumentException(
        'location', 'location id must be non-empty.'
    )
  return location_ref


def GetProjectRef():
  """Returns a project reference."""
  return resources.REGISTRY.Parse(
      properties.VALUES.core.project.GetOrFail(),
      collection='designcenter.projects',
  )


def GetSpaceRef(args):
  """Returns a space reference."""
  space_ref = args.CONCEPTS.space.Parse()
  if not space_ref.Name():
    raise exceptions.InvalidArgumentException(
        'space', 'space id must be non-empty.'
    )
  return space_ref


def MakeGetUriFunc(collection, release_track=base.ReleaseTrack.ALPHA):
  """Returns a function which turns a resource into a uri."""

  def _GetUri(resource):
    api_version = VERSION_MAP.get(release_track)
    result = resources.Registry().ParseRelativeName(
        resource.name, collection=collection, api_version=api_version
    )
    return result.SelfLink()

  return _GetUri


class EmbeddedResultOperationPoller(waiter.CloudOperationPoller):
  """Poller for operations with result embedded in operation.response."""

  def __init__(self, operation_service):
    super(EmbeddedResultOperationPoller, self).__init__(None, operation_service)

  def GetRequestType(self, request_name):
    """Overrides."""
    return self.operation_service.GetRequestType(request_name)

  def GetResult(self, operation):
    """Overrides."""
    if operation.response:
      return apitools_encoding.MessageToPyValue(operation.response)
    return None


def WaitForOperation(
    client,
    operation,
    message: str,
    max_wait_sec: int,
    release_track=base.ReleaseTrack.ALPHA,
):
  """Waits for the given operation to complete."""
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection=OPERATIONS_COLLECTION,
      api_version=VERSION_MAP.get(release_track),
  )

  return waiter.WaitFor(
      poller=waiter.CloudOperationPoller(
          client.projects_locations_operations,
          client.projects_locations_operations,
      ),
      operation_ref=operation_ref,
      message=message,
      max_wait_ms=max_wait_sec * 1000,
  )


def GetGoogleCatalogProjectId() -> str:
  """Returns the project ID for Google Catalog based on API endpoint."""
  endpoint_override = (
      properties.VALUES.api_endpoint_overrides.designcenter.Get()
  )
  # universe_domain will always be non empty with default value 'googleapis.com'
  universe_domain = properties.VALUES.core.universe_domain.Get()
  if (
      endpoint_override
      and f'autopush-designcenter.sandbox.{universe_domain}'
      in endpoint_override
  ):
    return 'gcpdesigncenter-autopush'
  if (
      endpoint_override
      and f'staging-designcenter.sandbox.{universe_domain}'
      in endpoint_override
  ):
    return 'gcpdesigncenter-staging'
  return 'gcpdesigncenter'


def WaitForOperationWithEmbeddedResult(
    client,
    operation,
    message: str,
    max_wait_sec: int,
    release_track=base.ReleaseTrack.ALPHA,
):
  """Waits for an operation to complete, where the result is embedded in the operation response."""
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection=OPERATIONS_COLLECTION,
      api_version=VERSION_MAP.get(release_track),
  )

  poller = EmbeddedResultOperationPoller(
      client.projects_locations_operations
  )

  return waiter.WaitFor(
      poller=poller,
      operation_ref=operation_ref,
      message=message,
      max_wait_ms=max_wait_sec * 1000,
  )
