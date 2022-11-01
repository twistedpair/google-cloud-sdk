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
"""Spanner instance API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime

from apitools.base.py import list_pager
from cloudsdk.google.protobuf import timestamp_pb2
from googlecloudsdk.api_lib.spanner import response_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


# The list of pre-defined IAM roles in Spanner.
KNOWN_ROLES = [
    'roles/spanner.admin', 'roles/spanner.databaseAdmin',
    'roles/spanner.databaseReader', 'roles/spanner.databaseUser',
    'roles/spanner.viewer'
]

# Timeout to use in ListInstances for unreachable instances.
UNREACHABLE_INSTANCE_TIMEOUT = datetime.timedelta(seconds=20)


def Create(instance,
           config,
           description,
           nodes,
           processing_units=None,
           instance_type=None,
           expire_behavior=None,
           default_storage_type=None):
  """Create a new instance."""
  client = apis.GetClientInstance('spanner', 'v1')
  # Module containing the definitions of messages for the specified API.
  msgs = apis.GetMessagesModule('spanner', 'v1')
  config_ref = resources.REGISTRY.Parse(
      config,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instanceConfigs')
  project_ref = resources.REGISTRY.Create(
      'spanner.projects', projectsId=properties.VALUES.core.project.GetOrFail)
  instance_obj = msgs.Instance(
      config=config_ref.RelativeName(), displayName=description)
  if nodes:
    instance_obj.nodeCount = nodes
  elif processing_units:
    instance_obj.processingUnits = processing_units
  if instance_type is not None:
    instance_obj.instanceType = instance_type
  if expire_behavior is not None:
    instance_obj.freeInstanceMetadata = msgs.FreeInstanceMetadata(
        expireBehavior=expire_behavior)
  if default_storage_type is not None:
    instance_obj.defaultStorageType = default_storage_type
  req = msgs.SpannerProjectsInstancesCreateRequest(
      parent=project_ref.RelativeName(),
      createInstanceRequest=msgs.CreateInstanceRequest(
          instanceId=instance, instance=instance_obj))
  return client.projects_instances.Create(req)


def SetPolicy(instance_ref, policy, field_mask=None):
  """Saves the given policy on the instance, overwriting whatever exists."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  policy.version = iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION
  req = msgs.SpannerProjectsInstancesSetIamPolicyRequest(
      resource=instance_ref.RelativeName(),
      setIamPolicyRequest=msgs.SetIamPolicyRequest(policy=policy,
                                                   updateMask=field_mask))
  return client.projects_instances.SetIamPolicy(req)


def GetIamPolicy(instance_ref):
  """Gets the IAM policy on an instance."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesGetIamPolicyRequest(
      resource=instance_ref.RelativeName(),
      getIamPolicyRequest=msgs.GetIamPolicyRequest(
          options=msgs.GetPolicyOptions(
              requestedPolicyVersion=
              iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION)))
  return client.projects_instances.GetIamPolicy(req)


def Delete(instance):
  """Delete an instance."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesDeleteRequest(name=ref.RelativeName())
  return client.projects_instances.Delete(req)


def Get(instance):
  """Get an instance by name."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesGetRequest(name=ref.RelativeName())
  return client.projects_instances.Get(req)


def List():
  """List instances in the project."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  project_ref = resources.REGISTRY.Create(
      'spanner.projects', projectsId=properties.VALUES.core.project.GetOrFail)
  tp_proto = timestamp_pb2.Timestamp()
  tp_proto.FromDatetime(
      datetime.datetime.utcnow() + UNREACHABLE_INSTANCE_TIMEOUT)
  req = msgs.SpannerProjectsInstancesListRequest(
      parent=project_ref.RelativeName(),
      instanceDeadline=tp_proto.ToJsonString())
  return list_pager.YieldFromList(
      client.projects_instances,
      req,
      field='instances',
      batch_size_attribute='pageSize',
      get_field_func=response_util.GetFieldAndLogUnreachable)


def Patch(instance,
          description=None,
          nodes=None,
          processing_units=None,
          instance_type=None,
          expire_behavior=None):
  """Update an instance."""
  fields = []
  if description is not None:
    fields.append('displayName')
  if nodes is not None:
    fields.append('nodeCount')
  if processing_units is not None:
    fields.append('processingUnits')
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')

  if processing_units:
    instance_obj = msgs.Instance(
        displayName=description, processingUnits=processing_units)
  else:
    instance_obj = msgs.Instance(displayName=description, nodeCount=nodes)

  if instance_type is not None:
    fields.append('instanceType')
    instance_obj.instanceType = instance_type
  if expire_behavior is not None:
    fields.append('freeInstanceMetadata.expireBehavior')
    instance_obj.freeInstanceMetadata = msgs.FreeInstanceMetadata(
        expireBehavior=expire_behavior)

  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesPatchRequest(
      name=ref.RelativeName(),
      updateInstanceRequest=msgs.UpdateInstanceRequest(
          fieldMask=','.join(fields), instance=instance_obj))
  return client.projects_instances.Patch(req)


def GetLocations(instance, verbose_flag):
  """Get all the replica regions for an instance."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  instance_res = Get(instance)
  config_req = msgs.SpannerProjectsInstanceConfigsGetRequest(
      name=instance_res.config)
  config_res = client.projects_instanceConfigs.Get(config_req)
  if verbose_flag:
    command_output = []
    for item in config_res.replicas:
      command_output.append({'location': item.location, 'type': item.type})
  else:
    region_set = set()
    for item in config_res.replicas:
      region_set.add(item.location)
    command_output = [{'location': item} for item in region_set]
  return command_output
