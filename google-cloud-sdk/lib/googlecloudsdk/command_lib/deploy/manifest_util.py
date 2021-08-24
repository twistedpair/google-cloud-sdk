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
from googlecloudsdk.command_lib.deploy import deploy_util
from googlecloudsdk.command_lib.deploy import exceptions
from googlecloudsdk.command_lib.deploy import target_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources

PIPELINE_UPDATE_MASK = '*'
DELIVERY_PIPELINE_KIND_V1BETA1 = 'DeliveryPipeline'
TARGET_KIND_V1BETA1 = 'Target'
API_VERSION_V1BETA1 = 'deploy.cloud.google.com/v1beta1'
DELIVERY_PIPELINE_FIELDS = ['description', 'serialPipeline']
TARGET_FIELDS = [
    'description', 'requireApproval', 'cluster', 'gkeCluster', 'gke'
]
METADATA_FIELDS = ['annotations', 'labels']


def ParseDeployConfig(messages, manifests, region):
  """Parses the declarative definition of the resources into message.

  Args:
    messages: module containing the definitions of messages for Cloud Deploy.
    manifests: [str], the list of parsed resource yaml definitions.
    region: str, location ID.

  Returns:
    A dictionary of resource kind and message.
  Raises:
    exceptions.CloudDeployConfigError, if the declarative definition is
    incorrect.
  """
  resource_dict = {DELIVERY_PIPELINE_KIND_V1BETA1: [], TARGET_KIND_V1BETA1: []}
  project = properties.VALUES.core.project.GetOrFail()
  for manifest in manifests:
    if manifest.get('apiVersion') is None:
      raise exceptions.CloudDeployConfigError(
          'missing required field .apiVersion')
    if manifest.get('kind') is None:
      raise exceptions.CloudDeployConfigError('missing required field .kind')
    api_version = manifest['apiVersion']
    if api_version == API_VERSION_V1BETA1:
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
    resource_type = deploy_util.ResourceType.DELIVERY_PIPELINE
    resource, resource_ref = _CreateDeliveryPipelineResource(
        messages, metadata['name'], project, region)
  elif kind == TARGET_KIND_V1BETA1:
    resource_type = deploy_util.ResourceType.TARGET
    resource, resource_ref = _CreateTargetResource(messages, metadata['name'],
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
  deploy_util.SetMetadata(messages, resource, resource_type,
                          metadata.get('annotations'), metadata.get('labels'))

  resource_dict[kind].append(resource)


def _CreateTargetResource(messages, target_name_or_id, project, region):
  """Creates target resource with full target name and the resource reference."""
  resource = messages.Target()
  resource_ref = target_util.TargetReference(target_name_or_id, project, region)
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


def ProtoToManifest(resource, resource_ref, kind, fields):
  """Converts a resource message to a cloud deploy resource manifest.

  The manifest can be applied by 'deploy apply' command.

  Args:
    resource: message in googlecloudsdk.third_party.apis.clouddeploy.
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
    # Skips the 'zero' values in the message.
    if v:
      manifest['metadata'][k] = v
  # Sets the name to resource ID instead of the full name.
  manifest['metadata']['name'] = resource_ref.Name()

  for k in fields:
    try:
      v = getattr(resource, k)
      # Skips the 'zero' values in the message.
      if v:
        manifest[k] = v
    except AttributeError:
      # TODO(b/188524927) 'gkeCluster' will be removed at some point.
      # try/except block and manifest_util_test.py can be removed when
      # the migration is done.
      log.debug('Field {} does not exist.'.format(k))

  return manifest
