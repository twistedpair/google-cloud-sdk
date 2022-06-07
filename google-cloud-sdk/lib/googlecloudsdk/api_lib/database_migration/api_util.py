# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import uuid

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
import six


def GetApiVersion(release_track):
  """Returns the API version based on the release track."""
  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha2'
  return 'v1'


def GetClientInstance(release_track, no_http=False):
  return apis.GetClientInstance('datamigration', GetApiVersion(release_track),
                                no_http=no_http)


def GetMessagesModule(release_track):
  return apis.GetMessagesModule('datamigration', GetApiVersion(release_track))


def GetResourceParser(release_track):
  resource_parser = resources.Registry()
  resource_parser.RegisterApiByName('datamigration',
                                    GetApiVersion(release_track))
  return resource_parser


def ParentRef(project, location):
  """Get the resource name of the parent collection.

  Args:
    project: the project of the parent collection.
    location: the GCP region of the membership.

  Returns:
    the resource name of the parent collection in the format of
    `projects/{project}/locations/{location}`.
  """

  return 'projects/{}/locations/{}'.format(project, location)


def GenerateRequestId():
  """Generates a UUID to use as the request ID.

  Returns:
    string, the 40-character UUID for the request ID.
  """
  return six.text_type(uuid.uuid4())


def HandleLRO(client, result_operation, service):
  """Uses the waiter library to handle LRO synchronous execution."""
  op_resource = resources.REGISTRY.ParseRelativeName(
      result_operation.name,
      collection='datamigration.projects.locations.operations')
  poller = waiter.CloudOperationPoller(
      service,
      client.projects_locations_operations)
  try:
    waiter.WaitFor(
        poller, op_resource,
        'Waiting for operation [{}] to complete'.format(
            result_operation.name))
  except waiter.TimeoutError:
    log.status.Print(
        'The operations may still be underway remotely and may still succeed. You may check the operation status for the following operation  [{}]'
        .format(result_operation.name))
    return
