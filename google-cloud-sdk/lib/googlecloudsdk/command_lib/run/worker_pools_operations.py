# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Allows you to write surfaces in terms of logical Cloud Run V2 WorkerPools API operations."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from google.api_core import exceptions


class WorkerPoolsOperations(object):
  """Client used to communicate with the actual Cloud Run V2 WorkerPools API."""

  def __init__(self, client):
    self._client = client

  def GetWorkerPool(self, worker_pool_ref):
    """Get the WorkerPool.

    Args:
      worker_pool_ref: Resource, WorkerPool to get.

    Returns:
      A WorkerPool object.
    """
    worker_pools = self._client.worker
    get_request = self._client.types.GetWorkerPoolRequest(
        name=worker_pool_ref.RelativeName()
    )
    try:
      # TODO(b/357135595): Add and record durations metrics
      return worker_pools.get_worker_pool(get_request)
    except exceptions.NotFound:
      return None
