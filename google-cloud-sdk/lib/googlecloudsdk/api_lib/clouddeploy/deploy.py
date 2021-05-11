# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Support library to handle the deploy subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

PIPELINE_UPDATE_MASK = 'description,annotations,labels,serial_pipeline,render_service_account'
TARGET_UPDATE_MASK = 'description,annotations,labels,approval_required,deploy_service_account,gke_cluster'
DELIVERY_PIPELINE_KIND = 'delivery-pipeline'
TARGET_KIND = 'target'


class DeployClient(object):
  """Client for managing Cloud Deploy delivery pipeline and target resources."""

  def __init__(self, client=None, messages=None):
    """Initialize a deploy.DeployClient.

    Args:
      client: base_api.BaseApiClient, the client class for Cloud Deploy.
      messages: module containing the definitions of messages for Cloud Deploy.
    """
    self.client = client or client_util.GetClientInstance()
    self.operation_client = client_util.OperationsClient()
    self.messages = messages or client_util.GetMessagesModule(client)
    self._pipeline_service = self.client.projects_locations_deliveryPipelines
    self._target_service = self.client.projects_locations_deliveryPipelines_targets

  def ParseDeployConfig(self, configs, region):
    """Parses the declarative definition of the resources into message.

    Args:
      configs: the list of parsed resource yaml definitions.
      region: location ID.

    Returns:
      A dictionary of resource kind and message.
    Raises:
      exception.Error, if the declarative definition is incorrect.
    """
    resource_dict = {DELIVERY_PIPELINE_KIND: [], TARGET_KIND: []}
    project = properties.VALUES.core.project.GetOrFail()
    for config in configs:
      if 'kind' not in config or config['kind'] is None:
        raise exceptions.Error('missing required field .kind')
      kind = config['kind']
      if 'name' not in config or config['name'] is None:
        raise exceptions.Error(
            'missing required field .name in {}'.format(kind))
      if kind == DELIVERY_PIPELINE_KIND:
        resource = self.messages.DeliveryPipeline()
        resource_ref = resources.REGISTRY.Parse(
            config['name'],
            collection='clouddeploy.projects.locations.deliveryPipelines',
            params={
                'projectsId': project,
                'locationsId': region,
                'deliveryPipelinesId': config['name'],
            })
        resource.name = resource_ref.RelativeName()
      elif kind == TARGET_KIND:
        if ('deliveryPipeline' not in config or not config['deliveryPipeline']):
          raise exceptions.Error(
              'missing required field .deliveryPipeline in target {}'.format(
                  config['name']))
        resource = self.messages.Target()
        resource_ref = resources.REGISTRY.Parse(
            config['name'],
            collection='clouddeploy.projects.locations.deliveryPipelines.targets',
            params={
                'projectsId': project,
                'locationsId': region,
                'deliveryPipelinesId': config['deliveryPipeline'],
                'targetsId': config['name']
            })
        resource.name = resource_ref.RelativeName()
      else:
        raise exceptions.Error('kind {} not supported'.format(kind))
      if '/' in resource_ref.Name():
        raise exceptions.Error('resource ID "{}" contains /.'.format(
            resource_ref.Name()))

      for field in config.keys():
        if field not in ['apiVersion', 'kind', 'deliveryPipeline', 'name']:
          setattr(resource, field, config[field])

      resource_dict[kind].append(resource)

    return resource_dict

  def CreateResources(self, resource_dict):
    """Creates Cloud Deploy resources.

    Asynchronously calls the API then iterate the operations
    to check the status.

    Args:
     resource_dict: dict[str, optional[list], dictionary of kind
       (delivery-pipeline|target) and its resources. The resource list can be
       empty.
    """
    msg_template = 'Created Cloud Deploy resource: {}.'
    # Create delivery pipeline first.
    if resource_dict[DELIVERY_PIPELINE_KIND]:
      operation_dict = {}
      for resource in resource_dict[DELIVERY_PIPELINE_KIND]:
        operation_dict[resource.name] = self.CreateDeliveryPipeline(resource)
      self._CheckOperationStatus(operation_dict, msg_template)
    if resource_dict[TARGET_KIND]:
      operation_dict = {}
      for resource in resource_dict[TARGET_KIND]:
        operation_dict[resource.name] = self.CreateTarget(resource)
      self._CheckOperationStatus(operation_dict, msg_template)

  def DeleteResources(self, resource_dict, force):
    """Delete Cloud Deploy resources.

    Asynchronously calls the API then iterate the operations
    to check the status.

    Args:
     resource_dict: dict[str, optional[list], dictionary of kind
       (delivery-pipeline|target) and its resources. The resource list can be
       empty.
     force: bool, if true, the delivery pipeline with sub-resources will be
       deleted and its sub-resources will also be deleted.
    """

    msg_template = 'Deleted Cloud Deploy resource: {}.'
    # Delete targets first.
    if resource_dict[TARGET_KIND]:
      operation_dict = {}
      for resource in resource_dict[TARGET_KIND]:
        operation_dict[resource.name] = self.DeleteTarget(resource)
      self._CheckOperationStatus(operation_dict, msg_template)
    if resource_dict[DELIVERY_PIPELINE_KIND]:
      operation_dict = {}
      for resource in resource_dict[DELIVERY_PIPELINE_KIND]:
        operation_dict[resource.name] = self.DeleteDeliveryPipeline(
            resource, force)
      self._CheckOperationStatus(operation_dict, msg_template)

  def _CheckOperationStatus(self, operation_dict, msg_template):
    """Checks operations status.

    Only logs the errors instead of re-throwing them.

    Args:
     operation_dict: dict[str, oOptional[clouddeploy_messages.Operation],
       dictionary of resource name and clouddeploy_messages.Operation. The
       operation can be None if the operation isn't executed.
     msg_template: output string template.
    """
    for resource_name, operation in operation_dict.items():
      if not operation or not operation.name:
        continue
      try:
        operation_ref = resources.REGISTRY.ParseRelativeName(
            operation.name,
            collection='clouddeploy.projects.locations.operations')
        response_msg = self.operation_client.WaitForOperation(
            operation, operation_ref,
            'Waiting for the operation on resource {}'.format(
                resource_name)).response
        if response_msg is not None:
          response = encoding.MessageToPyValue(response_msg)
          if 'name' in response:
            log.status.Print(msg_template.format(response['name']))

      except exceptions.Error as e:
        log.status.Print('Operation failed: {}'.format(e))

  def CreateDeliveryPipeline(self, pipeline_config):
    """Creates a delivery pipeline resource.

    Args:
      pipeline_config: apitools.base.protorpclite.messages.Message, delivery
        pipeline message.

    Returns:
      The operation message.
    """
    log.debug('Creating delivery pipeline: ' + repr(pipeline_config))
    return self._pipeline_service.Patch(
        self.messages.ClouddeployProjectsLocationsDeliveryPipelinesPatchRequest(
            deliveryPipeline=pipeline_config,
            allowMissing=True,
            name=pipeline_config.name,
            updateMask=PIPELINE_UPDATE_MASK))

  def CreateTarget(self, target_config):
    """Creates a target resource.

    Args:
      target_config: apitools.base.protorpclite.messages.Message, target
        message.

    Returns:
      The operation message.
    """
    log.debug('Creating target: ' + repr(target_config))
    return self._target_service.Patch(
        self.messages
        .ClouddeployProjectsLocationsDeliveryPipelinesTargetsPatchRequest(
            target=target_config,
            allowMissing=True,
            name=target_config.name,
            updateMask=TARGET_UPDATE_MASK))

  def DeleteDeliveryPipeline(self, pipeline_config, force):
    """Deletes a delivery pipeline resource.

    Args:
      pipeline_config: apitools.base.protorpclite.messages.Message, delivery
        pipeline message.
      force: if true, the delivery pipeline with sub-resources will be deleted
        and its sub-resources will also be deleted.

    Returns:
      The operation message. It could be none if the resource doesn't exist.
    """
    log.debug('Deleting delivery pipeline: ' + repr(pipeline_config))
    return self._pipeline_service.Delete(
        self.messages
        .ClouddeployProjectsLocationsDeliveryPipelinesDeleteRequest(
            allowMissing=True, name=pipeline_config.name, force=force))

  def DeleteTarget(self, target_config):
    """Deletes a target resource.

    Args:
      target_config: apitools.base.protorpclite.messages.Message, target
        message.

    Returns:
      The operation message. It could be none if the resource doesn't exist.
    """
    log.debug('Deleting target: ' + repr(target_config))
    return self._target_service.Delete(
        self.messages
        .ClouddeployProjectsLocationsDeliveryPipelinesTargetsDeleteRequest(
            allowMissing=True, name=target_config.name))
