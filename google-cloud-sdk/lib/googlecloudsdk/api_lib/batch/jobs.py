# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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

"""Utilities for Cloud Batch jobs API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core.util import files


def GetClientInstance(version='v1alpha1', no_http=False):
  return apis.GetClientInstance('batch', version, no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class JobsClient(object):
  """Client for jobs service in the Cloud Batch API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self._service = self.client.projects_locations_jobs

  def Create(self, job_id, location_ref, job_config):
    create_req_type = (
        self.messages.BatchProjectsLocationsJobsCreateRequest)
    create_req = create_req_type(
        jobId=job_id,
        parent=location_ref.RelativeName(),
        job=self._CreateJobMessage(job_config))
    return self._service.Create(create_req)

  def Get(self, job_ref):
    get_req_type = (
        self.messages.BatchProjectsLocationsJobsGetRequest)
    get_req = get_req_type(name=job_ref.RelativeName())
    return self._service.Get(get_req)

  def Delete(self, job_ref):
    delete_req_type = (
        self.messages.BatchProjectsLocationsJobsDeleteRequest)
    delete_req = delete_req_type(name=job_ref.RelativeName())
    return self._service.Delete(delete_req)

  # TODO(b/216858129): add HEREDOC support.
  def _CreateJobMessage(self, config):
    """Construct the job proto with the config input."""
    file_contents = files.ReadFileContents(config)
    return encoding.JsonToMessage(self.messages.Job, file_contents)
