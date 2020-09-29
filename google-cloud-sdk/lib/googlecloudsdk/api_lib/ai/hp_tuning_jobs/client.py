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
"""Utilities for querying hptuning-jobs in AI platform."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.core import yaml


class HpTuningJobsClient(object):
  """Client used for interacting with HyperparameterTuningJob endpoint."""

  def __init__(self, client=None, messages=None):
    self.client = client or apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[constants.BETA_VERSION])
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_hyperparameterTuningJobs

  @staticmethod
  def GetAlgorithmEnum():
    return apis.GetMessagesModule(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[constants.BETA_VERSION]
    ).GoogleCloudAiplatformV1beta1StudySpec.AlgorithmValueValuesEnum

  def Create(self,
             config_path,
             display_name,
             parent=None,
             max_trial_count=None,
             parallel_trial_count=None,
             algorithm=None):
    """Creates a hyperparameter tuning job with given parameters.

    Args:
      config_path: str, the file path of the hyperparameter tuning job
        configuration.
      display_name: str, the display name of the created hyperparameter tuning
        job.
      parent: str, parent of the created hyperparameter tuning job. e.g.
        /projects/xxx/locations/xxx/
      max_trial_count: int, the desired total number of Trials. The default
        value is 1.
      parallel_trial_count: int, the desired number of Trials to run in
        parallel. The default value is 1.
      algorithm: AlgorithmValueValuesEnum, the search algorithm specified for
        the Study.

    Returns:
      Created hyperparameter tuning job.
    """
    job_spec = self.messages.GoogleCloudAiplatformV1beta1HyperparameterTuningJob(
    )

    if config_path:
      data = yaml.load_path(config_path)
      if data:
        job_spec = messages_util.DictToMessageWithErrorCheck(
            data,
            self.messages.GoogleCloudAiplatformV1beta1HyperparameterTuningJob)

    job_spec.maxTrialCount = max_trial_count
    job_spec.parallelTrialCount = parallel_trial_count

    if display_name:
      job_spec.displayName = display_name

    if algorithm and job_spec.studySpec:
      job_spec.studySpec.algorithm = algorithm

    return self._service.Create(
        self.messages
        .AiplatformProjectsLocationsHyperparameterTuningJobsCreateRequest(
            parent=parent,
            googleCloudAiplatformV1beta1HyperparameterTuningJob=job_spec))

  def Get(self, name=None):
    request = self.messages.AiplatformProjectsLocationsHyperparameterTuningJobsGetRequest(
        name=name)
    return self._service.Get(request)

  def Cancel(self, name=None):
    request = self.messages.AiplatformProjectsLocationsHyperparameterTuningJobsCancelRequest(
        name=name)
    return self._service.Cancel(request)
