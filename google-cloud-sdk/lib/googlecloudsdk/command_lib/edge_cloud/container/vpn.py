# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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

"""Utils for VPN Connection commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import resources


def SetVPNClusterPath(ref, args, request):
  """Sets the vpnConnection.cluster field with a relative resource path.

  Args:
    ref: reference to the cluster object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """

  # Skips if full path of the cluster resource is provided.
  if 'projects/' in args.cluster:
    return request

  cluster = resources.REGISTRY.Create(
      'edgecontainer.projects.locations.clusters',
      projectsId=ref.projectsId,
      locationsId=ref.locationsId,
      clustersId=args.cluster)
  request.vpnConnection.cluster = cluster.RelativeName()
  return request


class DescribeVPNTableView:
  """View model for VPN connections describe."""

  def __init__(self, name, create_time, cluster, vpc, state, error):
    self.name = name
    self.create_time = create_time
    self.cluster = cluster
    self.vpc = vpc
    self.state = state
    if error:
      self.error = error


def CreateDescribeVPNTableViewResponseHook(response, args):
  """Create DescribeVPNTableView from GetVpnConnection response.

  Args:
    response: Response from GetVpnConnection
    args: Args from GetVpnConnection

  Returns:
    DescribeVPNTableView
  """
  del args  # args not used

  name = response.name
  create_time = response.createTime

  details = response.details
  if details:
    state = details.state
    error = details.error
  else:
    state = 'STATE_UNKNOWN'
    error = ''

  cluster = {}
  items = response.cluster.split('/')
  try:
    cluster['project'] = items[1]
    cluster['location'] = items[3]
    cluster['ID'] = items[5]
  except IndexError:
    pass
  if response.natGatewayIp:
    cluster['NAT Gateway IP'] = response.natGatewayIp

  vpc = {}
  items = response.vpc.split('/')
  try:
    vpc['project'] = items[1]
    vpc['ID'] = items[5]
  except IndexError:
    pass
  if details:
    vpc['Cloud Router'] = {
        'name': details.cloudRouter.name,
        'region': items[3]
    }
    vpc['Cloud VPNs'] = details.cloudVpns

  return DescribeVPNTableView(name, create_time, cluster, vpc, state, error)
