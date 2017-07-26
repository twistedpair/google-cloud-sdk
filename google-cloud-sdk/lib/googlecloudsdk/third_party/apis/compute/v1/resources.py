# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Resource definitions for cloud platform apis."""

import enum


BASE_URL = 'https://www.googleapis.com/compute/v1/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  ACCELERATORTYPES = (
      'acceleratorTypes',
      'projects/{project}/zones/{zone}/acceleratorTypes/{acceleratorType}',
      {},
      [u'project', u'zone', u'acceleratorType']
  )
  ADDRESSES = (
      'addresses',
      'projects/{project}/regions/{region}/addresses/{address}',
      {},
      [u'project', u'region', u'address']
  )
  AUTOSCALERS = (
      'autoscalers',
      'projects/{project}/zones/{zone}/autoscalers/{autoscaler}',
      {},
      [u'project', u'zone', u'autoscaler']
  )
  BACKENDBUCKETS = (
      'backendBuckets',
      'projects/{project}/global/backendBuckets/{backendBucket}',
      {},
      [u'project', u'backendBucket']
  )
  BACKENDSERVICES = (
      'backendServices',
      'projects/{project}/global/backendServices/{backendService}',
      {},
      [u'project', u'backendService']
  )
  DISKTYPES = (
      'diskTypes',
      'projects/{project}/zones/{zone}/diskTypes/{diskType}',
      {},
      [u'project', u'zone', u'diskType']
  )
  DISKS = (
      'disks',
      'projects/{project}/zones/{zone}/disks/{disk}',
      {},
      [u'project', u'zone', u'disk']
  )
  FIREWALLS = (
      'firewalls',
      'projects/{project}/global/firewalls/{firewall}',
      {},
      [u'project', u'firewall']
  )
  FORWARDINGRULES = (
      'forwardingRules',
      'projects/{project}/regions/{region}/forwardingRules/{forwardingRule}',
      {},
      [u'project', u'region', u'forwardingRule']
  )
  GLOBALADDRESSES = (
      'globalAddresses',
      'projects/{project}/global/addresses/{address}',
      {},
      [u'project', u'address']
  )
  GLOBALFORWARDINGRULES = (
      'globalForwardingRules',
      'projects/{project}/global/forwardingRules/{forwardingRule}',
      {},
      [u'project', u'forwardingRule']
  )
  GLOBALOPERATIONS = (
      'globalOperations',
      'projects/{project}/global/operations/{operation}',
      {},
      [u'project', u'operation']
  )
  HEALTHCHECKS = (
      'healthChecks',
      'projects/{project}/global/healthChecks/{healthCheck}',
      {},
      [u'project', u'healthCheck']
  )
  HTTPHEALTHCHECKS = (
      'httpHealthChecks',
      'projects/{project}/global/httpHealthChecks/{httpHealthCheck}',
      {},
      [u'project', u'httpHealthCheck']
  )
  HTTPSHEALTHCHECKS = (
      'httpsHealthChecks',
      'projects/{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      {},
      [u'project', u'httpsHealthCheck']
  )
  IMAGES = (
      'images',
      'projects/{project}/global/images/{image}',
      {},
      [u'project', u'image']
  )
  INSTANCEGROUPMANAGERS = (
      'instanceGroupManagers',
      'projects/{project}/zones/{zone}/instanceGroupManagers/'
      '{instanceGroupManager}',
      {},
      [u'project', u'zone', u'instanceGroupManager']
  )
  INSTANCEGROUPS = (
      'instanceGroups',
      'projects/{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      {},
      [u'project', u'zone', u'instanceGroup']
  )
  INSTANCETEMPLATES = (
      'instanceTemplates',
      'projects/{project}/global/instanceTemplates/{instanceTemplate}',
      {},
      [u'project', u'instanceTemplate']
  )
  INSTANCES = (
      'instances',
      'projects/{project}/zones/{zone}/instances/{instance}',
      {},
      [u'project', u'zone', u'instance']
  )
  LICENSES = (
      'licenses',
      'projects/{project}/global/licenses/{license}',
      {},
      [u'project', u'license']
  )
  MACHINETYPES = (
      'machineTypes',
      'projects/{project}/zones/{zone}/machineTypes/{machineType}',
      {},
      [u'project', u'zone', u'machineType']
  )
  NETWORKS = (
      'networks',
      'projects/{project}/global/networks/{network}',
      {},
      [u'project', u'network']
  )
  NEXTHOPGATEWAYS = (
      'nextHopGateways',
      'projects/{project}/global/gateways/{nextHopGateway}',
      {},
      ['project', 'nextHopGateway']
  )
  PROJECTS = (
      'projects',
      'projects/{project}',
      {},
      [u'project']
  )
  REGIONAUTOSCALERS = (
      'regionAutoscalers',
      'projects/{project}/regions/{region}/autoscalers/{autoscaler}',
      {},
      [u'project', u'region', u'autoscaler']
  )
  REGIONBACKENDSERVICES = (
      'regionBackendServices',
      'projects/{project}/regions/{region}/backendServices/{backendService}',
      {},
      [u'project', u'region', u'backendService']
  )
  REGIONCOMMITMENTS = (
      'regionCommitments',
      'projects/{project}/regions/{region}/commitments/{commitment}',
      {},
      [u'project', u'region', u'commitment']
  )
  REGIONINSTANCEGROUPMANAGERS = (
      'regionInstanceGroupManagers',
      'projects/{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      {},
      [u'project', u'region', u'instanceGroupManager']
  )
  REGIONINSTANCEGROUPS = (
      'regionInstanceGroups',
      'projects/{project}/regions/{region}/instanceGroups/{instanceGroup}',
      {},
      [u'project', u'region', u'instanceGroup']
  )
  REGIONOPERATIONS = (
      'regionOperations',
      'projects/{project}/regions/{region}/operations/{operation}',
      {},
      [u'project', u'region', u'operation']
  )
  REGIONS = (
      'regions',
      'projects/{project}/regions/{region}',
      {},
      [u'project', u'region']
  )
  ROUTERS = (
      'routers',
      'projects/{project}/regions/{region}/routers/{router}',
      {},
      [u'project', u'region', u'router']
  )
  ROUTES = (
      'routes',
      'projects/{project}/global/routes/{route}',
      {},
      [u'project', u'route']
  )
  SNAPSHOTS = (
      'snapshots',
      'projects/{project}/global/snapshots/{snapshot}',
      {},
      [u'project', u'snapshot']
  )
  SSLCERTIFICATES = (
      'sslCertificates',
      'projects/{project}/global/sslCertificates/{sslCertificate}',
      {},
      [u'project', u'sslCertificate']
  )
  SUBNETWORKS = (
      'subnetworks',
      'projects/{project}/regions/{region}/subnetworks/{subnetwork}',
      {},
      [u'project', u'region', u'subnetwork']
  )
  TARGETHTTPPROXIES = (
      'targetHttpProxies',
      'projects/{project}/global/targetHttpProxies/{targetHttpProxy}',
      {},
      [u'project', u'targetHttpProxy']
  )
  TARGETHTTPSPROXIES = (
      'targetHttpsProxies',
      'projects/{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      {},
      [u'project', u'targetHttpsProxy']
  )
  TARGETINSTANCES = (
      'targetInstances',
      'projects/{project}/zones/{zone}/targetInstances/{targetInstance}',
      {},
      [u'project', u'zone', u'targetInstance']
  )
  TARGETPOOLS = (
      'targetPools',
      'projects/{project}/regions/{region}/targetPools/{targetPool}',
      {},
      [u'project', u'region', u'targetPool']
  )
  TARGETSSLPROXIES = (
      'targetSslProxies',
      'projects/{project}/global/targetSslProxies/{targetSslProxy}',
      {},
      [u'project', u'targetSslProxy']
  )
  TARGETTCPPROXIES = (
      'targetTcpProxies',
      'projects/{project}/global/targetTcpProxies/{targetTcpProxy}',
      {},
      [u'project', u'targetTcpProxy']
  )
  TARGETVPNGATEWAYS = (
      'targetVpnGateways',
      'projects/{project}/regions/{region}/targetVpnGateways/'
      '{targetVpnGateway}',
      {},
      [u'project', u'region', u'targetVpnGateway']
  )
  URLMAPS = (
      'urlMaps',
      'projects/{project}/global/urlMaps/{urlMap}',
      {},
      [u'project', u'urlMap']
  )
  VPNTUNNELS = (
      'vpnTunnels',
      'projects/{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      {},
      [u'project', u'region', u'vpnTunnel']
  )
  ZONEOPERATIONS = (
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      {},
      [u'project', u'zone', u'operation']
  )
  ZONES = (
      'zones',
      'projects/{project}/zones/{zone}',
      {},
      [u'project', u'zone']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
