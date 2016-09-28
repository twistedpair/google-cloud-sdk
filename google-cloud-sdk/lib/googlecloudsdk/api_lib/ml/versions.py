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
"""Utilities for dealing with ML model versions API."""

from apitools.base.py import list_pager
from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import resources


class InvalidArgumentError(core_exceptions.Error):
  """Indicates that the input argument was invalid in some way."""
  pass


def Create(model, version, origin):
  """Create a new version in an existing model."""
  if '/' in version:
    raise InvalidArgumentError('Version name should not contain "/"')
  # TODO(b/31062835): remove CloneAndSwitchAPI here and below
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')
  res = registry.Parse(
      version,
      params={'modelsId': model},
      collection='ml.projects.models.versions')
  req = msgs.MlProjectsModelsVersionsCreateRequest(
      projectsId=res.projectsId,
      modelsId=res.modelsId,
      googleCloudMlV1beta1Version=msgs.GoogleCloudMlV1beta1Version(
          name=res.Name(), deploymentUri=origin))
  op = client.projects_models_versions.Create(req)
  return op


def Delete(model, version):
  """Delete a version from a model."""
  if '/' in version:
    raise InvalidArgumentError('Version name should not contain "/"')
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')
  res = registry.Parse(
      version,
      params={'modelsId': model},
      collection='ml.projects.models.versions')
  req = msgs.MlProjectsModelsVersionsDeleteRequest(
      projectsId=res.projectsId, modelsId=res.modelsId, versionsId=res.Name())
  op = client.projects_models_versions.Delete(req)
  return op


def Get(model, version):
  """Get details about an existing model version."""
  if '/' in version:
    raise InvalidArgumentError('Version name should not contain "/"')
  client = apis.GetClientInstance('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')
  res = registry.Parse(
      version,
      params={'modelsId': model},
      collection='ml.projects.models.versions')
  req = res.Request()
  resp = client.projects_models_versions.Get(req)
  return resp


def List(model):
  """List the versions for a model."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')
  res = registry.Parse(
      model, collection='ml.projects.models')
  req = msgs.MlProjectsModelsVersionsListRequest(
      projectsId=res.projectsId, modelsId=res.Name())
  return list_pager.YieldFromList(client.projects_models_versions,
                                  req,
                                  field='versions',
                                  batch_size_attribute='pageSize')


def SetDefault(model, version):
  """Set a model's default version."""
  if '/' in version:
    raise InvalidArgumentError('Version name should not contain "/"')
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('ml', 'v1beta1')

  res = registry.Parse(
      version,
      params={'modelsId': model},
      collection='ml.projects.models.versions')
  req = msgs.MlProjectsModelsVersionsSetDefaultRequest(
      projectsId=res.projectsId,
      modelsId=res.modelsId,
      versionsId=res.Name(),
      googleCloudMlV1beta1SetDefaultVersionRequest=(
          msgs.GoogleCloudMlV1beta1SetDefaultVersionRequest()))
  resp = client.projects_models_versions.SetDefault(req)
  return resp
