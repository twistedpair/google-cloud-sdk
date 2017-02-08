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
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
import yaml


def GetMessagesModule():
  return apis.GetMessagesModule('ml', 'v1beta1')


def GetClientInstance(no_http=False):
  return apis.GetClientInstance('ml', 'v1beta1', no_http=no_http)


class JobsClient(object):
  """Client for jobs service in the Cloud ML API."""

  def __init__(self, client=None, messages=None):
    self.client = client or GetClientInstance()
    self.messages = messages or GetMessagesModule()

  @property
  def state_enum(self):
    return self.messages.GoogleCloudMlV1beta1Job.StateValueValuesEnum

  def List(self, project_ref):
    req = self.messages.MlProjectsJobsListRequest(
        parent=project_ref.RelativeName())
    return list_pager.YieldFromList(
        self.client.projects_jobs, req, field='jobs',
        batch_size_attribute='pageSize')

  def Create(self, project_ref, job):
    req = self.messages.MlProjectsJobsCreateRequest(
        parent=project_ref.RelativeName(),
        googleCloudMlV1beta1Job=job)
    return self.client.projects_jobs.Create(req)

  def Cancel(self, job_ref):
    """Cancels given job."""
    req = self.messages.MlProjectsJobsCancelRequest(name=job_ref.RelativeName())
    return self.client.projects_jobs.Cancel(req)

  def Get(self, job_ref):
    req = self.messages.MlProjectsJobsGetRequest(name=job_ref.RelativeName())
    return self.client.projects_jobs.Get(req)


def BuildTrainingJob(path=None,
                     module_name=None,
                     job_name=None,
                     trainer_uri=None,
                     region=None,
                     job_dir=None,
                     scale_tier=None,
                     user_args=None,
                     runtime_version=None):
  """Builds a GoogleCloudMlV1beta1Job from a config file and/or flag values.

  Args:
      path: path to a yaml configuration file
      module_name: value to set for moduleName field (overrides yaml file)
      job_name: value to set for jobName field (overrides yaml file)
      trainer_uri: List of values to set for trainerUri field (overrides yaml
        file)
      region: compute region in which to run the job (overrides yaml file)
      job_dir: Cloud Storage working directory for the job (overrides yaml file)
      scale_tier: ScaleTierValueValuesEnum the scale tier for the job (overrides
        yaml file)
      user_args: [str]. A list of arguments to pass through to the job.
      (overrides yaml file)
      runtime_version: the runtime version in which to run the job (overrides
        yaml file)
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  messages = GetMessagesModule()
  job = messages.GoogleCloudMlV1beta1Job()

  if path:
    with open(path) as config_file:
      data = yaml.load(config_file)
    if data:
      job = encoding.DictToMessage(data, messages.GoogleCloudMlV1beta1Job)

  if job_name:
    job.jobId = job_name

  if not job.trainingInput:
    job.trainingInput = messages.GoogleCloudMlV1beta1TrainingInput()
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


def BuildBatchPredictionJob(job_name=None,
                            model_name=None,
                            version_name=None,
                            input_paths=None,
                            data_format=None,
                            output_path=None,
                            region=None,
                            runtime_version=None):
  """Builds a GoogleCloudMlV1beta1Job for batch prediction from flag values.

  Args:
      job_name: value to set for jobName field
      model_name: str, value to set for modelName field
      version_name: str, value to set for versionName field
      input_paths: list of input files
      data_format: format of the input files
      output_path: single value for the output location
      region: compute region in which to run the job
      runtime_version: the runtime version in which to run the job
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  messages = GetMessagesModule()

  project_id = properties.VALUES.core.project.Get()

  prediction_input = messages.GoogleCloudMlV1beta1PredictionInput(
      inputPaths=input_paths,
      outputPath=output_path,
      region=region,
      runtimeVersion=runtime_version
  )
  prediction_input.dataFormat = prediction_input.DataFormatValueValuesEnum(
      data_format)
  if version_name:
    version_ref = resources.REGISTRY.Parse(
        version_name, collection='ml.projects.models.versions',
        params={'modelsId': model_name, 'projectsId': project_id})
    prediction_input.versionName = version_ref.RelativeName()
  else:
    model_ref = resources.REGISTRY.Parse(
        model_name, collection='ml.projects.models',
        params={'projectsId': project_id})
    prediction_input.modelName = model_ref.RelativeName()

  return messages.GoogleCloudMlV1beta1Job(
      jobId=job_name,
      predictionInput=prediction_input
  )
