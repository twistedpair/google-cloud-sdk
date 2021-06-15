# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for AI Platform custom jobs commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import resources


def ParseJobName(name):
  return resources.REGISTRY.Parse(
      name, collection=constants.CUSTOM_JOB_COLLECTION).Name()


def _ConstructSingleWorkerPoolSpec(aiplatform_client,
                                   spec,
                                   python_package_uri=None,
                                   args=None,
                                   command=None):
  """Constructs the specification of a single worker pool.

  Args:
    aiplatform_client: The AI Platform API client used.
    spec: A dict whose fields represent a worker pool config.
    python_package_uri: str, The common python package uris that will be used by
      executor image, supposedly derived from the gcloud command flags.
    args: A list of arguments to be passed to containers or python packge,
      supposedly derived from the gcloud command flags.
    command: A list of commands to be passed to containers, supposedly derived
      from the gcloud command flags.

  Returns:
    A WorkerPoolSpec message instance for setting a worker pool in a custom job.
  """
  worker_pool_spec = aiplatform_client.GetMessage('WorkerPoolSpec')()

  machine_spec_msg = aiplatform_client.GetMessage('MachineSpec')
  machine_spec = machine_spec_msg(machineType=spec.get('machine-type'))
  accelerator_type = spec.get('accelerator-type')
  if accelerator_type:
    machine_spec.acceleratorType = arg_utils.ChoiceToEnum(
        accelerator_type, machine_spec_msg.AcceleratorTypeValueValuesEnum)
    machine_spec.acceleratorCount = int(spec.get('accelerator-count', 1))
  worker_pool_spec.machineSpec = machine_spec
  worker_pool_spec.replicaCount = int(spec.get('replica-count', 1))

  container_image_uri = spec.get('container-image-uri')
  executor_image_uri = spec.get('executor-image-uri')
  python_module = spec.get('python-module')

  if container_image_uri:
    container_spec_msg = aiplatform_client.GetMessage('ContainerSpec')
    worker_pool_spec.containerSpec = container_spec_msg(
        imageUri=container_image_uri)
    if args is not None:
      worker_pool_spec.containerSpec.args = args
    if command is not None:
      worker_pool_spec.containerSpec.command = command

  if python_package_uri or executor_image_uri or python_module:
    python_package_spec_msg = aiplatform_client.GetMessage('PythonPackageSpec')
    worker_pool_spec.pythonPackageSpec = python_package_spec_msg(
        executorImageUri=executor_image_uri,
        packageUris=(python_package_uri or []),
        pythonModule=python_module)
    if args is not None:
      worker_pool_spec.pythonPackageSpec.args = args

  return worker_pool_spec


def _ConstructWorkerPoolSpecs(aiplatform_client, specs, **kwargs):
  """Constructs the specification of the worker pools in a CustomJobSpec instance.

  Args:
    aiplatform_client: The AI Platform API client used.
    specs: A list of dict of worker pool specifications, supposedly derived from
      the gcloud command flags.
    **kwargs: The keyword args to pass down to construct each worker pool spec.

  Returns:
    A list of WorkerPoolSpec message instances for creating a custom job.
  """

  # TODO(b/184350069): Support creating jobs with auto-packaging.
  worker_pool_specs = []

  for spec in specs:
    if spec:
      worker_pool_specs.append(
          _ConstructSingleWorkerPoolSpec(aiplatform_client, spec, **kwargs))
    else:
      worker_pool_specs.append(aiplatform_client.GetMessage('WorkerPoolSpec')())

  return worker_pool_specs


def ConstructCustomJobSpec(aiplatform_client,
                           base_config=None,
                           network=None,
                           service_account=None,
                           worker_pool_specs=None,
                           **kwargs):
  """Construct the spec of a custom job to be used in job creation request.

  Args:
    aiplatform_client: The AI Platform API client used.
    base_config: A base CustomJobSpec message instance, e.g. imported from a
      Yaml config file, as a template to be overridden.
    network: user network to which the job should be peered with (overrides yaml
      file)
    service_account: A service account (email address string) to use for the
      job.
    worker_pool_specs: A dict of worker pool specification, usually derived from
      the gcloud command argument values.
     **kwargs: The keyword args to pass to construct the worker pool specs.

  Returns:
    A CustomJobSpec message instance for creating a custom job.
  """

  job_spec = base_config

  if network is not None:
    job_spec.network = network
  if service_account is not None:
    job_spec.serviceAccount = service_account

  if worker_pool_specs:
    job_spec.workerPoolSpecs = _ConstructWorkerPoolSpecs(
        aiplatform_client, worker_pool_specs, **kwargs)

  return job_spec
