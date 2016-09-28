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
"""Utilities for dealing with ML models API."""

from apitools.base.py import list_pager
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def Create(model):
  """Create a new model."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  # TODO(b/31062835): remove CloneAndSwitchAPI here and below
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')
  res = registry.Parse(model, collection='ml.projects.models')
  req = msgs.MlProjectsModelsCreateRequest(
      projectsId=res.projectsId,
      googleCloudMlV1beta1Model=msgs.GoogleCloudMlV1beta1Model(
          name=res.Name()))
  op = client.projects_models.Create(req)
  return op


def Delete(model):
  """Delete an existing model."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')

  res = registry.Parse(model, collection='ml.projects.models')
  req = msgs.MlProjectsModelsDeleteRequest(
      projectsId=res.projectsId, modelsId=res.Name())
  op = client.projects_models.Delete(req)
  return op


def Get(model):
  """Get details about a model."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')

  res = registry.Parse(model, collection='ml.projects.models')
  req = res.Request()
  resp = client.projects_models.Get(req)
  return resp


def List():
  """List models in the project."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  req = msgs.MlProjectsModelsListRequest(
      projectsId=properties.VALUES.core.project.Get())
  return list_pager.YieldFromList(
      client.projects_models,
      req,
      field='models',
      batch_size_attribute='pageSize')
