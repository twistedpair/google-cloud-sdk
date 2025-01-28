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
"""Utilities for AI Platform serverless ray jobs commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


SERVERLESS_RAY_JOB_COLLECTION = (
    'aiplatform.projects.locations.serverlessRayJobs'
)


def _ConstructResourceSpecs(aiplatform_client, resource_spec):
  """Constructs the specification of a Ray worker nodepool.

  Args:
    aiplatform_client: The AI Platform API client used.
    resource_spec: A dict whose fields represent the resource spec.

  Returns:
    A ResoueceSpec message instance for nodepool resource spec for the
    serverless ray job.
  """

  resource_specs = []
  spec = aiplatform_client.GetMessage('ServerlessRayJobSpecResourceSpec')()
  resource_spec_dict = resource_spec

  if resource_spec_dict.get('disk-size'):
    spec.disk = aiplatform_client.GetMessage(
        'ServerlessRayJobSpecResourceSpecDisk'
    )(diskSizeGb=resource_spec_dict.get('disk-size'))

  if resource_spec_dict.get('resource-unit'):
    spec.resourceUnit = resource_spec_dict.get('resource-unit')
  if resource_spec_dict.get('max-node-count'):
    spec.maxNodeCount = resource_spec_dict.get('max-node-count')

  print('resource_spec: {}'.format(spec))

  resource_specs.append(spec)

  return resource_specs


def ConstructServerlessRayJobSpec(
    aiplatform_client,
    main_python_file_uri=None,
    entrypoint_file_args=None,
    archive_uris=None,
    service_account=None,
    container_image_uri=None,
    resource_spec=None,
):
  """Constructs the spec of a serverless ray job to be used in job creation request.

  Args:
    aiplatform_client: The AI Platform API client used.
    main_python_file_uri: The main python file uri of the serverless ray job.
    entrypoint_file_args: The args to pass into the serverless ray job.
    archive_uris: The uris of the archives to be extracted and copy to Ray
      worker nodes.
    service_account: The service account to run the serverless ray job as.
    container_image_uri: The container image uri to run the serverless ray job.
    resource_spec: The resource spec of the nodepool for the serverless ray job.

  Returns:
    A ServerlessRayJobSpec message instance for creating a serverless ray job.
  """

  job_spec_message = aiplatform_client.GetMessage('ServerlessRayJobSpec')
  job_spec = job_spec_message(mainPythonFileUri=main_python_file_uri)

  if service_account is not None:
    job_spec.serviceAccount = service_account
  if archive_uris:
    job_spec.archiveUris = archive_uris
  if entrypoint_file_args:
    job_spec.args = entrypoint_file_args

  if resource_spec:
    job_spec.resourceSpecs = _ConstructResourceSpecs(
        aiplatform_client, resource_spec
    )

  if container_image_uri:
    runtime_env = aiplatform_client.GetMessage(
        'ServerlessRayJobSpecRuntimeEnv'
    )()
    runtime_env_container = aiplatform_client.GetMessage(
        'ServerlessRayJobSpecRuntimeEnvContainer'
    )(imageUri=container_image_uri)
    runtime_env.container = runtime_env_container
    job_spec.runtimeEnv = runtime_env

  return job_spec


def _IsKwargsDefined(key, **kwargs):
  return key in kwargs and bool(kwargs.get(key))
