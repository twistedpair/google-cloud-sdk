# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Utilities for querying serverless ray jobs in AI Platform."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.export import util as export_util
from googlecloudsdk.core.console import console_io


class ServerlessRayJobsClient(object):
  """Client used for interacting with Serverless Ray Jobs endpoint."""

  def __init__(self, version=constants.GA_VERSION):
    client = apis.GetClientInstance(constants.AI_PLATFORM_API_NAME,
                                    constants.AI_PLATFORM_API_VERSION[version])
    self._messages = client.MESSAGES_MODULE
    self._version = version
    self._service = client.projects_locations_serverlessRayJobs
    self._message_prefix = constants.AI_PLATFORM_MESSAGE_PREFIX[version]

  def GetMessage(self, message_name):
    """Returns the API message class by name."""

    return getattr(
        self._messages,
        '{prefix}{name}'.format(prefix=self._message_prefix,
                                name=message_name), None)

  def ServerlessRayJobMessage(self):
    """Retures the Serverless Ray Jobs resource message."""

    return self.GetMessage('ServerlessRayJob')

  def Create(self,
             parent,
             job_spec,
             display_name=None,
             labels=None):
    """Constructs a request and sends it to the endpoint to create a serverless ray job instance.

    Args:
      parent: str, The project resource path of the serverless ray job to
        create.
      job_spec: The ServerlessRayJobSpec message instance for the job creation
        request.
      display_name: str, The display name of the serverless ray job to create.
      labels: LabelValues, map-like user-defined metadata to organize the
        serverless ray job.

    Returns:
      A ServerlessRayJob message instance created.
    """
    serverless_ray_job = self.ServerlessRayJobMessage()(
        displayName=display_name, jobSpec=job_spec
    )

    if labels:
      serverless_ray_job.labels = labels

    # TODO(b/390679825): Add V1 version support when Serverless Ray Jobs API is
    # GA ready.
    return self._service.Create(
        self._messages.AiplatformProjectsLocationsServerlessRayJobsCreateRequest(
            parent=parent,
            googleCloudAiplatformV1beta1ServerlessRayJob=serverless_ray_job,
        )
    )

  def List(self, limit=None, region=None):
    return list_pager.YieldFromList(
        self._service,
        self._messages.AiplatformProjectsLocationsServerlessRayJobsListRequest(
            parent=region
        ),
        field='serverlessRayJobs',
        batch_size_attribute='pageSize',
        limit=limit,
    )

  def Get(self, name):
    request = (
        self._messages.AiplatformProjectsLocationsServerlessRayJobsGetRequest(
            name=name
        )
    )
    return self._service.Get(request)

  def Cancel(self, name):
    request = self._messages.AiplatformProjectsLocationsServerlessRayJobsCancelRequest(
        name=name
    )
    return self._service.Cancel(request)

  def ImportResourceMessage(self, yaml_file, message_name):
    """Import a messages class instance typed by name from a YAML file."""
    data = console_io.ReadFromFileOrStdin(yaml_file, binary=False)
    message_type = self.GetMessage(message_name)
    return export_util.Import(message_type=message_type, stream=data)
