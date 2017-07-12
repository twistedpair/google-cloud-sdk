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
"""Utilities for ml-engine models commands."""
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io


MODELS_COLLECTION = 'ml.projects.models'


def ParseModel(model):
  """Parses a model ID into a model resource object."""
  return resources.REGISTRY.Parse(
      model,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection=MODELS_COLLECTION)


def Create(models_client, model, regions=None, enable_logging=None):
  if regions is None:
    log.warn('`--regions` flag will soon be required. Please explicitly '
             'specify a region. Using [us-central1] by default.')
    regions = ['us-central1']
  return models_client.Create(model, regions, enable_logging)


def Delete(models_client, operations_client, model):
  console_io.PromptContinue('This will delete model [{}]...'.format(model),
                            cancel_on_no=True)
  op = models_client.Delete(model)

  return operations_client.WaitForOperation(
      op, message='Deleting model [{}]'.format(model)).response


def List(models_client):
  project_ref = resources.REGISTRY.Parse(
      properties.VALUES.core.project.GetOrFail(),
      collection='ml.projects')
  return models_client.List(project_ref)


def GetIamPolicy(models_client, model):
  model_ref = ParseModel(model)
  return models_client.GetIamPolicy(model_ref)


def SetIamPolicy(models_client, model, policy_file):
  model_ref = ParseModel(model)
  policy = iam_util.ParseJsonPolicyFile(
      policy_file, models_client.messages.GoogleIamV1Policy)
  update_mask = iam_util.ConstructUpdateMaskFromPolicy(policy_file)
  iam_util.LogSetIamPolicy(model_ref.Name(), 'model')
  return models_client.SetIamPolicy(model_ref, policy, update_mask)


def AddIamPolicyBinding(models_client, model, member, role):
  model_ref = ParseModel(model)
  policy = models_client.GetIamPolicy(model_ref)
  iam_util.AddBindingToIamPolicy(models_client.messages.GoogleIamV1Binding,
                                 policy, member, role)
  return models_client.SetIamPolicy(model_ref, policy, 'bindings,etag')


def RemoveIamPolicyBinding(models_client, model, member, role):
  model_ref = ParseModel(model)
  policy = models_client.GetIamPolicy(model_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return models_client.SetIamPolicy(model_ref, policy, 'bindings,etag')
