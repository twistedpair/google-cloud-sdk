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

"""Utilities for Cloud Batch tasks API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


def GetClientInstance(version='v1alpha1', no_http=False):
  return apis.GetClientInstance('batch', version, no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class TasksClient(object):
  """Client for tasks service in the Cloud Batch API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self.service = self.client.projects_locations_jobs_taskGroups_tasks

  def Get(self, task_ref):
    get_req_type = (
        self.messages.BatchProjectsLocationsJobsTaskGroupsTasksGetRequest)
    get_req = get_req_type(name=task_ref.RelativeName())
    return self.service.Get(get_req)
