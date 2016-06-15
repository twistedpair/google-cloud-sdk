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
"""Useful commands for interacting with the Cloud Resource Management API."""


from googlecloudsdk.api_lib.projects import util
from googlecloudsdk.third_party.apitools.base.py import list_pager


def List(client=None, messages=None, limit=None):
  """Make API calls to List active projects.

  Args:
    client: Projects client to use or None to use the default
    messages: Projects messages class to use or None to use the default
    limit: The number of projects to limit the resutls to. This limit is passed
           to the server and the server does the limiting.

  Returns:
    Generator that yields projects
  """
  client = client or util.GetClient()
  messages = messages or util.GetMessages()
  return list_pager.YieldFromList(
      client.projects,
      messages.CloudresourcemanagerProjectsListRequest(),
      limit=limit,
      field='projects',
      predicate=util.IsActive,
      batch_size_attribute='pageSize')
