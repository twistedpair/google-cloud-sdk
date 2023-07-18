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
"""workbench instances api helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum
from googlecloudsdk.api_lib.workbench import util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources

_RESERVATION_AFFINITY_KEY = 'compute.googleapis.com/reservation-name'


def CreateInstanceListRequest(args, messages):
  parent = util.GetParentFromArgs(args)
  return messages.NotebooksProjectsLocationsInstancesListRequest(parent=parent)


def GetInstanceURI(resource):
  instance = resources.REGISTRY.ParseRelativeName(
      resource.name, collection='notebooks.projects.locations.instances')
  return instance.SelfLink()


class OperationType(enum.Enum):
  CREATE = (log.CreatedResource, 'created')
  UPDATE = (log.UpdatedResource, 'updated')
  UPGRADE = (log.UpdatedResource, 'upgraded')
  ROLLBACK = (log.UpdatedResource, 'rolled back')
  DELETE = (log.DeletedResource, 'deleted')
  RESET = (log.ResetResource, 'reset')


def HandleLRO(operation,
              args,
              instance_service,
              release_track,
              operation_type=OperationType.UPDATE):
  """Handles Long-running Operations for both cases of async.

  Args:
    operation: The operation to poll.
    args: ArgParse instance containing user entered arguments.
    instance_service: The service to get the resource after the long-running
      operation completes.
    release_track: base.ReleaseTrack object.
    operation_type: Enum value of type OperationType indicating the kind of
      operation to wait for.

  Raises:
    apitools.base.py.HttpError: if the request returns an HTTP error

  Returns:
    The Instance resource if synchronous, else the Operation Resource.
  """
  logging_method = operation_type.value[0]
  if args.async_:
    logging_method(
        util.GetOperationResource(operation.name, release_track),
        kind='notebooks instance {0}'.format(args.instance),
        is_async=True)
    return operation
  else:
    response = util.WaitForOperation(
        operation,
        'Waiting for operation on Instance [{}] to be {} with [{}]'.format(
            args.instance, operation_type.value[1], operation.name),
        service=instance_service,
        release_track=release_track,
        is_delete=(operation_type.value[1] == 'deleted'))
    logging_method(
        util.GetOperationResource(operation.name, release_track),
        kind='notebooks instance {0}'.format(args.instance),
        is_async=False)
    return response
