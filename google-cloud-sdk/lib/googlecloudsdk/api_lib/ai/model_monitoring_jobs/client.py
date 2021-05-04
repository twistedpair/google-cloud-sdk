# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for dealing with AI Platform model monitoring jobs API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy

from apitools.base.py import encoding
from apitools.base.py import extra_types
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.ai import errors
from googlecloudsdk.command_lib.ai import model_monitoring_jobs_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core import yaml
import six


def _ParseEndpoint(endpoint_id, region_ref):
  """Parses a endpoint ID into a endpoint resource object."""
  region = region_ref.AsDict()['locationsId']
  return resources.REGISTRY.Parse(
      endpoint_id,
      params={
          'locationsId': region,
          'projectsId': properties.VALUES.core.project.GetOrFail
      },
      collection='aiplatform.projects.locations.endpoints')


class ModelMonitoringJobsClient(object):
  """High-level client for the AI Platform model deployment monitoring jobs surface."""

  def __init__(self, client=None, messages=None, version=None):
    self.client = client or apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[version])
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_modelDeploymentMonitoringJobs

  def _ConstructObjectiveConfig(self, endpoint_name, drift_thresholds):
    """Construct monitoring objective config.

    It only contains PredictionDriftDetectionConfig and is applied to all
    the deployed models.
    Args:
      endpoint_name: Endpoint resource name.
      drift_thresholds: Dict or None, key: feature_name, value: thresholds.

    Returns:
      A list of model monitoring objective config.
    """
    objective_config_template = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringObjectiveConfig(
    )
    if drift_thresholds is not None:
      prediction_drift_detection = self.messages.GoogleCloudAiplatformV1beta1ModelMonitoringObjectiveConfigPredictionDriftDetectionConfig(
      )
      additional_properties = []
      for key, value in drift_thresholds.items():
        threshold = 0.3 if not value else float(value)
        additional_properties.append(
            prediction_drift_detection.DriftThresholdsValue(
            ).AdditionalProperty(
                key=key,
                value=self.messages.GoogleCloudAiplatformV1beta1ThresholdConfig(
                    value=threshold)))
      prediction_drift_detection.driftThresholds = prediction_drift_detection.DriftThresholdsValue(
          additionalProperties=additional_properties)
      objective_config_template.objectiveConfig = self.messages.GoogleCloudAiplatformV1beta1ModelMonitoringObjectiveConfig(
          predictionDriftDetectionConfig=prediction_drift_detection)

    get_endpoint_req = self.messages.AiplatformProjectsLocationsEndpointsGetRequest(
        name=endpoint_name)
    endpoint = self.client.projects_locations_endpoints.Get(get_endpoint_req)
    objective_configs = []
    for deployed_model in endpoint.deployedModels:
      objective_config = copy.deepcopy(objective_config_template)
      objective_config.deployedModelId = deployed_model.id
      objective_configs.append(objective_config)
    return objective_configs

  def Create(self, location_ref, args):
    """Creates a model deployment monitoring job."""
    endpoint_ref = _ParseEndpoint(args.endpoint, location_ref)
    job_spec = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringJob(
    )
    if args.monitoring_config_from_file:
      data = yaml.load_path(args.monitoring_config_from_file)
      if data:
        job_spec = messages_util.DictToMessageWithErrorCheck(
            data, self.messages
            .GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringJob)
    else:
      job_spec.modelDeploymentMonitoringObjectiveConfigs = self._ConstructObjectiveConfig(
          endpoint_ref.RelativeName(), args.drift_thresholds)

    job_spec.endpoint = endpoint_ref.RelativeName()
    job_spec.displayName = args.display_name

    job_spec.modelMonitoringAlertConfig = self.messages.GoogleCloudAiplatformV1beta1ModelMonitoringAlertConfig(
        emailAlertConfig=self.messages
        .GoogleCloudAiplatformV1beta1ModelMonitoringAlertConfigEmailAlertConfig(
            userEmails=args.emails))

    job_spec.loggingSamplingStrategy = self.messages.GoogleCloudAiplatformV1beta1SamplingStrategy(
        randomSampleConfig=self.messages
        .GoogleCloudAiplatformV1beta1SamplingStrategyRandomSampleConfig(
            sampleRate=args.prediction_sampling_rate))

    job_spec.modelDeploymentMonitoringScheduleConfig = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringScheduleConfig(
        monitorInterval='{}s'.format(
            six.text_type(3600 * int(args.monitoring_frequency))))

    if args.predict_instance_schema is not None:
      job_spec.predictInstanceSchemaUri = args.predict_instance_schema

    if args.analysis_instance_schema is not None:
      job_spec.analysisInstanceSchemaUri = args.analysis_instance_schema

    if args.log_ttl is not None:
      job_spec.logTtl = '{}s'.format(six.text_type(86400 * int(args.log_ttl)))

    if args.sample_predict_request is not None:
      instance_json = model_monitoring_jobs_util.ReadInstanceFromArgs(
          args.sample_predict_request)
      job_spec.samplePredictInstance = encoding.PyValueToMessage(
          extra_types.JsonValue, instance_json)

    return self._service.Create(
        self.messages
        .AiplatformProjectsLocationsModelDeploymentMonitoringJobsCreateRequest(
            parent=location_ref.RelativeName(),
            googleCloudAiplatformV1beta1ModelDeploymentMonitoringJob=job_spec))

  def Patch(self, model_monitoring_job_ref, args):
    """Update a model deployment monitoring job."""
    model_monitoring_job_to_update = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringJob(
    )
    update_mask = []

    job_spec = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringJob(
    )
    if args.monitoring_config_from_file:
      data = yaml.load_path(args.monitoring_config_from_file)
      if data:
        job_spec = messages_util.DictToMessageWithErrorCheck(
            data, self.messages
            .GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringJob)
        model_monitoring_job_to_update.modelDeploymentMonitoringObjectiveConfigs = job_spec.modelDeploymentMonitoringObjectiveConfigs
        update_mask.append('model_deployment_monitoring_objective_configs')

    if args.drift_thresholds is not None:
      get_monitoring_job_req = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsGetRequest(
          name=model_monitoring_job_ref.RelativeName())
      model_monitoring_job = self._service.Get(get_monitoring_job_req)
      model_monitoring_job_to_update.modelDeploymentMonitoringObjectiveConfigs = self._ConstructObjectiveConfig(
          model_monitoring_job.endpoint, args.drift_thresholds)
      update_mask.append('model_deployment_monitoring_objective_configs')

    if args.display_name is not None:
      model_monitoring_job_to_update.displayName = args.display_name
      update_mask.append('display_name')

    if args.emails is not None:
      model_monitoring_job_to_update.modelMonitoringAlertConfig = self.messages.GoogleCloudAiplatformV1beta1ModelMonitoringAlertConfig(
          emailAlertConfig=self.messages.
          GoogleCloudAiplatformV1beta1ModelMonitoringAlertConfigEmailAlertConfig(
              userEmails=args.emails))
      update_mask.append('model_monitoring_alert_config')

    # sampling rate
    if args.prediction_sampling_rate is not None:
      model_monitoring_job_to_update.loggingSamplingStrategy = self.messages.GoogleCloudAiplatformV1beta1SamplingStrategy(
          randomSampleConfig=self.messages
          .GoogleCloudAiplatformV1beta1SamplingStrategyRandomSampleConfig(
              sampleRate=args.prediction_sampling_rate))
      update_mask.append('logging_sampling_strategy')

    # schedule
    if args.monitoring_frequency is not None:
      model_monitoring_job_to_update.modelDeploymentMonitoringScheduleConfig = self.messages.GoogleCloudAiplatformV1beta1ModelDeploymentMonitoringScheduleConfig(
          monitorInterval='{}s'.format(
              six.text_type(3600 * int(args.monitoring_frequency))))
      update_mask.append('model_deployment_monitoring_schedule_config')

    if args.analysis_instance_schema is not None:
      model_monitoring_job_to_update.analysisInstanceSchemaUri = args.analysis_instance_schema
      update_mask.append('analysis_instance_schema_uri')

    if args.log_ttl is not None:
      model_monitoring_job_to_update.logTtl = '{}s'.format(
          six.text_type(86400 * int(args.log_ttl)))
      update_mask.append('log_ttl')

    if not update_mask:
      raise errors.NoFieldsSpecifiedError('No updates requested.')

    req = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsPatchRequest(
        name=model_monitoring_job_ref.RelativeName(),
        googleCloudAiplatformV1beta1ModelDeploymentMonitoringJob=model_monitoring_job_to_update,
        updateMask=','.join(update_mask))
    return self._service.Patch(req)

  def Get(self, model_monitoring_job_ref):
    request = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsGetRequest(
        name=model_monitoring_job_ref.RelativeName())
    return self._service.Get(request)

  def List(self, limit=None, region_ref=None):
    return list_pager.YieldFromList(
        self._service,
        self.messages
        .AiplatformProjectsLocationsModelDeploymentMonitoringJobsListRequest(
            parent=region_ref.RelativeName()),
        field='modelDeploymentMonitoringJobs',
        batch_size_attribute='pageSize',
        limit=limit)

  def Delete(self, model_monitoring_job_ref):
    request = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsDeleteRequest(
        name=model_monitoring_job_ref.RelativeName())
    return self._service.Delete(request)

  def Pause(self, model_monitoring_job_ref):
    request = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsPauseRequest(
        name=model_monitoring_job_ref.RelativeName())
    return self._service.Pause(request)

  def Resume(self, model_monitoring_job_ref):
    request = self.messages.AiplatformProjectsLocationsModelDeploymentMonitoringJobsResumeRequest(
        name=model_monitoring_job_ref.RelativeName())
    return self._service.Resume(request)
