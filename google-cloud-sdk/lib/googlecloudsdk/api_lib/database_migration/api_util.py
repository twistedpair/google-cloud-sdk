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
"""Cloud Database Migration API utilities."""

import pprint
import uuid

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

_API_NAME = 'datamigration'


def GetApiVersion(release_track: base.ReleaseTrack) -> str:
  """Returns the API version based on the release track."""
  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha2'
  return 'v1'


def GetClientInstance(release_track: base.ReleaseTrack, no_http: bool = False):
  return apis.GetClientInstance(
      api_name=_API_NAME,
      api_version=GetApiVersion(release_track),
      no_http=no_http,
  )


def GetMessagesModule(release_track: base.ReleaseTrack):
  return apis.GetMessagesModule(
      api_name=_API_NAME,
      api_version=GetApiVersion(release_track),
  )


def GetResourceParser(release_track: base.ReleaseTrack) -> resources.Registry:
  resource_parser = resources.Registry()
  resource_parser.RegisterApiByName(
      api_name=_API_NAME,
      api_version=GetApiVersion(release_track),
  )
  return resource_parser


def ParentRef(project: str, location: str) -> str:
  """Get the resource name of the parent collection.

  Args:
    project: the project of the parent collection.
    location: the GCP region of the membership.

  Returns:
    the resource name of the parent collection in the format of
    `projects/{project}/locations/{location}`.
  """
  return f'projects/{project}/locations/{location}'


def GenerateRequestId() -> str:
  """Generates a UUID to use as the request ID.

  Returns:
    string, the 40-character UUID for the request ID.
  """
  return str(uuid.uuid4())


def HandleLRO(
    client,
    result_operation,
    service,
    no_resource: bool = False,
) -> None:
  """Uses the waiter library to handle LRO synchronous execution."""
  if no_resource:
    poller = waiter.CloudOperationPollerNoResources(
        operation_service=client.projects_locations_operations,
    )
  else:
    poller = CloudDmsOperationPoller(
        result_service=service,
        operation_service=client.projects_locations_operations,
    )

  try:
    waiter.WaitFor(
        poller,
        resources.REGISTRY.ParseRelativeName(
            relative_name=result_operation.name,
            collection='datamigration.projects.locations.operations',
        ),
        f'Waiting for operation [{result_operation.name}] to complete',
    )
  except waiter.TimeoutError:
    log.status.Print(
        'The operations may still be underway remotely and may still succeed.'
        ' You may check the operation status for the following operation'
        f' [{result_operation.name}]',
    )


class CloudDmsOperationPoller(waiter.CloudOperationPoller):
  """Manages a longrunning Operations for cloud DMS.

  It is needed since we want to return the entire error rather than just the
  error message as the base class does.

  See https://cloud.google.com/speech/reference/rpc/google.longrunning
  """

  def IsDone(self, operation) -> bool:
    """Overrides."""
    if operation.done and operation.error:
      op_error = encoding.MessageToDict(operation.error)
      raise waiter.OperationError('\n' + pprint.pformat(op_error))
    return operation.done
