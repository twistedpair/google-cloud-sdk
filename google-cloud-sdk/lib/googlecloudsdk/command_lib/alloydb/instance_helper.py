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
"""Helper functions for constructing and validating AlloyDB instance requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import properties


def ConstructCreateRequestFromArgs(client, alloydb_messages, project_ref, args):
  """Validates command line input arguments and passes parent's resources.

  Args:
    client: Client for api_utils.py class.
    alloydb_messages: Messages module for the API client.
    project_ref: parent resource path of the resource being created
    args: Command line input arguments.

  Returns:
    Fully-constructed request to create an AlloyDB instance.
  """
  instance_resource = alloydb_messages.Instance()

  # set availability-type if provided
  instance_resource.availabilityType = _ParseAvailabilityType(
      alloydb_messages, args.availability_type)
  instance_resource.machineConfig = alloydb_messages.MachineConfig(
      cpuCount=args.cpu_count)
  instance_ref = client.resource_parser.Create(
      'alloydb.projects.locations.clusters.instances',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      clustersId=args.cluster,
      instancesId=args.instance)
  instance_resource.name = instance_ref.RelativeName()

  instance_resource.databaseFlags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags')
  instance_resource.instanceType = _ParseInstanceType(alloydb_messages,
                                                      args.instance_type)

  if instance_resource.instanceType == alloydb_messages.Instance.InstanceTypeValueValuesEnum.READ_POOL:
    instance_resource.readPoolConfig = alloydb_messages.ReadPoolConfig(
        nodeCount=args.read_pool_node_count)

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesCreateRequest(
          instance=instance_resource,
          instanceId=args.instance,
          parent=project_ref.RelativeName()))


def ConstructPatchRequestFromArgs(alloydb_messages, instance_ref, args):
  """Constructs the request to update an AlloyDB instance.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    Fully-constructed request to update an AlloyDB instance.
  """
  instance_resource, mask = ConstructInstanceAndMaskFromArgs(
      alloydb_messages, instance_ref, args)

  return (
      alloydb_messages.AlloydbProjectsLocationsClustersInstancesPatchRequest(
          instance=instance_resource,
          name=instance_ref.RelativeName(),
          updateMask=mask))


def ConstructInstanceAndMaskFromArgs(alloydb_messages, instance_ref, args):
  """Validates command line arguments and creates the instance and field mask.

  Args:
    alloydb_messages: Messages module for the API client.
    instance_ref: parent resource path of the resource being updated
    args: Command line input arguments.

  Returns:
    An AlloyDB instance and mask for update.
  """
  availability_type_path = 'availabilityType'
  database_flags_path = 'databaseFlags'
  cpu_count_path = 'machineConfig.cpuCount'
  read_pool_node_count_path = 'readPoolConfig.nodeCount'

  instance_resource = alloydb_messages.Instance()
  paths = []

  instance_resource.name = instance_ref.RelativeName()

  availability_type = _ParseAvailabilityType(
      alloydb_messages, args.availability_type)
  if availability_type:
    instance_resource.availabilityType = availability_type
    paths.append(availability_type_path)

  database_flags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags')
  if database_flags:
    instance_resource.databaseFlags = database_flags
    paths.append(database_flags_path)

  if args.cpu_count:
    instance_resource.machineConfig = alloydb_messages.MachineConfig(
        cpuCount=args.cpu_count)
    paths.append(cpu_count_path)

  if args.read_pool_node_count:
    instance_resource.readPoolConfig = alloydb_messages.ReadPoolConfig(
        nodeCount=args.read_pool_node_count)
    paths.append(read_pool_node_count_path)

  mask = ','.join(paths) if paths else None
  return instance_resource, mask


def _ParseAvailabilityType(alloydb_messages, availability_type):
  if availability_type:
    return alloydb_messages.Instance.AvailabilityTypeValueValuesEnum.lookup_by_name(
        availability_type.upper())
  return None


def _ParseInstanceType(alloydb_messages, instance_type):
  if instance_type:
    return alloydb_messages.Instance.InstanceTypeValueValuesEnum.lookup_by_name(
        instance_type.upper())
  return None
