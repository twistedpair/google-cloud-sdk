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

from googlecloudsdk.api_lib.alloydb import instance_prop_reducers as reducers
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import properties


def ConstructRequestFromArgs(client, alloydb_messages,
                             project_ref, args):
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
  instance_ref = client.resource_parser.Create(
      'alloydbadmin.projects.locations.clusters.instances',
      projectsId=properties.VALUES.core.project.GetOrFail,
      locationsId=args.region,
      clustersId=args.cluster,
      instancesId=args.instance)
  instance_resource.name = instance_ref.RelativeName()

  instance_resource.tier = reducers.MachineType(args.tier, args.memory,
                                                args.cpu)
  instance_resource.databaseFlags = labels_util.ParseCreateArgs(
      args,
      alloydb_messages.Instance.DatabaseFlagsValue,
      labels_dest='database_flags')
  instance_resource.gceZone = args.zone
  instance_resource.instanceType = _ParseInstanceType(alloydb_messages,
                                                      args.instance_type)
  instance_resource.networkConfig = _ParseNetworkConfig(alloydb_messages,
                                                        args.assign_ip)
  instance_resource.readPoolConfig = alloydb_messages.ReadPoolConfig(
      readPoolSize=args.read_pool_size)

  # TODO(b/185795425): Need better understanding of use cases before adding
  # instance_resource.networkConfig
  #   sslRequired (--require-ssl)
  # instance_resource.labels (--labels)
  return alloydb_messages.AlloydbadminProjectsLocationsClustersInstancesCreateRequest(
      instance=instance_resource,
      instanceId=args.instance,
      parent=project_ref.RelativeName())


def _ParseAvailabilityType(alloydb_messages, availability_type):
  if availability_type:
    return alloydb_messages.Instance.AvailabilityTypeValueValuesEnum.lookup_by_name(
        availability_type.upper())
  return None


def _ParseInstanceType(alloydb_messages, instance_type):
  return alloydb_messages.Instance.InstanceTypeValueValuesEnum.lookup_by_name(
      instance_type.upper())


def _ParseNetworkConfig(alloydb_messages, assign_ip):
  if assign_ip:
    return alloydb_messages.NetworkConfig(publicIpEnabled=assign_ip)
  return None

