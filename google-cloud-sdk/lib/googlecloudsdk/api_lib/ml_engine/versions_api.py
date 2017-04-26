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
from googlecloudsdk.api_lib.util import apis


def VersionsClient(version='v1beta1'):
  if version == 'v1beta1':
    return VersionsClientBeta()
  elif version == 'v1':
    return VersionsClientGa()
  else:
    raise ValueError('Unrecognized version [{}]'.format(version))


class VersionsClientBase(object):
  """Client for the versions service of Cloud ML Engine."""

  def __init__(self, client, messages=None):
    self.client = client
    self.messages = messages or self.client.MESSAGES_MODULE

  @property
  def version_class(self):
    raise NotImplementedError()

  def _MakeCreateRequest(self, parent, version):
    raise NotImplementedError()

  def _MakeSetDefaultRequest(self, name):
    raise NotImplementedError()

  def Create(self, model_ref, version_id, origin, runtime_version):
    """Creates a new version in an existing model."""
    return self.client.projects_models_versions.Create(
        self._MakeCreateRequest(
            parent=model_ref.RelativeName(),
            version=self.version_class(
                name=version_id,
                deploymentUri=origin,
                runtimeVersion=runtime_version)))

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
        self._MakeSetDefaultRequest(name=version_ref.RelativeName()))


class VersionsClientBeta(VersionsClientBase):
  """Client for the versions service of Cloud ML Engine."""

  def __init__(self, client=None, messages=None):
    super(VersionsClientBeta, self).__init__(
        client or apis.GetClientInstance('ml', 'v1beta1'), messages)

  @property
  def version_class(self):
    return self.messages.GoogleCloudMlV1beta1Version

  def _MakeCreateRequest(self, parent, version):
    return self.messages.MlProjectsModelsVersionsCreateRequest(
        parent=parent,
        googleCloudMlV1beta1Version=version)

  def _MakeSetDefaultRequest(self, name):
    request = self.messages.GoogleCloudMlV1beta1SetDefaultVersionRequest()
    return self.messages.MlProjectsModelsVersionsSetDefaultRequest(
        name=name,
        googleCloudMlV1beta1SetDefaultVersionRequest=request)


class VersionsClientGa(VersionsClientBase):
  """Client for the versions service of Cloud ML Engine."""

  def __init__(self, client=None, messages=None):
    super(VersionsClientGa, self).__init__(
        client or apis.GetClientInstance('ml', 'v1'), messages)

  @property
  def version_class(self):
    return self.messages.GoogleCloudMlV1Version

  def _MakeCreateRequest(self, parent, version):
    return self.messages.MlProjectsModelsVersionsCreateRequest(
        parent=parent,
        googleCloudMlV1Version=version)

  def _MakeSetDefaultRequest(self, name):
    request = self.messages.GoogleCloudMlV1SetDefaultVersionRequest()
    return self.messages.MlProjectsModelsVersionsSetDefaultRequest(
        name=name,
        googleCloudMlV1SetDefaultVersionRequest=request)
