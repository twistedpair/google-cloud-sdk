# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Instance creation request modifier."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


def Messages(api_version):
  return apis.GetMessagesModule('krmapihosting', api_version)


def AddExtraArgs():
  """Adds additional args that can't be easily represented in create.yaml."""

  return []


def CreateUpdateRequest(ref, args):
  """Returns an updated request formatted to the right URI endpoint."""
  messages = Messages(ref.GetCollectionInfo().api_version)

  # krmapihosting create endpoint uses a different uri from the one generated,
  # we will need to construct it manually
  custom_uri = 'projects/{project_id}/locations/{location}'.format(
      project_id=ref.projectsId, location=args.location)

  # Default values if flags not specified

  # Default master ipv4 cidr block address if not provided
  master_ipv4_cidr_block = '172.16.0.128/28'
  if args.master_ipv4_cidr_block is not None:
    master_ipv4_cidr_block = args.master_ipv4_cidr_block

  # We don't expose the bundle in this surface.
  bundles_config = messages.BundlesConfig(
      configControllerConfig=messages.ConfigControllerConfig(enabled=True))

  krm_api_host = messages.KrmApiHost(
      masterIpv4CidrBlock=master_ipv4_cidr_block,
      bundlesConfig=bundles_config)

  # Pass through the network parameter if it was provided.
  if args.network is not None:
    krm_api_host.network = args.network

  # Pass through the man_block parameter if it was provided.
  if args.man_block is not None:
    krm_api_host.manBlock = args.man_block

  # Pass through the cluster_ipv4_cidr_block parameter if it was provided.
  if args.cluster_ipv4_cidr_block is not None:
    krm_api_host.clusterCidrBlock = args.cluster_ipv4_cidr_block

  # Pass through the services-ipv4-cidr-block parameter if it was provided.
  if args.services_ipv4_cidr_block is not None:
    krm_api_host.servicesCidrBlock = args.services_ipv4_cidr_block

  # Pass through the cluster_named_range parameter if it was provided.
  if args.cluster_named_range is not None:
    krm_api_host.clusterNamedRange = args.cluster_named_range

  # Pass through the services_named_range parameter if it was provided.
  if args.services_named_range is not None:
    krm_api_host.servicesNamedRange = args.services_named_range

  if args.full_management:
    full_mgmt_config = messages.FullManagementConfig(
        clusterCidrBlock=args.cluster_ipv4_cidr_block,
        clusterNamedRange=args.cluster_named_range,
        manBlock=args.man_block,
        masterIpv4CidrBlock=master_ipv4_cidr_block,
        network=args.network,
        servicesCidrBlock=args.services_ipv4_cidr_block,
        servicesNamedRange=args.services_named_range)
    mgmt_config = messages.ManagementConfig(
        fullManagementConfig=full_mgmt_config)
    krm_api_host.managementConfig = mgmt_config
  else:
    std_mgmt_config = messages.StandardManagementConfig(
        clusterCidrBlock=args.cluster_ipv4_cidr_block,
        clusterNamedRange=args.cluster_named_range,
        manBlock=args.man_block,
        masterIpv4CidrBlock=master_ipv4_cidr_block,
        network=args.network,
        servicesCidrBlock=args.services_ipv4_cidr_block,
        servicesNamedRange=args.services_named_range)
    mgmt_config = messages.ManagementConfig(
        standardManagementConfig=std_mgmt_config)
    krm_api_host.managementConfig = mgmt_config

  request = (
      messages.KrmapihostingProjectsLocationsKrmApiHostsCreateRequest(
          parent=custom_uri,
          krmApiHostId=ref.krmApiHostsId,
          krmApiHost=krm_api_host))

  return request
