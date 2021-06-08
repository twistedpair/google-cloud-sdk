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
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.resource import resource_property

PIPELINE_UPDATE_MASK = 'description,annotations,labels,serial_pipeline,render_service_account'
TARGET_UPDATE_MASK = 'description,annotations,labels,approval_required,deploy_service_account,gke_cluster'
DELIVERY_PIPELINE_KIND_BETA1 = 'delivery-pipeline'
TARGET_KIND_BETA1 = 'target'
DELIVERY_PIPELINE_KIND_V1BETA1 = 'DeliveryPipeline'
TARGET_KIND_V1BETA1 = 'Target'
API_VERSION_V1BETA1 = 'deploy.cloud.google.com/v1beta1'
API_VERSION_BETA1 = 'cloudDeploy/beta1'
TARGET_TYPE = 'target'
DELIVERY_PIPELINE_TYPE = 'delivery-pipeline'
DELIVERY_PIPELINE_LABEL = 'deliveryPipeline'


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
    resource_dict = {
        DELIVERY_PIPELINE_KIND_BETA1: [],
        TARGET_KIND_BETA1: [],
        DELIVERY_PIPELINE_KIND_V1BETA1: [],
        TARGET_KIND_V1BETA1: []
    }
    project = properties.VALUES.core.project.GetOrFail()
    for config in configs:
      if config.get('apiVersion') is None:
        raise exceptions.CloudDeployConfigError(
            'missing required field .apiVersion')
      if config.get('kind') is None:
        raise exceptions.CloudDeployConfigError('missing required field .kind')
      api_version = config['apiVersion']
      if api_version == API_VERSION_BETA1:
        self._ParseBeta1Config(config['kind'], config, project, region,
                               resource_dict)
      elif api_version == API_VERSION_V1BETA1:
        self._ParseV1Beta1Config(config['kind'], config, project, region,
                                 resource_dict)
      else:
        raise exceptions.CloudDeployConfigError(
            'api version {} not supported'.format(api_version))

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
    # In case user has both types of pipeline definition in the same
    # config file.
    pipelines = resource_dict[DELIVERY_PIPELINE_KIND_BETA1] + resource_dict[
        DELIVERY_PIPELINE_KIND_V1BETA1]
    if pipelines:
      operation_dict = {}
      for resource in pipelines:
        operation_dict[resource.name] = self.CreateDeliveryPipeline(resource)
      self._CheckOperationStatus(operation_dict, msg_template)
    # In case user has both types of target definition in the same
    # config file.
    targets = resource_dict[TARGET_KIND_BETA1] + resource_dict[
        TARGET_KIND_V1BETA1]
    if targets:
      operation_dict = {}
      for resource in targets:
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
    targets = resource_dict[TARGET_KIND_BETA1] + resource_dict[
        TARGET_KIND_V1BETA1]
    if targets:
      operation_dict = {}
      for resource in targets:
        operation_dict[resource.name] = self.DeleteTarget(resource)
      self._CheckOperationStatus(operation_dict, msg_template)
    pipelines = resource_dict[DELIVERY_PIPELINE_KIND_BETA1] + resource_dict[
        DELIVERY_PIPELINE_KIND_V1BETA1]
    if pipelines:
      operation_dict = {}
      for resource in pipelines:
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

      except core_exceptions.Error as e:
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

  def _ParseV1Beta1Config(self, kind, config, project, region, resource_dict):
    """Parses the Cloud Deploy v1beta1 resource specifications into message.

       This specification version is KRM complied and should be used after
       private review.

    Args:
       kind: str, name of the resource schema.
       config: dict[str,str], cloud deploy resource yaml definition.
       project: str, gcp project.
       region: str, ID of the location.
       resource_dict: dict[str,optional[message]], a dictionary of resource kind
         and message.
    """
    metadata = config.get('metadata')
    if not metadata or not metadata.get('name'):
      raise exceptions.CloudDeployConfigError(
          'missing required field .metadata.name in {}'.format(kind))
    if kind == DELIVERY_PIPELINE_KIND_V1BETA1:
      resource_type = DELIVERY_PIPELINE_TYPE
      resource, resource_ref = self._CreateDeliveryPipelineResource(
          metadata['name'], project, region)
    elif kind == TARGET_KIND_V1BETA1:
      resource_type = TARGET_TYPE
      if config.get('deliveryPipeline') is None:
        raise exceptions.CloudDeployConfigError(
            'missing required field .deliveryPipeline in target {}'.format(
                metadata['name']))
      resource, resource_ref = self._CreateTargetResource(
          metadata['name'], config['deliveryPipeline'], project, region)
    else:
      raise exceptions.CloudDeployConfigError(
          'kind {} not supported'.format(kind))

    if '/' in resource_ref.Name():
      raise exceptions.CloudDeployConfigError(
          'resource ID "{}" contains /.'.format(resource_ref.Name()))

    for field in config:
      if field not in ['apiVersion', 'kind', 'metadata', 'deliveryPipeline']:
        setattr(resource, field, config.get(field))
    # Sets the properties in metadata.
    for field in metadata:
      if field not in ['name', 'annotations', 'labels']:
        setattr(resource, field, metadata.get(field))
    SetMetadata(self.messages, resource, resource_type,
                metadata.get('annotations'), metadata.get('labels'))

    resource_dict[kind].append(resource)

  def _ParseBeta1Config(self, kind, config, project, region, resource_dict):
    """Parses the Cloud Deploy beta1 resource specifications into message.

      This specification version shouldn't be used after private review.

    Args:
      kind: str, name of the resource schema.
      config: dict[str,str], cloud deploy resource yaml definition.
      project: str, gcp project.
      region: str, ID of the location.
      resource_dict: dict[str,optional[message]], a dictionary of resource kind
        and message.
    """
    if config.get('name') is None:
      raise exceptions.CloudDeployConfigError(
          'missing required field .name in {}'.format(kind))
    if kind == DELIVERY_PIPELINE_KIND_BETA1:
      resource, resource_ref = self._CreateDeliveryPipelineResource(
          config['name'], project, region)
      resource_type = DELIVERY_PIPELINE_TYPE
    elif kind == TARGET_KIND_BETA1:
      if config.get('deliveryPipeline') is None:
        raise exceptions.CloudDeployConfigError(
            'missing required field .deliveryPipeline in target {}'.format(
                config['name']))
      resource, resource_ref = self._CreateTargetResource(
          config['name'], config['deliveryPipeline'], project, region)
      resource_type = TARGET_TYPE
    else:
      raise exceptions.CloudDeployConfigError(
          'kind {} not supported'.format(kind))

    if '/' in resource_ref.Name():
      raise exceptions.CloudDeployConfigError(
          'resource ID "{}" contains /.'.format(resource_ref.Name()))

    for field in config:
      if field not in [
          'apiVersion', 'kind', 'deliveryPipeline', 'name', 'annotations',
          'labels'
      ]:
        setattr(resource, field, config.get(field))

    SetMetadata(self.messages, resource, resource_type,
                config.get('annotations'), config.get('labels'))

    resource_dict[kind].append(resource)

  def _CreateTargetResource(self, target_name, delivery_pipeline_id, project,
                            region):
    """Creates target resource with full target name and the resource reference."""
    resource = self.messages.Target()
    resource_ref = resources.REGISTRY.Parse(
        target_name,
        collection='clouddeploy.projects.locations.deliveryPipelines.targets',
        params={
            'projectsId': project,
            'locationsId': region,
            'deliveryPipelinesId': delivery_pipeline_id,
            'targetsId': target_name
        })
    resource.name = resource_ref.RelativeName()

    return resource, resource_ref

  def _CreateDeliveryPipelineResource(self, delivery_pipeline_name, project,
                                      region):
    """Creates delivery pipeline resource with full delivery pipeline name and the resource reference."""
    resource = self.messages.DeliveryPipeline()
    resource_ref = resources.REGISTRY.Parse(
        delivery_pipeline_name,
        collection='clouddeploy.projects.locations.deliveryPipelines',
        params={
            'projectsId': project,
            'locationsId': region,
            'deliveryPipelinesId': delivery_pipeline_name,
        })
    resource.name = resource_ref.RelativeName()

    return resource, resource_ref


def SetMetadata(messages,
                message,
                resource_type,
                annotations=None,
                labels=None):
  """Sets the metadata of a cloud deploy resource message.

  Args:
   messages: module containing the definitions of messages for Cloud Deploy.
   message: message in googlecloudsdk.third_party.apis.cloudeploy.
   resource_type: str, the type of the resource to be updated.
   annotations: dict[str,str], a dict of annotation (key,value) pairs.
   labels: dict[str,str], a dict of label (key,value) pairs.
  """

  if annotations:
    if resource_type == DELIVERY_PIPELINE_TYPE:
      annotations_value_msg = messages.DeliveryPipeline.AnnotationsValue
    else:
      annotations_value_msg = messages.Target.AnnotationsValue
    av = annotations_value_msg()
    for k, v in annotations.items():
      av.additionalProperties.append(
          annotations_value_msg.AdditionalProperty(key=k, value=v))

    message.annotations = av

  if labels:
    if resource_type == DELIVERY_PIPELINE_TYPE:
      labels_value_msg = messages.DeliveryPipeline.LabelsValue
    else:
      labels_value_msg = messages.Target.LabelsValue
    lv = labels_value_msg()
    for k, v in labels.items():
      lv.additionalProperties.append(
          labels_value_msg.AdditionalProperty(
              # Base on go/unified-cloud-labels-proposal,
              # converts camel case key to snake case.
              key=resource_property.ConvertToSnakeCase(k),
              value=v))

    message.labels = lv
