# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for the model garden command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from apitools.base.py import encoding
from googlecloudsdk.api_lib.ai import operations
from googlecloudsdk.api_lib.ai.models import client as client_models
from googlecloudsdk.api_lib.monitoring import metric
from googlecloudsdk.api_lib.quotas import quota_info
from googlecloudsdk.command_lib.ai import endpoints_util
from googlecloudsdk.command_lib.ai import models_util
from googlecloudsdk.command_lib.ai import operations_util
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import requests
from googlecloudsdk.core import resources


_MAX_LABEL_VALUE_LENGTH = 63


_ACCELERATOR_TYPE_TO_QUOTA_ID_MAP = {
    'NVIDIA_TESLA_P4': 'CustomModelServingP4GPUsPerProjectPerRegion',
    'NVIDIA_TESLA_T4': 'CustomModelServingT4GPUsPerProjectPerRegion',
    'NVIDIA_L4': 'CustomModelServingL4GPUsPerProjectPerRegion',
    'NVIDIA_TESLA_K80': 'CustomModelServingK80GPUsPerProjectPerRegion',
    'NVIDIA_TESLA_V100': 'CustomModelServingV100GPUsPerProjectPerRegion',
    'NVIDIA_TESLA_P100': 'CustomModelServingP100GPUsPerProjectPerRegion',
    'NVIDIA_TESLA_A100': 'CustomModelServingA100GPUsPerProjectPerRegion',
    'NVIDIA_A100_80GB': 'CustomModelServingA10080GBGPUsPerProjectPerRegion',
    'NVIDIA_H100_80GB': 'CustomModelServingH100GPUsPerProjectPerRegion',
    'TPU_V5_LITEPOD': 'CustomModelServingV5ETPUPerProjectPerRegion',
}


_ACCELERATOR_TYPE_TP_QUOTA_METRIC_MAP = {
    'NVIDIA_TESLA_P4': 'custom_model_serving_nvidia_p4_gpus',
    'NVIDIA_TESLA_T4': 'custom_model_serving_nvidia_t4_gpus',
    'NVIDIA_L4': 'custom_model_serving_nvidia_l4_gpus',
    'NVIDIA_TESLA_K80': 'custom_model_serving_nvidia_k80_gpus',
    'NVIDIA_TESLA_V100': 'custom_model_serving_nvidia_v100_gpus',
    'NVIDIA_TESLA_P100': 'custom_model_serving_nvidia_p100_gpus',
    'NVIDIA_TESLA_A100': 'custom_model_serving_nvidia_a100_gpus',
    'NVIDIA_A100_80GB': 'custom_model_serving_nvidia_a100_80gb_gpus',
    'NVIDIA_H100_80GB': 'custom_model_serving_nvidia_h100_gpus',
    'TPU_V5_LITEPOD': 'custom_model_serving_tpu_v5e',
}
_TIME_SERIES_FILTER = (
    # gcloud-disable-gdu-domain
    'metric.type="serviceruntime.googleapis.com/quota/allocation/usage" AND'
    ' resource.type="consumer_quota" AND'
    # gcloud-disable-gdu-domain
    ' metric.label.quota_metric="aiplatform.googleapis.com/{}"'
    ' AND resource.label.project_id="{}" AND resource.label.location="{}" AND'
    # gcloud-disable-gdu-domain
    ' resource.label.service="aiplatform.googleapis.com"'
)


def _ParseEndpoint(endpoint_id, location_id):
  """Parses a Vertex Endpoint ID into a endpoint resource object."""
  return resources.REGISTRY.Parse(
      endpoint_id,
      params={
          'locationsId': location_id,
          'projectsId': properties.VALUES.core.project.GetOrFail,
      },
      collection='aiplatform.projects.locations.endpoints',
  )


def _GetQuotaLimit(region, project, accelerator_type):
  """Gets the quota limit for the accelerator type in the region."""
  accelerator_quota = quota_info.GetQuotaInfo(
      project,
      None,
      None,
      # gcloud-disable-gdu-domain
      'aiplatform.googleapis.com',
      _ACCELERATOR_TYPE_TO_QUOTA_ID_MAP[accelerator_type],
  )
  # Skip the last item in the list because it only contains the list of
  # supported region.
  for region_info in accelerator_quota.dimensionsInfos[:-1]:
    if region_info.applicableLocations[0] == region:
      return region_info.details.value or 0
  return 0


def _GetQuotaUsage(region, project, accelerator_type):
  """Gets the quota usage for the accelerator type in the region using the monitoring AP."""
  # Format the time in RFC3339 UTC Zulu format
  current_time_utc = datetime.datetime.now(datetime.timezone.utc)
  # Need to go back at least 24 hours to reliably get a data point
  twenty_five_hours_ago_time_utc = current_time_utc - datetime.timedelta(
      hours=25
  )

  rfc3339_time = current_time_utc.isoformat(timespec='seconds').replace(
      '+00:00', 'Z'
  )
  rfc3339_time_twenty_five_hours_ago = twenty_five_hours_ago_time_utc.isoformat(
      timespec='seconds'
  ).replace('+00:00', 'Z')

  quota_usage_time_series = metric.MetricClient().ListTimeSeriesByProject(
      project=project,
      aggregation_alignment_period='60s',
      aggregation_per_series_aligner=metric.GetMessagesModule().MonitoringProjectsTimeSeriesListRequest.AggregationPerSeriesAlignerValueValuesEnum.ALIGN_NEXT_OLDER,
      interval_start_time=rfc3339_time_twenty_five_hours_ago,
      interval_end_time=rfc3339_time,
      filter_str=_TIME_SERIES_FILTER.format(
          _ACCELERATOR_TYPE_TP_QUOTA_METRIC_MAP[accelerator_type],
          project,
          region,
      ),
  )
  try:
    current_usage = (
        quota_usage_time_series.timeSeries[0].points[0].value.int64Value
    )
  except IndexError:
    # If no data point is found, the usage is 0.
    current_usage = 0
  return current_usage


def GetCLIEndpointLabelValue(
    is_hf_model, publisher_name, model_name='', model_version_name=''
):
  if is_hf_model:
    return f'hf-{publisher_name}-{model_name}'.replace('.', '_')[
        :_MAX_LABEL_VALUE_LENGTH
    ]
  else:
    return f'mg-{publisher_name}-{model_version_name}'.replace('.', '_')[
        :_MAX_LABEL_VALUE_LENGTH
    ]


def GetOneClickEndpointLabelValue(
    is_hf_model, publisher_name, model_name='', model_version_name=''
):
  if is_hf_model:
    return f'hf-{publisher_name}-{model_name}'.replace('.', '_')[
        :_MAX_LABEL_VALUE_LENGTH
    ]
  else:
    return (
        f'publishers-{publisher_name}-models-{model_name}-{model_version_name}'
        .replace(
            '.', '_'
        )[
            :_MAX_LABEL_VALUE_LENGTH
        ]
    )


def IsHFModelGated(publisher_name, model_name):
  """Checks if the HF model is gated or not by calling HF API."""
  hf_response = requests.GetSession().get(
      f'https://huggingface.co/api/models/{publisher_name}/{model_name}?blobs=true'
  )
  if hf_response.status_code != 200:
    raise core_exceptions.InternalError(
        "Something went wrong when we call HuggingFace's API to get the"
        ' model metadata. Please try again later.'
    )
  return bool(hf_response.json()['gated'])


def VerifyHFTokenPermission(hf_token, publisher_name, model_name):
  hf_response = requests.GetSession().request(
      'GET',
      f'https://huggingface.co/api/models/{publisher_name}/{model_name}/auth-check',
      headers={'Authorization': f'Bearer {hf_token}'},
  )
  if hf_response.status_code != 200:
    raise core_exceptions.Error(
        'The Hugging Face access token is not valid or does not have permission'
        ' to access the gated model.'
    )
  return


def GetDeployConfig(args, publisher_model):
  """Returns a best suited deployment configuration for the publisher model."""
  try:
    multi_deploy = (
        publisher_model.supportedActions.multiDeployVertex.multiDeployVertex
    )
  except AttributeError:
    raise core_exceptions.Error(
        'Model does not support deployment, please use a deploy-able model'
        ' instead. You can use the `gcloud ai model-garden models list`'
        ' command to find out which ones are currently supported by the'
        ' `deploy` command.'
    )

  deploy_config = None
  if args.machine_type:
    for deploy in multi_deploy:
      if deploy.dedicatedResources.machineSpec.machineType == args.machine_type:
        deploy_config = deploy
        break
    if deploy_config is None:
      raise core_exceptions.Error(
          f'Machine type "{args.machine_type}" is not supported by the'
          ' model. You can use the `gcloud ai model-garden models'
          ' list-deployment-config` command to find the supported machine'
          ' types.'
      )
  else:
    # Default to use the first config.
    deploy_config = multi_deploy[0]

  machine_spec = deploy_config.dedicatedResources.machineSpec
  log.status.Print(
      'Using the {} deployment configuration:'.format(
          'selected' if args.machine_type else 'default'
      )
  )
  if machine_spec.machineType:
    log.status.Print(f' Machine type: {machine_spec.machineType}')
  if machine_spec.acceleratorType:
    log.status.Print(f' Accelerator type: {machine_spec.acceleratorType}')
  if machine_spec.acceleratorCount:
    log.status.Print(f' Accelerator count: {machine_spec.acceleratorCount}')
  return deploy_config


def CheckAcceleratorQuota(
    args, machine_type, accelerator_type, accelerator_count
):
  """Checks the accelerator quota for the project and region."""
  # In the machine spec, TPUs don't have accelerator type and count, but they
  # have machine type.
  if machine_type == 'ct5lp-hightpu-1t':
    accelerator_type = 'TPU_V5_LITEPOD'
    accelerator_count = 1
  elif machine_type == 'ct5lp-hightpu-4t':
    accelerator_type = 'TPU_V5_LITEPOD'
    accelerator_count = 4
  project = properties.VALUES.core.project.GetOrFail()
  quota_limit = _GetQuotaLimit(args.region, project, accelerator_type)
  if quota_limit < accelerator_count:
    raise core_exceptions.Error(
        f'The project does not have enough quota for {accelerator_type} in'
        f' {args.region} to'
        f' deploy the model. The quota limit is {quota_limit} and you are'
        f' requesting for {accelerator_count}. Please'
        ' use a different region or request more quota by following'
        ' https://cloud.google.com/vertex-ai/docs/quotas#requesting_additional_quota.'
    )

  current_usage = _GetQuotaUsage(args.region, project, accelerator_type)
  if current_usage + accelerator_count > quota_limit:
    raise core_exceptions.Error(
        f'The project does not have enough quota for {accelerator_type} in'
        f' {args.region} to'
        f' deploy the model. The current usage is {current_usage} out of'
        f' {quota_limit} and you are'
        f' requesting for {accelerator_count}. Please'
        ' use a different region or request more quota by following'
        ' https://cloud.google.com/vertex-ai/docs/quotas#requesting_additional_quota.'
    )
  log.status.Print(
      'The project has enough quota. The current usage of quota for'
      f' accelerator type {accelerator_type} in region {args.region} is'
      f' {current_usage} out of {quota_limit}.'
  )


def CreateEndpoint(
    endpoint_name,
    label_value,
    region_ref,
    operation_client,
    endpoints_client,
):
  """Creates a Vertex endpoint for deployment."""
  create_endpoint_op = endpoints_client.CreateBeta(
      region_ref,
      endpoint_name,
      labels=endpoints_client.messages.GoogleCloudAiplatformV1beta1Endpoint.LabelsValue(
          additionalProperties=[
              endpoints_client.messages.GoogleCloudAiplatformV1beta1Endpoint.LabelsValue.AdditionalProperty(
                  key='mg-cli-deploy', value=label_value
              )
          ]
      ),
  )
  create_endpoint_response_msg = operations_util.WaitForOpMaybe(
      operation_client,
      create_endpoint_op,
      endpoints_util.ParseOperation(create_endpoint_op.name),
  )
  if create_endpoint_response_msg is None:
    raise core_exceptions.InternalError(
        'Internal error: Failed to create a Vertex endpoint. Please try again.'
    )
  response = encoding.MessageToPyValue(create_endpoint_response_msg)
  if 'name' not in response:
    raise core_exceptions.InternalError(
        'Internal error: Failed to create a Vertex endpoint. Please try again.'
    )
  log.status.Print(
      (
          'Created Vertex AI endpoint: {}.\nStarting to upload the model'
          ' to Model Registry.'
      ).format(response['name'])
  )
  return response['name'].split('/')[-1]


def UploadModel(
    deploy_config,
    args,
    requires_hf_token,
    is_hf_model,
    uploaded_model_name,
    publisher_name,
    publisher_model_name,
):
  """Uploads the Model Garden model to Model Registry."""
  container_env_vars, container_args, container_commands = None, None, None
  if deploy_config.containerSpec.env:
    container_env_vars = {
        var.name: var.value for var in deploy_config.containerSpec.env
    }
    if requires_hf_token and 'HUGGING_FACE_HUB_TOKEN' in container_env_vars:
      container_env_vars['HUGGING_FACE_HUB_TOKEN'] = (
          args.hugging_face_access_token
      )
  if deploy_config.containerSpec.args:
    container_args = list(deploy_config.containerSpec.args)
  if deploy_config.containerSpec.command:
    container_commands = list(deploy_config.containerSpec.command)

  models_client = client_models.ModelsClient()
  upload_model_op = models_client.UploadV1Beta1(
      args.CONCEPTS.region.Parse(),
      uploaded_model_name,  # Re-use endpoint_name as the uploaded model name.
      None,
      None,
      deploy_config.artifactUri,
      deploy_config.containerSpec.imageUri,
      container_commands,
      container_args,
      container_env_vars,
      [deploy_config.containerSpec.ports[0].containerPort],
      None,
      deploy_config.containerSpec.predictRoute,
      deploy_config.containerSpec.healthRoute,
      base_model_source=models_client.messages.GoogleCloudAiplatformV1beta1ModelBaseModelSource(
          modelGardenSource=models_client.messages.GoogleCloudAiplatformV1beta1ModelGardenSource(
              # The value is consistent with one-click deploy.
              publicModelName='publishers/{}/models/{}'.format(
                  'hf-' + publisher_name if is_hf_model else publisher_name,
                  publisher_model_name,
              )
          )
      ),
  )

  upload_model_response_msg = operations_util.WaitForOpMaybe(
      operations_client=operations.OperationsClient(),
      op=upload_model_op,
      op_ref=models_util.ParseModelOperation(upload_model_op.name),
  )
  if upload_model_response_msg is None:
    raise core_exceptions.InternalError(
        'Internal error: Failed to upload a Model Garden model to Model'
        ' Registry. Please try again later.'
    )
  upload_model_response = encoding.MessageToPyValue(upload_model_response_msg)
  if 'model' not in upload_model_response:
    raise core_exceptions.InternalError(
        'Internal error: Failed to upload a Model Garden model to Model'
        ' Registry. Please try again later.'
    )
  log.status.Print(
      (
          'Uploaded model to Model Registry at {}.\nStarting to deploy the'
          ' model.'
      ).format(upload_model_response['model'])
  )
  return upload_model_response['model'].split('/')[-1]


def DeployModel(
    args,
    deploy_config,
    endpoint_id,
    endpoint_name,
    model_id,
    endpoints_client,
    operation_client,
):
  """Deploys the Model Registry model to the Vertex endpoint."""
  accelerator_type = (
      deploy_config.dedicatedResources.machineSpec.acceleratorType
  )
  accelerator_count = (
      deploy_config.dedicatedResources.machineSpec.acceleratorCount
  )

  accelerator_dict = None
  if accelerator_type is not None or accelerator_count is not None:
    accelerator_dict = {}
    if accelerator_type is not None:
      accelerator_dict['type'] = str(accelerator_type).lower().replace('_', '-')
    if accelerator_count is not None:
      accelerator_dict['count'] = accelerator_count

  deploy_model_op = endpoints_client.DeployModelBeta(
      _ParseEndpoint(endpoint_id, args.region),
      model_id,
      args.region,
      endpoint_name,  # Use the endpoint_name as the deployed model name.
      machine_type=deploy_config.dedicatedResources.machineSpec.machineType,
      accelerator_dict=accelerator_dict,
      enable_access_logging=True,
      enable_container_logging=True,
  )
  operations_util.WaitForOpMaybe(
      operation_client,
      deploy_model_op,
      endpoints_util.ParseOperation(deploy_model_op.name),
      asynchronous=True,  # Deploy the model asynchronously.
  )
  deploy_op_id = deploy_model_op.name.split('/')[-1]
  print(
      'Deploying the model to the endpoint. To check the deployment'
      ' status, you can try one of the following methods:\n1) Look for'
      f' endpoint `{endpoint_name}` at the [Vertex AI] -> [Online'
      ' prediction] tab in Cloud Console\n2) Use `gcloud ai operations'
      f' describe {deploy_op_id} --region={args.region}` to find the status'
      ' of the deployment long-running operation\n3) Use `gcloud ai'
      f' endpoints describe {endpoint_id} --region={args.region}` command'
      " to check the endpoint's metadata."
  )
