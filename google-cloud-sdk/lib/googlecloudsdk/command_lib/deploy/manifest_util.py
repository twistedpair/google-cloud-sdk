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
"""Utilities for parsing the cloud deploy resource to yaml definition."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
from googlecloudsdk.command_lib.deploy import exceptions
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
DELIVERY_PIPELINE_FIELDS = ['description', 'serialPipeline']
TARGET_FIELDS = ['description', 'approvalRequired', 'gkeCluster']
METADATA_FIELDS = ['name', 'annotations', 'labels']


def ParseDeployConfig(messages, manifests, region):
  """Parses the declarative definition of the resources into message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    manifests: the list of parsed resource yaml definitions.
    region: location ID.

  Returns:
    A dictionary of resource kind and message.
  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  resource_dict = {
      DELIVERY_PIPELINE_KIND_BETA1: [],
      TARGET_KIND_BETA1: [],
      DELIVERY_PIPELINE_KIND_V1BETA1: [],
      TARGET_KIND_V1BETA1: []
  }
  project = properties.VALUES.core.project.GetOrFail()
  for manifest in manifests:
    if manifest.get('apiVersion') is None:
      raise exceptions.CloudDeployConfigError(
          'missing required field .apiVersion')
    if manifest.get('kind') is None:
      raise exceptions.CloudDeployConfigError('missing required field .kind')
    api_version = manifest['apiVersion']
    if api_version == API_VERSION_BETA1:
      _ParseBeta1Config(messages, manifest['kind'], manifest, project, region,
                        resource_dict)
    elif api_version == API_VERSION_V1BETA1:
      _ParseV1Beta1Config(messages, manifest['kind'], manifest, project, region,
                          resource_dict)
    else:
      raise exceptions.CloudDeployConfigError(
          'api version {} not supported'.format(api_version))

  return resource_dict


def _ParseV1Beta1Config(messages, kind, manifest, project, region,
                        resource_dict):
  """Parses the Cloud Deploy v1beta1 resource specifications into message.

       This specification version is KRM complied and should be used after
       private review.

  Args:
     messages: module containing the definitions of messages for Cloud Deploy.
     kind: str, name of the resource schema.
     manifest: dict[str,str], cloud deploy resource yaml definition.
     project: str, gcp project.
     region: str, ID of the location.
     resource_dict: dict[str,optional[message]], a dictionary of resource kind
       and message.

  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  metadata = manifest.get('metadata')
  if not metadata or not metadata.get('name'):
    raise exceptions.CloudDeployConfigError(
        'missing required field .metadata.name in {}'.format(kind))
  if kind == DELIVERY_PIPELINE_KIND_V1BETA1:
    resource_type = DELIVERY_PIPELINE_TYPE
    resource, resource_ref = _CreateDeliveryPipelineResource(
        messages, metadata['name'], project, region)
  elif kind == TARGET_KIND_V1BETA1:
    resource_type = TARGET_TYPE
    if manifest.get('deliveryPipeline') is None:
      raise exceptions.CloudDeployConfigError(
          'missing required field .deliveryPipeline in target {}'.format(
              metadata['name']))
    resource, resource_ref = _CreateTargetResource(messages, metadata['name'],
                                                   manifest['deliveryPipeline'],
                                                   project, region)
  else:
    raise exceptions.CloudDeployConfigError(
        'kind {} not supported'.format(kind))

  if '/' in resource_ref.Name():
    raise exceptions.CloudDeployConfigError(
        'resource ID "{}" contains /.'.format(resource_ref.Name()))

  for field in manifest:
    if field not in ['apiVersion', 'kind', 'metadata', 'deliveryPipeline']:
      setattr(resource, field, manifest.get(field))
  # Sets the properties in metadata.
  for field in metadata:
    if field not in ['name', 'annotations', 'labels']:
      setattr(resource, field, metadata.get(field))
  SetMetadata(messages, resource, resource_type, metadata.get('annotations'),
              metadata.get('labels'))

  resource_dict[kind].append(resource)


def _ParseBeta1Config(messages, kind, manifest, project, region, resource_dict):
  """Parses the Cloud Deploy beta1 resource specifications into message.

      This specification version shouldn't be used after private review.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    kind: str, name of the resource schema.
    manifest: dict[str,str], cloud deploy resource yaml definition.
    project: str, gcp project.
    region: str, ID of the location.
    resource_dict: dict[str,optional[message]], a dictionary of resource kind
      and message.

  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  if manifest.get('name') is None:
    raise exceptions.CloudDeployConfigError(
        'missing required field .name in {}'.format(kind))
  if kind == DELIVERY_PIPELINE_KIND_BETA1:
    resource, resource_ref = _CreateDeliveryPipelineResource(
        messages, manifest['name'], project, region)
    resource_type = DELIVERY_PIPELINE_TYPE
  elif kind == TARGET_KIND_BETA1:
    if manifest.get('deliveryPipeline') is None:
      raise exceptions.CloudDeployConfigError(
          'missing required field .deliveryPipeline in target {}'.format(
              manifest['name']))
    resource, resource_ref = _CreateTargetResource(messages, manifest['name'],
                                                   manifest['deliveryPipeline'],
                                                   project, region)
    resource_type = TARGET_TYPE
  else:
    raise exceptions.CloudDeployConfigError(
        'kind {} not supported'.format(kind))

  if '/' in resource_ref.Name():
    raise exceptions.CloudDeployConfigError(
        'resource ID "{}" contains /.'.format(resource_ref.Name()))

  for field in manifest:
    if field not in [
        'apiVersion', 'kind', 'deliveryPipeline', 'name', 'annotations',
        'labels'
    ]:
      setattr(resource, field, manifest.get(field))

  SetMetadata(messages, resource, resource_type, manifest.get('annotations'),
              manifest.get('labels'))

  resource_dict[kind].append(resource)


def _CreateTargetResource(messages, target_name, delivery_pipeline_id, project,
                          region):
  """Creates target resource with full target name and the resource reference."""
  resource = messages.Target()
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


def _CreateDeliveryPipelineResource(messages, delivery_pipeline_name, project,
                                    region):
  """Creates delivery pipeline resource with full delivery pipeline name and the resource reference."""
  resource = messages.DeliveryPipeline()
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


def ProtoToManifest(resource, resource_ref, kind, fields):
  """Convert a resource message to a cloud deploy resource manifest.

  The manifest can be applied by 'deploy apply' command.

  Args:
    resource: message in googlecloudsdk.third_party.apis.cloudeploy.
    resource_ref: cloud deploy resource object.
    kind: kind of the cloud deploy resource
    fields: the fields in the resource that will be used in the manifest.

  Returns:
    A dictionary that represents the cloud deploy resource.
  """
  manifest = collections.OrderedDict(
      apiVersion=API_VERSION_V1BETA1, kind=kind, metadata={})

  for k in METADATA_FIELDS:
    v = getattr(resource, k)
    if v:
      manifest['metadata'][k] = v
  manifest['metadata']['name'] = resource_ref.Name()

  for k in fields:
    v = getattr(resource, k)
    if v:
      manifest[k] = v
  if kind == TARGET_KIND_V1BETA1:
    manifest['deliveryPipeline'] = resource_ref.AsDict()['deliveryPipelinesId']

  return manifest
