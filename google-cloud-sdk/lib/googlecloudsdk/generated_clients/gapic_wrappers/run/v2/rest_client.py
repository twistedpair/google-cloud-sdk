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
  """Run client."""
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
    self.builds = gapic_util.MakeRestClient(
        run_v2.services.builds.client.BuildsClient,
        credentials, **kwargs)
    self.executions = gapic_util.MakeRestClient(
        run_v2.services.executions.client.ExecutionsClient,
        credentials, **kwargs)
    self.jobs = gapic_util.MakeRestClient(
        run_v2.services.jobs.client.JobsClient,
        credentials, **kwargs)
    self.revisions = gapic_util.MakeRestClient(
        run_v2.services.revisions.client.RevisionsClient,
        credentials, **kwargs)
    self.services = gapic_util.MakeRestClient(
        run_v2.services.services.client.ServicesClient,
        credentials, **kwargs)
    self.tasks = gapic_util.MakeRestClient(
        run_v2.services.tasks.client.TasksClient,
        credentials, **kwargs)
    self.worker = gapic_util.MakeRestClient(
        run_v2.services.worker_pools.client.WorkerPoolsClient,
        credentials, **kwargs)
