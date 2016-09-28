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


BASE_URL = 'https://www.googleapis.com/compute/beta/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  ADDRESSES = (
      'addresses',
      'projects/{project}/regions/{region}/addresses/{address}',
      {},
      [u'project', u'region', u'address'],
      'ComputeAddressesGetRequest',)
  AUTOSCALERS = (
      'autoscalers',
      'projects/{project}/zones/{zone}/autoscalers/{autoscaler}',
      {},
      [u'project', u'zone', u'autoscaler'],
      'ComputeAutoscalersGetRequest',)
  BACKENDSERVICES = (
      'backendServices',
      'projects/{project}/global/backendServices/{backendService}',
      {},
      [u'project', u'backendService'],
      'ComputeBackendServicesGetRequest',)
  DISKTYPES = (
      'diskTypes',
      'projects/{project}/zones/{zone}/diskTypes/{diskType}',
      {},
      [u'project', u'zone', u'diskType'],
      'ComputeDiskTypesGetRequest',)
  DISKS = (
      'disks',
      'projects/{project}/zones/{zone}/disks/{disk}',
      {},
      [u'project', u'zone', u'disk'],
      'ComputeDisksGetRequest',)
  FIREWALLS = (
      'firewalls',
      'projects/{project}/global/firewalls/{firewall}',
      {},
      [u'project', u'firewall'],
      'ComputeFirewallsGetRequest',)
  FORWARDINGRULES = (
      'forwardingRules',
      'projects/{project}/regions/{region}/forwardingRules/{forwardingRule}',
      {},
      [u'project', u'region', u'forwardingRule'],
      'ComputeForwardingRulesGetRequest',)
  GLOBALADDRESSES = (
      'globalAddresses',
      'projects/{project}/global/addresses/{address}',
      {},
      [u'project', u'address'],
      'ComputeGlobalAddressesGetRequest',)
  GLOBALFORWARDINGRULES = (
      'globalForwardingRules',
      'projects/{project}/global/forwardingRules/{forwardingRule}',
      {},
      [u'project', u'forwardingRule'],
      'ComputeGlobalForwardingRulesGetRequest',)
  GLOBALOPERATIONS = (
      'globalOperations',
      'projects/{project}/global/operations/{operation}',
      {},
      [u'project', u'operation'],
      'ComputeGlobalOperationsGetRequest',)
  HEALTHCHECKS = (
      'healthChecks',
      'projects/{project}/global/healthChecks/{healthCheck}',
      {},
      [u'project', u'healthCheck'],
      'ComputeHealthChecksGetRequest',)
  HTTPHEALTHCHECKS = (
      'httpHealthChecks',
      'projects/{project}/global/httpHealthChecks/{httpHealthCheck}',
      {},
      [u'project', u'httpHealthCheck'],
      'ComputeHttpHealthChecksGetRequest',)
  HTTPSHEALTHCHECKS = (
      'httpsHealthChecks',
      'projects/{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      {},
      [u'project', u'httpsHealthCheck'],
      'ComputeHttpsHealthChecksGetRequest',)
  IMAGES = (
      'images',
      'projects/{project}/global/images/{image}',
      {},
      [u'project', u'image'],
      'ComputeImagesGetRequest',)
  INSTANCEGROUPMANAGERS = (
      'instanceGroupManagers',
      'projects/{project}/zones/{zone}/instanceGroupManagers/'
      '{instanceGroupManager}',
      {},
      [u'project', u'zone', u'instanceGroupManager'],
      'ComputeInstanceGroupManagersGetRequest',)
  INSTANCEGROUPS = (
      'instanceGroups',
      'projects/{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      {},
      [u'project', u'zone', u'instanceGroup'],
      'ComputeInstanceGroupsGetRequest',)
  INSTANCETEMPLATES = (
      'instanceTemplates',
      'projects/{project}/global/instanceTemplates/{instanceTemplate}',
      {},
      [u'project', u'instanceTemplate'],
      'ComputeInstanceTemplatesGetRequest',)
  INSTANCES = (
      'instances',
      'projects/{project}/zones/{zone}/instances/{instance}',
      {},
      [u'project', u'zone', u'instance'],
      'ComputeInstancesGetRequest',)
  LICENSES = (
      'licenses',
      'projects/{project}/global/licenses/{license}',
      {},
      [u'project', u'license'],
      'ComputeLicensesGetRequest',)
  MACHINETYPES = (
      'machineTypes',
      'projects/{project}/zones/{zone}/machineTypes/{machineType}',
      {},
      [u'project', u'zone', u'machineType'],
      'ComputeMachineTypesGetRequest',)
  NETWORKS = (
      'networks',
      'projects/{project}/global/networks/{network}',
      {},
      [u'project', u'network'],
      'ComputeNetworksGetRequest',)
  PROJECTS = (
      'projects',
      'projects/{project}',
      {},
      [u'project'],
      'ComputeProjectsGetRequest',)
  REGIONAUTOSCALERS = (
      'regionAutoscalers',
      'projects/{project}/regions/{region}/autoscalers/{autoscaler}',
      {},
      [u'project', u'region', u'autoscaler'],
      'ComputeRegionAutoscalersGetRequest',)
  REGIONBACKENDSERVICES = (
      'regionBackendServices',
      'projects/{project}/regions/{region}/backendServices/{backendService}',
      {},
      [u'project', u'region', u'backendService'],
      'ComputeRegionBackendServicesGetRequest',)
  REGIONINSTANCEGROUPMANAGERS = (
      'regionInstanceGroupManagers',
      'projects/{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      {},
      [u'project', u'region', u'instanceGroupManager'],
      'ComputeRegionInstanceGroupManagersGetRequest',)
  REGIONINSTANCEGROUPS = (
      'regionInstanceGroups',
      'projects/{project}/regions/{region}/instanceGroups/{instanceGroup}',
      {},
      [u'project', u'region', u'instanceGroup'],
      'ComputeRegionInstanceGroupsGetRequest',)
  REGIONOPERATIONS = (
      'regionOperations',
      'projects/{project}/regions/{region}/operations/{operation}',
      {},
      [u'project', u'region', u'operation'],
      'ComputeRegionOperationsGetRequest',)
  REGIONS = (
      'regions',
      'projects/{project}/regions/{region}',
      {},
      [u'project', u'region'],
      'ComputeRegionsGetRequest',)
  ROUTERS = (
      'routers',
      'projects/{project}/regions/{region}/routers/{router}',
      {},
      [u'project', u'region', u'router'],
      'ComputeRoutersGetRequest',)
  ROUTES = (
      'routes',
      'projects/{project}/global/routes/{route}',
      {},
      [u'project', u'route'],
      'ComputeRoutesGetRequest',)
  SNAPSHOTS = (
      'snapshots',
      'projects/{project}/global/snapshots/{snapshot}',
      {},
      [u'project', u'snapshot'],
      'ComputeSnapshotsGetRequest',)
  SSLCERTIFICATES = (
      'sslCertificates',
      'projects/{project}/global/sslCertificates/{sslCertificate}',
      {},
      [u'project', u'sslCertificate'],
      'ComputeSslCertificatesGetRequest',)
  SUBNETWORKS = (
      'subnetworks',
      'projects/{project}/regions/{region}/subnetworks/{subnetwork}',
      {},
      [u'project', u'region', u'subnetwork'],
      'ComputeSubnetworksGetRequest',)
  TARGETHTTPPROXIES = (
      'targetHttpProxies',
      'projects/{project}/global/targetHttpProxies/{targetHttpProxy}',
      {},
      [u'project', u'targetHttpProxy'],
      'ComputeTargetHttpProxiesGetRequest',)
  TARGETHTTPSPROXIES = (
      'targetHttpsProxies',
      'projects/{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      {},
      [u'project', u'targetHttpsProxy'],
      'ComputeTargetHttpsProxiesGetRequest',)
  TARGETINSTANCES = (
      'targetInstances',
      'projects/{project}/zones/{zone}/targetInstances/{targetInstance}',
      {},
      [u'project', u'zone', u'targetInstance'],
      'ComputeTargetInstancesGetRequest',)
  TARGETPOOLS = (
      'targetPools',
      'projects/{project}/regions/{region}/targetPools/{targetPool}',
      {},
      [u'project', u'region', u'targetPool'],
      'ComputeTargetPoolsGetRequest',)
  TARGETSSLPROXIES = (
      'targetSslProxies',
      'projects/{project}/global/targetSslProxies/{targetSslProxy}',
      {},
      [u'project', u'targetSslProxy'],
      'ComputeTargetSslProxiesGetRequest',)
  TARGETVPNGATEWAYS = (
      'targetVpnGateways',
      'projects/{project}/regions/{region}/targetVpnGateways/'
      '{targetVpnGateway}',
      {},
      [u'project', u'region', u'targetVpnGateway'],
      'ComputeTargetVpnGatewaysGetRequest',)
  URLMAPS = (
      'urlMaps',
      'projects/{project}/global/urlMaps/{urlMap}',
      {},
      [u'project', u'urlMap'],
      'ComputeUrlMapsGetRequest',)
  VPNTUNNELS = (
      'vpnTunnels',
      'projects/{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      {},
      [u'project', u'region', u'vpnTunnel'],
      'ComputeVpnTunnelsGetRequest',)
  ZONEOPERATIONS = (
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      {},
      [u'project', u'zone', u'operation'],
      'ComputeZoneOperationsGetRequest',)
  ZONES = (
      'zones',
      'projects/{project}/zones/{zone}',
      {},
      [u'project', u'zone'],
      'ComputeZonesGetRequest',)

  def __init__(self, collection_name, path, flat_paths, params, request_type):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.request_type = request_type
