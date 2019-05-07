# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Utility functions for managing GCE OS Configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from enum import Enum
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base


class InstanceDetailsStates(Enum):
  """Indicate instance progress during a patch job execution."""
  NOTIFIED = 1
  PATCHING = 2
  FINISHED = 3


INSTANCE_DETAILS_KEY_MAP = {
    'instancesAcked': InstanceDetailsStates.NOTIFIED,
    'instancesApplyingPatches': InstanceDetailsStates.PATCHING,
    'instancesDownloadingPatches': InstanceDetailsStates.PATCHING,
    'instancesFailed': InstanceDetailsStates.FINISHED,
    'instancesInactive': InstanceDetailsStates.FINISHED,
    'instancesNotified': InstanceDetailsStates.NOTIFIED,
    'instancesPending': InstanceDetailsStates.NOTIFIED,
    'instancesRebooting': InstanceDetailsStates.PATCHING,
    'instancesStarted': InstanceDetailsStates.PATCHING,
    'instancesSucceeded': InstanceDetailsStates.FINISHED,
    'instancesSucceededRebootRequired': InstanceDetailsStates.FINISHED
}

_API_CLIENT_NAME = 'osconfig'
_API_CLIENT_VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1alpha1'}


def GetProjectUriPath(project):
  """Return the URI path of a GCP project."""
  return '/'.join(['projects', project])


def GetPatchJobUriPath(project, patch_job):
  """Return the URI path of an osconfig patch job."""
  return '/'.join(['projects', project, 'patchJobs', patch_job])


def GetPatchJobName(patch_job_uri):
  """Return the name of a patch job from its URI."""
  return patch_job_uri.split('/')[3]


def GetClientClass(release_track):
  return apis.GetClientClass(_API_CLIENT_NAME,
                             _API_CLIENT_VERSION_MAP[release_track])


def GetClientInstance(release_track):
  return apis.GetClientInstance(_API_CLIENT_NAME,
                                _API_CLIENT_VERSION_MAP[release_track])


def GetClientMessages(release_track):
  return apis.GetMessagesModule(_API_CLIENT_NAME,
                                _API_CLIENT_VERSION_MAP[release_track])


class Poller(waiter.OperationPoller):
  """Poller for synchronous patch job execution."""

  def __init__(self, client, messages):
    """Initializes poller for patch job execution.

    Args:
      client: API client of the OsConfig service.
      messages: API messages of the OsConfig service.
    """
    self.client = client
    self.messages = messages
    self.patch_job_terminal_states = [
        self.messages.PatchJob.StateValueValuesEnum.SUCCEEDED,
        self.messages.PatchJob.StateValueValuesEnum.COMPLETED_WITH_ERRORS,
        self.messages.PatchJob.StateValueValuesEnum.TIMED_OUT,
        self.messages.PatchJob.StateValueValuesEnum.CANCELED
    ]

  def IsDone(self, patch_job):
    """Overrides."""
    return patch_job.state in self.patch_job_terminal_states

  def Poll(self, request):
    """Overrides."""
    return self.client.projects_patchJobs.Get(request)

  def GetResult(self, patch_job):
    """Overrides."""
    return patch_job
