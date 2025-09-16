# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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

from googlecloudsdk.api_lib.clouddeploy import client_util
from googlecloudsdk.command_lib.deploy import automation_util
from googlecloudsdk.command_lib.deploy import custom_target_type_util
from googlecloudsdk.command_lib.deploy import deploy_policy_util
from googlecloudsdk.command_lib.deploy import manifest_util
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import log


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

  def CreateResources(self, manifests, region):
    """Creates Cloud Deploy resources.

    Asynchronously calls the API then iterate the operations
    to check the status.

    Args:
     manifests: the list of parsed resource yaml definitions.
     region: location ID.
    """
    resource_dict = manifest_util.ParseDeployConfig(
        self.messages, manifests, region
    )
    msg_template = 'Created Cloud Deploy resource: {}.'
    operation_dict = {
        resource.name: self.CreateDeliveryPipeline(resource)
        for resource in resource_dict[
            manifest_util.ResourceKind.DELIVERY_PIPELINE
        ]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    operation_dict = {
        resource.name: target_util.PatchTarget(resource)
        for resource in resource_dict[manifest_util.ResourceKind.TARGET]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    # Create automation resource.
    operation_dict = {
        resource.name: automation_util.PatchAutomation(resource)
        for resource in resource_dict[manifest_util.ResourceKind.AUTOMATION]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    # Create custom target type resource.
    operation_dict = {
        resource.name: custom_target_type_util.PatchCustomTargetType(resource)
        for resource in resource_dict[
            manifest_util.ResourceKind.CUSTOM_TARGET_TYPE
        ]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    # Create deploy policy resource.
    operation_dict = {
        resource.name: deploy_policy_util.PatchDeployPolicy(resource)
        for resource in resource_dict[manifest_util.ResourceKind.DEPLOY_POLICY]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

  def DeleteResources(self, manifests, region, force):
    """Delete Cloud Deploy resources.

    Asynchronously calls the API then iterate the operations
    to check the status.

    Args:
     manifests: [str], the list of parsed resource yaml definitions.
     region: str, location ID.
     force: bool, if true, the delivery pipeline with sub-resources will be
       deleted and its sub-resources will also be deleted.
    """
    resource_dict = manifest_util.ParseDeployConfig(
        self.messages, manifests, region
    )
    msg_template = 'Deleted Cloud Deploy resource: {}.'
    operation_dict = {
        resource.name: target_util.DeleteTarget(resource.name)
        for resource in resource_dict[manifest_util.ResourceKind.TARGET]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    operation_dict = {
        resource.name: custom_target_type_util.DeleteCustomTargetType(
            resource.name
        )
        for resource in resource_dict[
            manifest_util.ResourceKind.CUSTOM_TARGET_TYPE
        ]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    operation_dict = {
        resource.name: automation_util.DeleteAutomation(resource.name)
        for resource in resource_dict[manifest_util.ResourceKind.AUTOMATION]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    operation_dict = {
        resource.name: self.DeleteDeliveryPipeline(resource, force)
        for resource in resource_dict[
            manifest_util.ResourceKind.DELIVERY_PIPELINE
        ]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

    operation_dict = {
        resource.name: deploy_policy_util.DeleteDeployPolicy(resource.name)
        for resource in resource_dict[manifest_util.ResourceKind.DEPLOY_POLICY]
    }
    self.operation_client.CheckOperationStatus(operation_dict, msg_template)

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
            updateMask=manifest_util.PIPELINE_UPDATE_MASK,
        )
    )

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
        self.messages.ClouddeployProjectsLocationsDeliveryPipelinesDeleteRequest(
            allowMissing=True, name=pipeline_config.name, force=force
        )
    )
