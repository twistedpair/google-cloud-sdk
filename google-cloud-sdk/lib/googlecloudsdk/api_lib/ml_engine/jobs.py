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
"""Utilities for dealing with ML jobs API."""
from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
import yaml


def GetMessagesModule(version='v1'):
  return apis.GetMessagesModule('ml', version)


def GetClientInstance(version='v1', no_http=False):
  return apis.GetClientInstance('ml', version, no_http=no_http)


class JobsClient(object):
  """Client for jobs service in the Cloud ML Engine API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance('v1')
    self.messages = messages or self.client.MESSAGES_MODULE

  @property
  def state_enum(self):
    return self.messages.GoogleCloudMlV1Job.StateValueValuesEnum

  def List(self, project_ref):
    req = self.messages.MlProjectsJobsListRequest(
        parent=project_ref.RelativeName())
    return list_pager.YieldFromList(
        self.client.projects_jobs, req, field='jobs',
        batch_size_attribute='pageSize')

  @property
  def job_class(self):
    return self.messages.GoogleCloudMlV1Job

  @property
  def training_input_class(self):
    return self.messages.GoogleCloudMlV1TrainingInput

  @property
  def prediction_input_class(self):
    return self.messages.GoogleCloudMlV1PredictionInput

  def _MakeCreateRequest(self, parent=None, job=None):
    return self.messages.MlProjectsJobsCreateRequest(
        parent=parent,
        googleCloudMlV1Job=job)

  def Create(self, project_ref, job):
    return self.client.projects_jobs.Create(
        self._MakeCreateRequest(
            parent=project_ref.RelativeName(),
            job=job))

  def Cancel(self, job_ref):
    """Cancels given job."""
    req = self.messages.MlProjectsJobsCancelRequest(name=job_ref.RelativeName())
    return self.client.projects_jobs.Cancel(req)

  def Get(self, job_ref):
    req = self.messages.MlProjectsJobsGetRequest(name=job_ref.RelativeName())
    return self.client.projects_jobs.Get(req)

  def BuildTrainingJob(self,
                       path=None,
                       module_name=None,
                       job_name=None,
                       trainer_uri=None,
                       region=None,
                       job_dir=None,
                       scale_tier=None,
                       user_args=None,
                       runtime_version=None):
    """Builds a Cloud ML Engine Job from a config file and/or flag values.

    Args:
        path: path to a yaml configuration file
        module_name: value to set for moduleName field (overrides yaml file)
        job_name: value to set for jobName field (overrides yaml file)
        trainer_uri: List of values to set for trainerUri field (overrides yaml
          file)
        region: compute region in which to run the job (overrides yaml file)
        job_dir: Cloud Storage working directory for the job (overrides yaml
          file)
        scale_tier: ScaleTierValueValuesEnum the scale tier for the job
          (overrides yaml file)
        user_args: [str]. A list of arguments to pass through to the job.
        (overrides yaml file)
        runtime_version: the runtime version in which to run the job (overrides
          yaml file)
    Returns:
        A constructed Job object.
    """
    job = self.job_class()

    if path:
      with open(path) as config_file:
        data = yaml.load(config_file)
      if data:
        job = encoding.DictToMessage(data, self.job_class)

    if job_name:
      job.jobId = job_name

    if not job.trainingInput:
      job.trainingInput = self.training_input_class()
    additional_fields = {
        'pythonModule': module_name,
        'args': user_args,
        'packageUris': trainer_uri,
        'region': region,
        'jobDir': job_dir,
        'scaleTier': scale_tier,
        'runtimeVersion': runtime_version
    }
    for field_name, value in additional_fields.items():
      if value is not None:
        setattr(job.trainingInput, field_name, value)

    return job

  def BuildBatchPredictionJob(self,
                              job_name=None,
                              model_dir=None,
                              model_name=None,
                              version_name=None,
                              input_paths=None,
                              data_format=None,
                              output_path=None,
                              region=None,
                              runtime_version=None,
                              max_worker_count=None):
    """Builds a Cloud ML Engine Job for batch prediction from flag values.

    Args:
        job_name: value to set for jobName field
        model_dir: str, Google Cloud Storage location of the model files
        model_name: str, value to set for modelName field
        version_name: str, value to set for versionName field
        input_paths: list of input files
        data_format: format of the input files
        output_path: single value for the output location
        region: compute region in which to run the job
        runtime_version: the runtime version in which to run the job
        max_worker_count: int, the maximum number of workers to use
    Returns:
        A constructed Job object.
    """
    project_id = properties.VALUES.core.project.GetOrFail()

    prediction_input = self.prediction_input_class(
        inputPaths=input_paths,
        outputPath=output_path,
        region=region,
        runtimeVersion=runtime_version,
        maxWorkerCount=max_worker_count)
    prediction_input.dataFormat = prediction_input.DataFormatValueValuesEnum(
        data_format)
    if model_dir:
      prediction_input.uri = model_dir
    elif version_name:
      version_ref = resources.REGISTRY.Parse(
          version_name, collection='ml.projects.models.versions',
          params={'modelsId': model_name, 'projectsId': project_id})
      prediction_input.versionName = version_ref.RelativeName()
    else:
      model_ref = resources.REGISTRY.Parse(
          model_name, collection='ml.projects.models',
          params={'projectsId': project_id})
      prediction_input.modelName = model_ref.RelativeName()

    return self.job_class(
        jobId=job_name,
        predictionInput=prediction_input
    )
