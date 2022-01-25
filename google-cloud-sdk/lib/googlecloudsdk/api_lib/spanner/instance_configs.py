# -*- coding: utf-8 -*- #
# Copyright 2016 Google LLC. All Rights Reserved.
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
"""Spanner instanceConfigs API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.ai import errors
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
import six


def Get(config):
  """Get the specified instance config."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs')
  req = msgs.SpannerProjectsInstanceConfigsGetRequest(
      name=ref.RelativeName())
  return client.projects_instanceConfigs.Get(req)


def List():
  """List instance configs in the project."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstanceConfigsListRequest(
      parent='projects/'+properties.VALUES.core.project.GetOrFail())
  return list_pager.YieldFromList(
      client.projects_instanceConfigs,
      req,
      field='instanceConfigs',
      batch_size_attribute='pageSize')


def Delete(config, etag=None, validate_only=False):
  """Delete an instance config."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs')
  req = msgs.SpannerProjectsInstanceConfigsDeleteRequest(
      name=ref.RelativeName(), etag=etag, validateOnly=validate_only)
  return client.projects_instanceConfigs.Delete(req)


def Create(config,
           display_name,
           base_config,
           replicas,
           validate_only,
           labels=None,
           etag=None):
  """Create instance configs in the project."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  project_ref = resources.REGISTRY.Create(
      'spanner.projects', projectsId=properties.VALUES.core.project.GetOrFail)
  config_ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs')
  replica_info = []
  for replica in replicas:
    # TODO(b/399093071): Change type to ReplicaInfo.TypeValueValuesEnum instead
    # of str.
    replica_type = msgs.ReplicaInfo.TypeValueValuesEnum.TYPE_UNSPECIFIED
    if replica['type'] == 'READ_ONLY':
      replica_type = msgs.ReplicaInfo.TypeValueValuesEnum.READ_ONLY
    elif replica['type'] == 'READ_WRITE':
      replica_type = msgs.ReplicaInfo.TypeValueValuesEnum.READ_WRITE
    elif replica['type'] == 'WITNESS':
      replica_type = msgs.ReplicaInfo.TypeValueValuesEnum.WITNESS

    replica_info.append(
        msgs.ReplicaInfo(location=replica['location'], type=replica_type))

  labels_message = {}
  if labels is not None:
    labels_message = msgs.InstanceConfig.LabelsValue(additionalProperties=[
        msgs.InstanceConfig.LabelsValue.AdditionalProperty(
            key=key, value=value) for key, value in six.iteritems(labels)
    ])

  instance_config = msgs.InstanceConfig(
      name=config_ref.RelativeName(),
      displayName=display_name,
      baseConfig=base_config,
      labels=labels_message,
      replicas=replica_info)
  if etag:
    instance_config.etag = etag

  req = msgs.SpannerProjectsInstanceConfigsCreateRequest(
      parent=project_ref.RelativeName(),
      instanceConfigId=config,
      instanceConfig=instance_config,
      validateOnly=validate_only)
  return client.projects_instanceConfigs.Create(req)


def Patch(args):
  """Update an instance config."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      args.config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs')
  instance_config = msgs.InstanceConfig(name=ref.RelativeName())

  update_mask = []

  if args.display_name is not None:
    instance_config.displayName = args.display_name
    update_mask.append('display_name')

  if args.etag is not None:
    instance_config.etag = args.etag

  def GetLabels():
    req = msgs.SpannerProjectsInstanceConfigsGetRequest(name=ref.RelativeName())
    return client.projects_instanceConfigs.Get(req).labels

  labels_update = labels_util.ProcessUpdateArgsLazy(
      args, msgs.InstanceConfig.LabelsValue, GetLabels)
  if labels_update.needs_update:
    instance_config.labels = labels_update.labels
    update_mask.append('labels')

  if not update_mask:
    raise errors.NoFieldsSpecifiedError('No updates requested.')

  req = msgs.SpannerProjectsInstanceConfigsPatchRequest(
      name=ref.RelativeName(),
      instanceConfig=instance_config,
      updateMask=','.join(update_mask),
      validateOnly=args.validate_only)
  return client.projects_instanceConfigs.Patch(req)
