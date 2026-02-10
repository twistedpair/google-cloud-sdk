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

"""Utility functions for the Hypercompute Cluster API."""

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import resources


API_NAME = 'hypercomputecluster'
ALPHA_API_VERSION = 'v1alpha'
TRACK_TO_API_VERSION = {base.ReleaseTrack.ALPHA: ALPHA_API_VERSION}


OPERATIONS_COLLECTION = 'hypercomputecluster.projects.locations.operations'


def GetApiVersion(release_track=base.ReleaseTrack.GA) -> str:
  """Returns the API version for the given release track."""
  if release_track not in TRACK_TO_API_VERSION:
    raise ValueError(f'Unsupported release track: {release_track}')
  return TRACK_TO_API_VERSION[release_track]


def GetReleaseTrack(api_version=ALPHA_API_VERSION) -> base.ReleaseTrack:
  """Returns the API version for the given release track."""
  if api_version not in TRACK_TO_API_VERSION.values():
    raise ValueError(
        f'Unsupported API version for release track: {api_version}'
    )
  return [
      key for key, value in TRACK_TO_API_VERSION.items() if value == api_version
  ][0]


def GetClientInstance(release_track=base.ReleaseTrack.GA):
  """Returns the client instance for the given release track."""
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(API_NAME, api_version)


def GetMessagesModule(release_track=base.ReleaseTrack.GA):
  """Returns the messages module for the given release track."""
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(API_NAME, api_version)


def WaitForOperation(client, operation, message: str, max_wait_sec: int):
  """Waits for the given operation to complete."""
  operation_ref = resources.REGISTRY.ParseRelativeName(
      operation.name,
      collection=OPERATIONS_COLLECTION,
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


def GetCluster(client, args, messages):
  """Returns the cluster message for the cluster name derived from the args."""
  cluster_ref = args.CONCEPTS.cluster.Parse()
  try:
    return client.projects_locations_clusters.Get(
        messages.HypercomputeclusterProjectsLocationsClustersGetRequest(
            name=cluster_ref.RelativeName()
        )
    )
  except apitools_exceptions.HttpError as error:
    raise calliope_exceptions.HttpException(error)
