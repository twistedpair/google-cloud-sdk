# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for ml versions commands."""
from googlecloudsdk.api_lib.ml import operations
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import progress_tracker


def ParseVersion(model, version):
  """Parses a model/version ID into a version resource object."""
  return resources.REGISTRY.Parse(
      version, params={'modelsId': model},
      collection='ml.projects.models.versions')


def WaitForOpMaybe(client, op, async_=False, msg='Waiting'):
  """Waits for an operation if async_ flag is on.

  Args:
    client: apitools API client for the Cloud ML service
    op: Cloud ML operation, the operation to poll
    async_: bool, whether to wait for the operation or return immediately
    msg: str, the message to display while waiting for the operation

  Returns:
    The result of the operation if async_ is true, or the Operation message
        otherwise
  """
  if async_:
    return op
  with progress_tracker.ProgressTracker(msg):
    op = operations.WaitForOperation(client.projects_operations, op)
  return op.response
