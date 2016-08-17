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
"""Utilities for dealing with ML jobs API."""

from apitools.base.py import list_pager

from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def Cancel(job):
  client = apis.GetClientInstance('ml', 'v1alpha3')
  msgs = apis.GetMessagesModule('ml', 'v1alpha3')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.operations')
  req = msgs.MlProjectsOperationsCancelRequest(
      projectsId=res.projectsId, operationsId=res.Name())
  resp = client.projects_operations.Cancel(req)
  return resp


def Get(job):
  client = apis.GetClientInstance('ml', 'v1alpha3')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.operations')
  req = res.Request()
  resp = client.projects_operations.Get(req)
  return resp


def List():
  client = apis.GetClientInstance('ml', 'v1alpha3')
  msgs = apis.GetMessagesModule('ml', 'v1alpha3')
  req = msgs.MlProjectsOperationsListRequest(
      projectsId=properties.VALUES.core.project.Get())
  return list_pager.YieldFromList(
      client.projects_operations,
      req,
      field='operations',
      batch_size_attribute='pageSize')
