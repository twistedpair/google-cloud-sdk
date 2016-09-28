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
from googlecloudsdk.core.util import files
import yaml


def Cancel(job):
  """Cancels given job."""
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.jobs')
  req = msgs.MlProjectsJobsCancelRequest(
      projectsId=res.projectsId, jobsId=res.Name())
  resp = client.projects_jobs.Cancel(req)
  return resp


def Get(job):
  client = apis.GetClientInstance('ml', 'v1beta1')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.jobs')
  req = res.Request()
  resp = client.projects_jobs.Get(req)
  return resp


def List():
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  req = msgs.MlProjectsJobsListRequest(
      projectsId=properties.VALUES.core.project.Get())
  return list_pager.YieldFromList(
      client.projects_jobs, req, field='jobs', batch_size_attribute='pageSize')


def Create(job):
  client = apis.GetClientInstance('ml', 'v1beta1')
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  req = msgs.MlProjectsJobsCreateRequest(
      projectsId=properties.VALUES.core.project.Get(),
      googleCloudMlV1beta1Job=job)
  resp = client.projects_jobs.Create(req)
  return resp


def BuildTrainingJob(path=None,
                     module_name=None,
                     job_name=None,
                     trainer_uri=None,
                     region=None,
                     user_args=None):
  """Builds a GoogleCloudMlV1beta1Job from a config file and/or flag values.

  Args:
      path: path to a yaml configuration file
      module_name: value to set for moduleName field (overrides yaml file)
      job_name: value to set for jobName field (overrides yaml file)
      trainer_uri: List of values to set for trainerUri field (overrides yaml
        file)
      region: compute region in which to run the job (overrides yaml file)
      user_args: [str]. A list of arguments to pass through to the job.
      (overrides yaml file)
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  request_class = msgs.GoogleCloudMlV1beta1Job
  obj = request_class()
  if path:
    with files.Context(open(path)) as config_file:
      data = yaml.load(config_file)
    if data:
      obj = encoding.DictToMessage(data, request_class)
  if not obj.trainingInput:
    obj.trainingInput = msgs.GoogleCloudMlV1beta1TrainingInput()
  if module_name:
    obj.trainingInput.pythonModule = module_name
  if user_args:
    obj.trainingInput.args = user_args
  if job_name:
    obj.jobId = job_name
  if trainer_uri:
    obj.trainingInput.packageUris = trainer_uri
  if region:
    obj.trainingInput.region = region
  return obj


def BuildBatchPredictionJob(job_name=None,
                            model_name=None,
                            version_name=None,
                            input_paths=None,
                            data_format=None,
                            output_path=None,
                            region=None):
  """Builds a GoogleCloudMlV1beta1Job for batch prediction from flag values.

  Args:
      job_name: value to set for jobName field
      model_name: value to set for modelName field
      version_name: value to set for versionName field
      input_paths: list of input files
      data_format: format of the input files
      output_path: single value for the output location
      region: compute region in which to run the job
  Returns:
      A constructed GoogleCloudMlV1beta1Job object.
  """
  msgs = apis.GetMessagesModule('ml', 'v1beta1')
  request_class = msgs.GoogleCloudMlV1beta1Job
  obj = request_class()
  obj.predictionInput = msgs.GoogleCloudMlV1beta1PredictionInput()

  obj.jobId = job_name
  project_id = properties.VALUES.core.project.Get()
  if version_name:
    # pylint: disable=g-backslash-continuation
    obj.predictionInput.versionName = 'projects/{0}/models/{1}/versions/{2}'. \
        format(project_id, model_name, version_name)
  else:
    # pylint: disable=g-backslash-continuation
    obj.predictionInput.modelName = \
        'projects/{0}/models/{1}'.format(project_id, model_name)
  obj.predictionInput.inputPaths = input_paths
  data_format_dict = {'TEXT': msgs.GoogleCloudMlV1beta1PredictionInput.
                              DataFormatValueValuesEnum.TEXT,
                      'TF_RECORD': msgs.GoogleCloudMlV1beta1PredictionInput.
                                   DataFormatValueValuesEnum.TF_RECORD}
  obj.predictionInput.dataFormat = data_format_dict[data_format]
  obj.predictionInput.outputPath = output_path
  obj.predictionInput.region = region
  return obj
