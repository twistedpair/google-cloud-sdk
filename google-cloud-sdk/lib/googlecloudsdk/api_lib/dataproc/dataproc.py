# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Common stateful utilities for the gcloud dataproc tool."""

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.core import resources


class Dataproc(object):
  """Stateful utility for calling Dataproc APIs.

  While this currently could all be static. It is encapsulated in a class to
  support API version switching in future.
  """

  def __init__(self, release_track=base.ReleaseTrack.GA):
    super(Dataproc, self).__init__()
    self.release_track = release_track

  @property
  def client(self):
    if self.release_track == base.ReleaseTrack.GA:
      return apis.GetClientInstance('dataproc', 'v1')
    return apis.GetClientInstance('dataproc', 'v1beta2')

  @property
  def messages(self):
    return self.client.MESSAGES_MODULE

  @property
  def resources(self):
    return resources.REGISTRY

  @property
  def terminal_job_states(self):
    return [
        self.messages.JobStatus.StateValueValuesEnum.CANCELLED,
        self.messages.JobStatus.StateValueValuesEnum.DONE,
        self.messages.JobStatus.StateValueValuesEnum.ERROR,
    ]
