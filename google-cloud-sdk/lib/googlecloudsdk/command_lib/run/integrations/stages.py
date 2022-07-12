# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Gather stage/condition information for any important objects here."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.core.console import progress_tracker


UPDATE_APPLICATION = 'UpdateApplication'
CREATE_DEPLOYMENT = 'CreateDeployment'
UNDEPLOY_RESOURCE = 'UndeployResource'
CLEANUP_CONFIGURATION = 'CleanupConfiguration'
_DEPLOY_STAGE_PREFIX = 'Deploy_'


def _UpdateApplicationStage(create):
  """Returns the stage for updating the Application.

  Args:
    create: whether it's for the create command.

  Returns:
    progress_tracker.Stage
  """
  if create:
    message = 'Saving Configuration for Integration...'
  else:
    message = 'Updating Configuration for Integration...'

  return progress_tracker.Stage(message, key=UPDATE_APPLICATION)


def IntegrationStages(create, match_type_names):
  """Returns the progress tracker Stages for creating or updating an Integration.

  Args:
    create: whether it's for the create command.
    match_type_names: list of dict typed names. Dict is of the form:
                      {'type':string, 'name':string}.

  Returns:
    dict of stage key to progress_tracker Stage.
  """

  stages = {UPDATE_APPLICATION: _UpdateApplicationStage(create)}
  stages[CREATE_DEPLOYMENT] = progress_tracker.Stage(
      'Configuring Integration...', key=CREATE_DEPLOYMENT)
  deploy_stages = _DeployStages(match_type_names, 'Configuring ')
  stages.update(deploy_stages)

  return stages


# TODO(b/237396542): Add this to integration type metadata map.
def _TypeToDescriptiveName(resource_type):
  """Returns a more readable name for a resource type, for printing to console.

  Args:
    resource_type: type to be described.

  Returns:
    string with readable type name.
  """
  if resource_type == 'router':
    return 'Load Balancer'
  elif resource_type == 'service':
    return 'Cloud Run Service'
  elif resource_type == 'redis':
    return 'Redis Instance'
  elif resource_type == 'vpc':
    return 'VPC Connector'
  elif resource_type == 'cloudsql':
    return 'Cloud SQL Instance'
  return resource_type


def IntegrationDeleteStages(service_match_type_names, delete_match_type_names):
  """Returns the progress tracker Stages for deleting an Integration.

  Args:
    service_match_type_names: the (selector) match type names for services that
      must be updated, as a  list of dicts. Dict is of the form: {'type':string,
      'name':string}.
    delete_match_type_names: the (selector) match type names for resoruces that
      must be destroyed, , as a  list of dicts. Dict is of the form:
      {'type':string, 'name':string}.

  Returns:
    list of progress_tracker.Stage
  """
  stages = {}
  if service_match_type_names:
    stages[UPDATE_APPLICATION] = progress_tracker.Stage(
        'Unbinding services...', key=UPDATE_APPLICATION)
    stages[CREATE_DEPLOYMENT] = progress_tracker.Stage(
        'Configuring resources...', key=CREATE_DEPLOYMENT)
    service_stages = _DeployStages(service_match_type_names, 'Configuring ')
    stages.update(service_stages)
  stages[UNDEPLOY_RESOURCE] = progress_tracker.Stage(
      'Deleting resources...', key=UNDEPLOY_RESOURCE)
  undeploy_stages = _DeployStages(delete_match_type_names, 'Deleting ')
  stages.update(undeploy_stages)
  stages[CLEANUP_CONFIGURATION] = progress_tracker.Stage(
      'Saving Integration configurations...', key=CLEANUP_CONFIGURATION)
  return stages


def ApplyStages():
  """Returns the progress tracker Stages for apply command.

  Returns:
    array of progress_tracker.Stage
  """
  return [
      progress_tracker.Stage('Saving Configuration...', key=UPDATE_APPLICATION),
      progress_tracker.Stage(
          'Actuating Configuration...', key=CREATE_DEPLOYMENT),
  ]


def StageKeyForResourceDeployment(resource_type):
  """Returns the stage key for the step that deploys a resource type.

  Args:
    resource_type: The resource type string.

  Returns:
    stage key for deployment of type.
  """
  return _DEPLOY_STAGE_PREFIX + resource_type


def _DeployStages(match_type_names, stage_prefix):
  """Appends a deploy stage for each resource type in match_type_names.

  Args:
    match_type_names: The (selector) match type names as a list of dict of
      {'type': string, 'name': string}
    stage_prefix: string. The prefix to add to the stage message.

  Returns:
    dict of stage key to progress_tracker Stage.
  """
  if not match_type_names:
    return {}
  stages = {}
  resource_types = set()
  for type_name in match_type_names:
    resource_types.add(type_name['type'])

  for resource_type in resource_types:
    message = stage_prefix + _TypeToDescriptiveName(resource_type) + '...'
    stages[StageKeyForResourceDeployment(
        resource_type)] = progress_tracker.Stage(
            message, key=StageKeyForResourceDeployment(resource_type))

  return stages
