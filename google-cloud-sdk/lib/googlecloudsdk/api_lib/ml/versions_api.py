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
"""Utilities for dealing with ML versions API."""

from apitools.base.py import list_pager
from googlecloudsdk.core import apis


class VersionsClient(object):
  """Client for the versions service of Cloud ML."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance('ml', 'v1beta1')
    self.messages = messages or apis.GetMessagesModule('ml', 'v1beta1')

  def Create(self, model_ref, version_id, origin, runtime_version):
    """Creates a new version in an existing model."""
    return self.client.projects_models_versions.Create(
        self.messages.MlProjectsModelsVersionsCreateRequest(
            parent=model_ref.RelativeName(),
            googleCloudMlV1beta1Version=(
                self.messages.GoogleCloudMlV1beta1Version(
                    name=version_id,
                    deploymentUri=origin,
                    runtimeVersion=runtime_version))))

  def Delete(self, version_ref):
    """Deletes a version from a model."""
    return self.client.projects_models_versions.Delete(
        self.messages.MlProjectsModelsVersionsDeleteRequest(
            name=version_ref.RelativeName()))

  def Get(self, version_ref):
    """Gets details about an existing model version."""
    return self.client.projects_models_versions.Get(
        self.messages.MlProjectsModelsVersionsGetRequest(
            name=version_ref.RelativeName()))

  def List(self, model_ref):
    """Lists the versions for a model."""
    list_request = self.messages.MlProjectsModelsVersionsListRequest(
        parent=model_ref.RelativeName())
    return list_pager.YieldFromList(
        self.client.projects_models_versions, list_request,
        field='versions', batch_size_attribute='pageSize')

  def SetDefault(self, version_ref):
    """Sets a model's default version."""
    return self.client.projects_models_versions.SetDefault(
        self.messages.MlProjectsModelsVersionsSetDefaultRequest(
            name=version_ref.RelativeName(),
            googleCloudMlV1beta1SetDefaultVersionRequest=(
                self.messages.GoogleCloudMlV1beta1SetDefaultVersionRequest())))
