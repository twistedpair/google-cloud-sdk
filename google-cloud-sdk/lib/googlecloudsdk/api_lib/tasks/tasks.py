# Copyright 2017 Google Inc. All Rights Reserved.
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
"""API Library for gcloud tasks."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib import tasks


class Tasks(object):

  def __init__(self, tasks_api=None):
    if tasks_api is None:
      tasks_api = tasks.ApiAdapter()
    self.api = tasks_api

  def List(self, parent_ref, limit=None, page_size=100):
    request = (
        self.api.messages.CloudtasksProjectsLocationsQueuesTasksListRequest(
            parent=parent_ref.RelativeName()))
    return list_pager.YieldFromList(
        self.api.tasks_service, request, batch_size=page_size, limit=limit,
        field='tasks', batch_size_attribute='pageSize')
