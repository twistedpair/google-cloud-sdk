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
from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import text

import yaml


class InvalidVersionConfigFile(exceptions.Error):
  """Error indicating an invalid Version configuration file."""


class VersionsClient(object):
  """Client for the versions service of Cloud ML Engine."""

  _ALLOWED_YAML_FIELDS = set(['description', 'deploymentUri', 'runtimeVersion',
                              'manualScaling'])

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance('ml', 'v1')
    self.messages = messages or self.client.MESSAGES_MODULE

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

  def Create(self, model_ref, version):
    """Creates a new version in an existing model."""
    return self.client.projects_models_versions.Create(
        self._MakeCreateRequest(
            parent=model_ref.RelativeName(),
            version=version))

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

  def BuildVersion(self, name,
                   path=None,
                   deployment_uri=None,
                   runtime_version=None):
    """Create a Version object.

    The object is based on an optional YAML configuration file and the
    parameters to this method; any provided method parameters override any
    provided in-file configuration.

    The file may only have the fields given in
    VersionsClientBase._ALLOWED_YAML_FIELDS specified; the only parameters
    allowed are those that can be specified on the command line.

    Args:
      name: str, the name of the version object to create.
      path: str, the path to the YAML file.
      deployment_uri: str, the deploymentUri to set for the Version
      runtime_version: str, the runtimeVersion to set for the Version

    Returns:
      A Version object (for the corresponding API version).

    Raises:
      InvalidVersionConfigFile: If the file contains unexpected fields.
    """
    version = self.version_class()

    if path:
      try:
        with open(path) as config_file:
          data = yaml.load(config_file)
      except (IOError, OSError, yaml.error.YAMLError) as err:
        raise InvalidVersionConfigFile(
            'Could not read Version configuration file [{path}]:\n\n'
            '{err}'.format(path=path, err=str(err)))
      if data:
        version = encoding.DictToMessage(data, self.version_class)

    specified_fields = set([f.name for f in version.all_fields() if
                            getattr(version, f.name)])
    invalid_fields = (specified_fields - self._ALLOWED_YAML_FIELDS |
                      set(version.all_unrecognized_fields()))
    if invalid_fields:
      raise InvalidVersionConfigFile(
          'Invalid {noun} [{fields}] in configuration file [{path}]. '
          'Allowed fields: [{allowed}].'.format(
              noun=text.Pluralize(len(invalid_fields), 'field'),
              fields=', '.join(sorted(invalid_fields)),
              path=path,
              allowed=', '.join(sorted(self._ALLOWED_YAML_FIELDS))))

    additional_fields = {
        'name': name,
        'deploymentUri': deployment_uri,
        'runtimeVersion': runtime_version,
    }
    for field_name, value in additional_fields.items():
      if value is not None:
        setattr(version, field_name, value)

    return version
