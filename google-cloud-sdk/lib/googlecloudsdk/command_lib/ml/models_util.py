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
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def ParseModel(model):
  """Parses a model ID into a model resource object."""
  return resources.REGISTRY.Parse(model, collection='ml.projects.models')


def Create(models_client, model, regions=None, enable_logging=None):
  if regions is None:
    log.warn('`--regions` flag will soon be required. Please explicitly '
             'specify a region. Using [us-central1] by default.')
    regions = ['us-central1']
  return models_client.Create(model, regions, enable_logging)


def Delete(models_client, operations_client, model):
  op = models_client.Delete(model)

  return operations_client.WaitForOperation(
      op, message='Deleting model [{}]'.format(model)).response


def List(models_client):
  project_ref = resources.REGISTRY.Parse(
      properties.VALUES.core.project.Get(required=True),
      collection='ml.projects')
  return models_client.List(project_ref)
