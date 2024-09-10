# -*- coding: utf-8 -*-
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Run gRPC client. This class is automatically generated."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import gapic_util
from googlecloudsdk.generated_clients.gapic_clients import run_v2


class GapicWrapperClient(object):
  """Run async client."""
  types = run_v2.types

  def __init__(self, credentials, **kwargs):
    """
    Instantiates the GapicWrapperClient for run_v2.

    Args:
      credentials: google.auth.credentials.Credentials, the credentials to use.
      **kwargs: Additional kwargs to pass to gapic.MakeClient.

    Returns:
        GapicWrapperClient
    """
    self.credentials = credentials
    self.builds = gapic_util.MakeAsyncClient(
        run_v2.services.builds.async_client.BuildsAsyncClient,
        credentials, **kwargs)
    self.executions = gapic_util.MakeAsyncClient(
        run_v2.services.executions.async_client.ExecutionsAsyncClient,
        credentials, **kwargs)
    self.jobs = gapic_util.MakeAsyncClient(
        run_v2.services.jobs.async_client.JobsAsyncClient,
        credentials, **kwargs)
    self.revisions = gapic_util.MakeAsyncClient(
        run_v2.services.revisions.async_client.RevisionsAsyncClient,
        credentials, **kwargs)
    self.services = gapic_util.MakeAsyncClient(
        run_v2.services.services.async_client.ServicesAsyncClient,
        credentials, **kwargs)
    self.tasks = gapic_util.MakeAsyncClient(
        run_v2.services.tasks.async_client.TasksAsyncClient,
        credentials, **kwargs)
    self.worker = gapic_util.MakeAsyncClient(
        run_v2.services.worker_pools.async_client.WorkerPoolsAsyncClient,
        credentials, **kwargs)
