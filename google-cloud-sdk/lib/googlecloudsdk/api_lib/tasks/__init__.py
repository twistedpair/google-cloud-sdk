# -*- coding: utf-8 -*- #
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
"""API Library for gcloud cloudtasks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


API_NAME = 'cloudtasks'
API_VERSION = 'v2beta2'


def GetClientInstance(no_http=False):
  return apis.GetClientInstance(API_NAME, API_VERSION, no_http=no_http)


def GetMessagesModule(client=None):
  client = client or GetClientInstance()
  return client.MESSAGES_MODULE


class ApiAdapter(object):

  def __init__(self, client=None, messages=None):
    client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule(client)
    self.queues_service = client.projects_locations_queues
    self.tasks_service = client.projects_locations_queues_tasks
    self.locations_service = client.projects_locations
