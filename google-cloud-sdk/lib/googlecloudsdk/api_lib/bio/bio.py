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

"""Useful commands for interacting with the bio operations API."""

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions


class NoEndpointException(Exception):

  def __str__(self):
    return (
        'Source endpoint not initialized. Bio.Init must be '
        'called before using this module.')


class Bio(object):
  """Base class for bio api classes."""
  _client = None

  def __init__(self, project_id):
    self._project_id = project_id
    self._CheckClient()

  def _CheckClient(self):
    if not self._client:
      raise NoEndpointException()

  @property
  def client(self):
    self._CheckClient()
    return self._client

  def GetMessages(self):
    return self.client.MESSAGES_MODULE

  @classmethod
  def GetClientClass(cls):
    return apis.GetClientClass('bio', 'v1')

  @classmethod
  def GetClientInstance(cls, no_http=False):
    return apis.GetClientInstance('bio', 'v1', no_http)

  @classmethod
  def _SetApiEndpoint(cls):
    cls._client = cls.GetClientInstance()

  @classmethod
  def Init(cls):
    cls._SetApiEndpoint()

  def _MakeRequest(self, method, message):
    try:
      return method(message)
    except apitools_exceptions.HttpError as error:
      raise exceptions.HttpException(error)


class Operations(Bio):
  """Abstracts source project."""

  def __init__(self, project_id=None):
    super(Operations, self).__init__(project_id)

  def List(self, limit=None):
    """Make API calls to List operations.

    Args:
      limit: The number of operations to limit the resutls to.

    Returns:
      Generator that yields projects
    """
    return list_pager.YieldFromList(
        self.client.projects_operations,
        self.client.MESSAGES_MODULE.BioProjectsOperationsListRequest(
            # TODO(b/32240422): use resource parser here
            name='projects/{0}'.format(self._project_id)),
        limit=limit,
        field='operations',
        batch_size_attribute='pageSize')

  def Get(self, operation_ref):
    """Get operation information."""
    return self._MakeRequest(
        self.client.projects_operations.Get,
        self.client.MESSAGES_MODULE.BioProjectsOperationsGetRequest(
            name=operation_ref.RelativeName()))

  def Cancel(self, operation_ref):
    """Get operation information."""

    return self._MakeRequest(
        self.client.projects_operations.Cancel,
        self.client.MESSAGES_MODULE.BioProjectsOperationsCancelRequest(
            name=operation_ref.RelativeName()))


class Pipelines(Bio):

  def __init__(self, project_id, default_zones=None):
    super(Pipelines, self).__init__(project_id)
    self._default_zones = default_zones

  def RunDeepVariant(self, compute_zones, input_fastq1, input_fastq2, labels,
                     output_path, sample_name):
    """Runs DeepVariant."""

    zones = compute_zones or self._default_zones or []
    req = self.GetMessages().BioProjectsPipelinesRunDeepVariantV1alphaRequest(
        projectId=self._project_id,
        runDeepVariantV1alphaRequest=self.GetMessages()
        .RunDeepVariantV1alphaRequest(
            options=self.GetMessages().PipelineOptions(
                computeZones=zones, labels=labels),
            inputFastq1=input_fastq1,
            inputFastq2=input_fastq2,
            outputPath=output_path,
            sampleName=sample_name))

    return self._MakeRequest(
        self.client.projects_pipelines.RunDeepVariantV1alpha, req)
