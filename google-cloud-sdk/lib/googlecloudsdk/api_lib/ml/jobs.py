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


def Cancel(job):
  client = apis.GetClientInstance('ml', 'v1alpha3')
  msgs = apis.GetMessagesModule('ml', 'v1alpha3')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.operations')
  req = msgs.MlProjectsOperationsCancelRequest(
      projectsId=res.projectsId, operationsId=res.Name())
  resp = client.projects_operations.Cancel(req)
  return resp


def Get(job):
  client = apis.GetClientInstance('ml', 'v1alpha3')
  res = resources.REGISTRY.Parse(job, collection='ml.projects.operations')
  req = res.Request()
  resp = client.projects_operations.Get(req)
  return resp


def List():
  client = apis.GetClientInstance('ml', 'v1alpha3')
  msgs = apis.GetMessagesModule('ml', 'v1alpha3')
  req = msgs.MlProjectsOperationsListRequest(
      projectsId=properties.VALUES.core.project.Get())
  return list_pager.YieldFromList(
      client.projects_operations,
      req,
      field='operations',
      batch_size_attribute='pageSize')


def Train(config):
  client = apis.GetClientInstance('ml', 'v1alpha3')
  msgs = apis.GetMessagesModule('ml', 'v1alpha3')
  req = msgs.MlProjectsSubmitTrainingJobRequest(
      projectsId=properties.VALUES.core.project.Get(),
      googleCloudMlV1alpha3SubmitTrainingJobRequest=config)
  resp = client.projects.SubmitTrainingJob(req)
  return resp


def BuildTrainingConfig(path=None,
                        module_name=None,
                        job_name=None,
                        trainer_uri=None):
  """Builds a SubmitTrainingJobRequest from a config file and/or flag values.

  Args:
      path: path to a yaml configuration file
      module_name: value to set for moduleName field (overrides yaml file)
      job_name: value to set for jobName field (overrides yaml file)
      trainer_uri: single value to set for trainerUri field (overrides yaml
        file)
  Returns:
      A constructed GoogleCloudMlV1alpha3SubmitTrainingJobRequest object.
  """
  request_class = apis.GetMessagesModule(
      'ml', 'v1alpha3').GoogleCloudMlV1alpha3SubmitTrainingJobRequest
  if not path:
    obj = request_class()
  else:
    data = yaml.load(open(path))
    if not data:
      obj = request_class()
    else:
      obj = encoding.DictToMessage(data, request_class)
  if module_name:
    obj.moduleName = module_name
  if job_name:
    obj.jobName = job_name
  if trainer_uri:
    obj.trainerUri = trainer_uri
  return obj
