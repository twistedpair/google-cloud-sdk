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


class Collections(enum.Enum):
  """Collections for all supported apis."""

  APIKEYS_V1_PROJECTS_APIKEYS = (
      'apikeys',
      'v1',
      'https://apikeys.googleapis.com/v1/',
      'projects.apiKeys',
      'projects/{projectId}/apiKeys/{keyId}',
      [u'projectId', u'keyId'])
  APPENGINE_V1BETA5_APPS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps',
      'apps/{appsId}',
      [u'appsId'])
  APPENGINE_V1BETA5_APPS_LOCATIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps.locations',
      'apps/{appsId}/locations/{locationsId}',
      [u'appsId', u'locationsId'])
  APPENGINE_V1BETA5_APPS_OPERATIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps.operations',
      'apps/{appsId}/operations/{operationsId}',
      [u'appsId', u'operationsId'])
  APPENGINE_V1BETA5_APPS_SERVICES = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps.services',
      'apps/{appsId}/services/{servicesId}',
      [u'appsId', u'servicesId'])
  APPENGINE_V1BETA5_APPS_SERVICES_VERSIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps.services.versions',
      'apps/{appsId}/services/{servicesId}/versions/{versionsId}',
      [u'appsId', u'servicesId', u'versionsId'])
  APPENGINE_V1BETA5_APPS_SERVICES_VERSIONS_INSTANCES = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/v1beta5/',
      'apps.services.versions.instances',
      'apps/{appsId}/services/{servicesId}/versions/{versionsId}/instances/'
      '{instancesId}',
      [u'appsId', u'servicesId', u'versionsId', u'instancesId'])
  BIGQUERY_V2_DATASETS = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'datasets',
      'projects/{projectId}/datasets/{datasetId}',
      [u'projectId', u'datasetId'])
  BIGQUERY_V2_JOBS = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'jobs',
      'projects/{projectId}/jobs/{jobId}',
      [u'projectId', u'jobId'])
  BIGQUERY_V2_TABLES = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'tables',
      'projects/{projectId}/datasets/{datasetId}/tables/{tableId}',
      [u'projectId', u'datasetId', u'tableId'])
  BIGTABLEADMIN_V2_OPERATIONS = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/v2/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  BIGTABLEADMIN_V2_PROJECTS_INSTANCES = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/v2/',
      'projects.instances',
      'projects/{projectsId}/instances/{instancesId}',
      [u'projectsId', u'instancesId'])
  BIGTABLEADMIN_V2_PROJECTS_INSTANCES_CLUSTERS = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/v2/',
      'projects.instances.clusters',
      'projects/{projectsId}/instances/{instancesId}/clusters/{clustersId}',
      [u'projectsId', u'instancesId', u'clustersId'])
  BIGTABLEADMIN_V2_PROJECTS_INSTANCES_TABLES = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/v2/',
      'projects.instances.tables',
      'projects/{projectsId}/instances/{instancesId}/tables/{tablesId}',
      [u'projectsId', u'instancesId', u'tablesId'])
  BIGTABLECLUSTERADMIN_V1_OPERATIONS = (
      'bigtableclusteradmin',
      'v1',
      'https://bigtableclusteradmin.googleapis.com/v1/',
      'operations',
      '{+name}',
      [u'name'])
  BIGTABLECLUSTERADMIN_V1_PROJECTS_ZONES_CLUSTERS = (
      'bigtableclusteradmin',
      'v1',
      'https://bigtableclusteradmin.googleapis.com/v1/',
      'projects.zones.clusters',
      '{+name}',
      [u'name'])
  CLOUDBILLING_V1_BILLINGACCOUNTS = (
      'cloudbilling',
      'v1',
      'https://cloudbilling.googleapis.com/v1/',
      'billingAccounts',
      'billingAccounts/{billingAccountsId}',
      [u'billingAccountsId'])
  CLOUDBUILD_V1_OPERATIONS = (
      'cloudbuild',
      'v1',
      'https://cloudbuild.googleapis.com/v1/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  CLOUDBUILD_V1_PROJECTS_BUILDS = (
      'cloudbuild',
      'v1',
      'https://cloudbuild.googleapis.com/v1/',
      'projects.builds',
      'projects/{projectId}/builds/{id}',
      [u'projectId', u'id'])
  CLOUDBUILD_V1_PROJECTS_TRIGGERS = (
      'cloudbuild',
      'v1',
      'https://cloudbuild.googleapis.com/v1/',
      'projects.triggers',
      'projects/{projectId}/triggers/{triggerId}',
      [u'projectId', u'triggerId'])
  CLOUDDEBUGGER_V2_DEBUGGER_DEBUGGEES_BREAKPOINTS = (
      'clouddebugger',
      'v2',
      'https://clouddebugger.googleapis.com/v2/',
      'debugger.debuggees.breakpoints',
      'debugger/debuggees/{debuggeeId}/breakpoints/{breakpointId}',
      [u'debuggeeId', u'breakpointId'])
  CLOUDERRORREPORTING_V1BETA1_PROJECTS_GROUPS = (
      'clouderrorreporting',
      'v1beta1',
      'https://clouderrorreporting.googleapis.com/v1beta1/',
      'projects.groups',
      'projects/{projectsId}/groups/{groupsId}',
      [u'projectsId', u'groupsId'])
  CLOUDFUNCTIONS_V1BETA1_OPERATIONS = (
      'cloudfunctions',
      'v1beta1',
      'https://cloudfunctions.googleapis.com/v1beta1/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  CLOUDFUNCTIONS_V1BETA1_PROJECTS_REGIONS_FUNCTIONS = (
      'cloudfunctions',
      'v1beta1',
      'https://cloudfunctions.googleapis.com/v1beta1/',
      'projects.regions.functions',
      'projects/{projectsId}/regions/{regionsId}/functions/{functionsId}',
      [u'projectsId', u'regionsId', u'functionsId'])
  CLOUDFUNCTIONS_V1BETA2_OPERATIONS = (
      'cloudfunctions',
      'v1beta2',
      'https://cloudfunctions.googleapis.com/v1beta2/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  CLOUDFUNCTIONS_V1BETA2_PROJECTS_LOCATIONS_FUNCTIONS = (
      'cloudfunctions',
      'v1beta2',
      'https://cloudfunctions.googleapis.com/v1beta2/',
      'projects.locations.functions',
      'projects/{projectsId}/locations/{locationsId}/functions/{functionsId}',
      [u'projectsId', u'locationsId', u'functionsId'])
  CLOUDRESOURCEMANAGER_V1BETA1_ORGANIZATIONS = (
      'cloudresourcemanager',
      'v1beta1',
      'https://cloudresourcemanager.googleapis.com/v1beta1/',
      'organizations',
      'organizations/{organizationsId}',
      [u'organizationsId'])
  CLOUDRESOURCEMANAGER_V1BETA1_PROJECTS = (
      'cloudresourcemanager',
      'v1beta1',
      'https://cloudresourcemanager.googleapis.com/v1beta1/',
      'projects',
      'projects/{projectId}',
      [u'projectId'])
  CLOUDUSERACCOUNTS_ALPHA_GLOBALACCOUNTSOPERATIONS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/',
      'globalAccountsOperations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  CLOUDUSERACCOUNTS_ALPHA_GROUPS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/',
      'groups',
      'projects/{project}/global/groups/{groupName}',
      [u'project', u'groupName'])
  CLOUDUSERACCOUNTS_ALPHA_USERS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/',
      'users',
      'projects/{project}/global/users/{user}',
      [u'project', u'user'])
  CLOUDUSERACCOUNTS_BETA_GLOBALACCOUNTSOPERATIONS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/',
      'globalAccountsOperations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  CLOUDUSERACCOUNTS_BETA_GROUPS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/',
      'groups',
      'projects/{project}/global/groups/{groupName}',
      [u'project', u'groupName'])
  CLOUDUSERACCOUNTS_BETA_USERS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/',
      'users',
      'projects/{project}/global/users/{user}',
      [u'project', u'user'])
  COMPUTE_ALPHA_ADDRESSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'addresses',
      'projects/{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_ALPHA_AUTOSCALERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'autoscalers',
      'projects/{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_ALPHA_BACKENDBUCKETS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'backendBuckets',
      'projects/{project}/global/backendBuckets/{backendBucket}',
      [u'project', u'backendBucket'])
  COMPUTE_ALPHA_BACKENDSERVICES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'backendServices',
      'projects/{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_ALPHA_DISKTYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'diskTypes',
      'projects/{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_ALPHA_DISKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'disks',
      'projects/{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_ALPHA_FIREWALLS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'firewalls',
      'projects/{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_ALPHA_FORWARDINGRULES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'forwardingRules',
      'projects/{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_ALPHA_GLOBALADDRESSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'globalAddresses',
      'projects/{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_ALPHA_GLOBALFORWARDINGRULES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'globalForwardingRules',
      'projects/{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_ALPHA_GLOBALOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'globalOperations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_ALPHA_HEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'healthChecks',
      'projects/{project}/global/healthChecks/{healthCheck}',
      [u'project', u'healthCheck'])
  COMPUTE_ALPHA_HTTPHEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'httpHealthChecks',
      'projects/{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_ALPHA_HTTPSHEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'httpsHealthChecks',
      'projects/{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_ALPHA_IMAGES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'images',
      'projects/{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_ALPHA_INSTANCEGROUPMANAGERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'instanceGroupManagers',
      'projects/{project}/zones/{zone}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_ALPHA_INSTANCEGROUPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'instanceGroups',
      'projects/{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_ALPHA_INSTANCETEMPLATES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'instanceTemplates',
      'projects/{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_ALPHA_INSTANCES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'instances',
      'projects/{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_ALPHA_LICENSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'licenses',
      'projects/{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_ALPHA_MACHINETYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'machineTypes',
      'projects/{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_ALPHA_NETWORKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'networks',
      'projects/{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_ALPHA_PROJECTS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'projects',
      'projects/{project}',
      [u'project'])
  COMPUTE_ALPHA_REGIONAUTOSCALERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionAutoscalers',
      'projects/{project}/regions/{region}/autoscalers/{autoscaler}',
      [u'project', u'region', u'autoscaler'])
  COMPUTE_ALPHA_REGIONBACKENDSERVICES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionBackendServices',
      'projects/{project}/regions/{region}/backendServices/{backendService}',
      [u'project', u'region', u'backendService'])
  COMPUTE_ALPHA_REGIONDISKTYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionDiskTypes',
      'projects/{project}/regions/{region}/diskTypes/{diskType}',
      [u'project', u'region', u'diskType'])
  COMPUTE_ALPHA_REGIONDISKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionDisks',
      'projects/{project}/regions/{region}/disks/{disk}',
      [u'project', u'region', u'disk'])
  COMPUTE_ALPHA_REGIONINSTANCEGROUPMANAGERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionInstanceGroupManagers',
      'projects/{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'region', u'instanceGroupManager'])
  COMPUTE_ALPHA_REGIONINSTANCEGROUPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionInstanceGroups',
      'projects/{project}/regions/{region}/instanceGroups/{instanceGroup}',
      [u'project', u'region', u'instanceGroup'])
  COMPUTE_ALPHA_REGIONOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regionOperations',
      'projects/{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_ALPHA_REGIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'regions',
      'projects/{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_ALPHA_ROUTERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'routers',
      'projects/{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_ALPHA_ROUTES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'routes',
      'projects/{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_ALPHA_SNAPSHOTS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'snapshots',
      'projects/{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_ALPHA_SSLCERTIFICATES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'sslCertificates',
      'projects/{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_ALPHA_SUBNETWORKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'subnetworks',
      'projects/{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_ALPHA_TARGETHTTPPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetHttpProxies',
      'projects/{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_ALPHA_TARGETHTTPSPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetHttpsProxies',
      'projects/{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_ALPHA_TARGETINSTANCES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetInstances',
      'projects/{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_ALPHA_TARGETPOOLS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetPools',
      'projects/{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_ALPHA_TARGETSSLPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetSslProxies',
      'projects/{project}/global/targetSslProxies/{targetSslProxy}',
      [u'project', u'targetSslProxy'])
  COMPUTE_ALPHA_TARGETTCPPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetTcpProxies',
      'projects/{project}/global/targetTcpProxies/{targetTcpProxy}',
      [u'project', u'targetTcpProxy'])
  COMPUTE_ALPHA_TARGETVPNGATEWAYS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'targetVpnGateways',
      'projects/{project}/regions/{region}/targetVpnGateways/'
      '{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_ALPHA_URLMAPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'urlMaps',
      'projects/{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_ALPHA_VPNTUNNELS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'vpnTunnels',
      'projects/{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_ALPHA_ZONEOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_ALPHA_ZONES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/',
      'zones',
      'projects/{project}/zones/{zone}',
      [u'project', u'zone'])
  COMPUTE_BETA_ADDRESSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'addresses',
      'projects/{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_BETA_AUTOSCALERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'autoscalers',
      'projects/{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_BETA_BACKENDSERVICES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'backendServices',
      'projects/{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_BETA_DISKTYPES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'diskTypes',
      'projects/{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_BETA_DISKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'disks',
      'projects/{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_BETA_FIREWALLS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'firewalls',
      'projects/{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_BETA_FORWARDINGRULES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'forwardingRules',
      'projects/{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_BETA_GLOBALADDRESSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'globalAddresses',
      'projects/{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_BETA_GLOBALFORWARDINGRULES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'globalForwardingRules',
      'projects/{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_BETA_GLOBALOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'globalOperations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_BETA_HEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'healthChecks',
      'projects/{project}/global/healthChecks/{healthCheck}',
      [u'project', u'healthCheck'])
  COMPUTE_BETA_HTTPHEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'httpHealthChecks',
      'projects/{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_BETA_HTTPSHEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'httpsHealthChecks',
      'projects/{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_BETA_IMAGES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'images',
      'projects/{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_BETA_INSTANCEGROUPMANAGERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'instanceGroupManagers',
      'projects/{project}/zones/{zone}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_BETA_INSTANCEGROUPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'instanceGroups',
      'projects/{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_BETA_INSTANCETEMPLATES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'instanceTemplates',
      'projects/{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_BETA_INSTANCES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'instances',
      'projects/{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_BETA_LICENSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'licenses',
      'projects/{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_BETA_MACHINETYPES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'machineTypes',
      'projects/{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_BETA_NETWORKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'networks',
      'projects/{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_BETA_PROJECTS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'projects',
      'projects/{project}',
      [u'project'])
  COMPUTE_BETA_REGIONAUTOSCALERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'regionAutoscalers',
      'projects/{project}/regions/{region}/autoscalers/{autoscaler}',
      [u'project', u'region', u'autoscaler'])
  COMPUTE_BETA_REGIONINSTANCEGROUPMANAGERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'regionInstanceGroupManagers',
      'projects/{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'region', u'instanceGroupManager'])
  COMPUTE_BETA_REGIONINSTANCEGROUPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'regionInstanceGroups',
      'projects/{project}/regions/{region}/instanceGroups/{instanceGroup}',
      [u'project', u'region', u'instanceGroup'])
  COMPUTE_BETA_REGIONOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'regionOperations',
      'projects/{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_BETA_REGIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'regions',
      'projects/{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_BETA_ROUTERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'routers',
      'projects/{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_BETA_ROUTES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'routes',
      'projects/{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_BETA_SNAPSHOTS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'snapshots',
      'projects/{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_BETA_SSLCERTIFICATES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'sslCertificates',
      'projects/{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_BETA_SUBNETWORKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'subnetworks',
      'projects/{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_BETA_TARGETHTTPPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetHttpProxies',
      'projects/{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_BETA_TARGETHTTPSPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetHttpsProxies',
      'projects/{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_BETA_TARGETINSTANCES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetInstances',
      'projects/{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_BETA_TARGETPOOLS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetPools',
      'projects/{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_BETA_TARGETSSLPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetSslProxies',
      'projects/{project}/global/targetSslProxies/{targetSslProxy}',
      [u'project', u'targetSslProxy'])
  COMPUTE_BETA_TARGETVPNGATEWAYS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'targetVpnGateways',
      'projects/{project}/regions/{region}/targetVpnGateways/'
      '{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_BETA_URLMAPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'urlMaps',
      'projects/{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_BETA_VPNTUNNELS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'vpnTunnels',
      'projects/{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_BETA_ZONEOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_BETA_ZONES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/',
      'zones',
      'projects/{project}/zones/{zone}',
      [u'project', u'zone'])
  COMPUTE_V1_ADDRESSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'addresses',
      'projects/{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_V1_AUTOSCALERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'autoscalers',
      'projects/{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_V1_BACKENDSERVICES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'backendServices',
      'projects/{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_V1_DISKTYPES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'diskTypes',
      'projects/{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_V1_DISKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'disks',
      'projects/{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_V1_FIREWALLS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'firewalls',
      'projects/{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_V1_FORWARDINGRULES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'forwardingRules',
      'projects/{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_V1_GLOBALADDRESSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'globalAddresses',
      'projects/{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_V1_GLOBALFORWARDINGRULES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'globalForwardingRules',
      'projects/{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_V1_GLOBALOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'globalOperations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_V1_HEALTHCHECKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'healthChecks',
      'projects/{project}/global/healthChecks/{healthCheck}',
      [u'project', u'healthCheck'])
  COMPUTE_V1_HTTPHEALTHCHECKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'httpHealthChecks',
      'projects/{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_V1_HTTPSHEALTHCHECKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'httpsHealthChecks',
      'projects/{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_V1_IMAGES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'images',
      'projects/{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_V1_INSTANCEGROUPMANAGERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'instanceGroupManagers',
      'projects/{project}/zones/{zone}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_V1_INSTANCEGROUPS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'instanceGroups',
      'projects/{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_V1_INSTANCETEMPLATES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'instanceTemplates',
      'projects/{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_V1_INSTANCES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'instances',
      'projects/{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_V1_LICENSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'licenses',
      'projects/{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_V1_MACHINETYPES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'machineTypes',
      'projects/{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_V1_NETWORKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'networks',
      'projects/{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_V1_PROJECTS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'projects',
      'projects/{project}',
      [u'project'])
  COMPUTE_V1_REGIONOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'regionOperations',
      'projects/{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_V1_REGIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'regions',
      'projects/{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_V1_ROUTERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'routers',
      'projects/{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_V1_ROUTES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'routes',
      'projects/{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_V1_SNAPSHOTS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'snapshots',
      'projects/{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_V1_SSLCERTIFICATES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'sslCertificates',
      'projects/{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_V1_SUBNETWORKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'subnetworks',
      'projects/{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_V1_TARGETHTTPPROXIES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetHttpProxies',
      'projects/{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_V1_TARGETHTTPSPROXIES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetHttpsProxies',
      'projects/{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_V1_TARGETINSTANCES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetInstances',
      'projects/{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_V1_TARGETPOOLS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetPools',
      'projects/{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_V1_TARGETSSLPROXIES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetSslProxies',
      'projects/{project}/global/targetSslProxies/{targetSslProxy}',
      [u'project', u'targetSslProxy'])
  COMPUTE_V1_TARGETVPNGATEWAYS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'targetVpnGateways',
      'projects/{project}/regions/{region}/targetVpnGateways/'
      '{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_V1_URLMAPS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'urlMaps',
      'projects/{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_V1_VPNTUNNELS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'vpnTunnels',
      'projects/{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_V1_ZONEOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_V1_ZONES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/',
      'zones',
      'projects/{project}/zones/{zone}',
      [u'project', u'zone'])
  CONTAINER_V1_PROJECTS_ZONES_CLUSTERS = (
      'container',
      'v1',
      'https://container.googleapis.com/v1/',
      'projects.zones.clusters',
      'projects/{projectId}/zones/{zone}/clusters/{clusterId}',
      [u'projectId', u'zone', u'clusterId'])
  CONTAINER_V1_PROJECTS_ZONES_CLUSTERS_NODEPOOLS = (
      'container',
      'v1',
      'https://container.googleapis.com/v1/',
      'projects.zones.clusters.nodePools',
      'projects/{projectId}/zones/{zone}/clusters/{clusterId}/nodePools/'
      '{nodePoolId}',
      [u'projectId', u'zone', u'clusterId', u'nodePoolId'])
  CONTAINER_V1_PROJECTS_ZONES_OPERATIONS = (
      'container',
      'v1',
      'https://container.googleapis.com/v1/',
      'projects.zones.operations',
      'projects/{projectId}/zones/{zone}/operations/{operationId}',
      [u'projectId', u'zone', u'operationId'])
  CONTAINERANALYSIS_V1ALPHA1_PROJECTS_OCCURRENCES = (
      'containeranalysis',
      'v1alpha1',
      'https://containeranalysis.googleapis.com/v1alpha1/',
      'projects.occurrences',
      'projects/{projectsId}/occurrences/{occurrencesId}',
      [u'projectsId', u'occurrencesId'])
  CONTAINERANALYSIS_V1ALPHA1_PROVIDERS_NOTES = (
      'containeranalysis',
      'v1alpha1',
      'https://containeranalysis.googleapis.com/v1alpha1/',
      'providers.notes',
      'providers/{providersId}/notes/{notesId}',
      [u'providersId', u'notesId'])
  DATAFLOW_V1B3_PROJECTS_JOBS = (
      'dataflow',
      'v1b3',
      'https://dataflow.googleapis.com/v1b3/',
      'projects.jobs',
      'projects/{projectId}/jobs/{jobId}',
      [u'projectId', u'jobId'])
  DATAPROC_V1_PROJECTS_REGIONS_CLUSTERS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/v1/',
      'projects.regions.clusters',
      'projects/{projectId}/regions/{region}/clusters/{clusterName}',
      [u'projectId', u'region', u'clusterName'])
  DATAPROC_V1_PROJECTS_REGIONS_JOBS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/v1/',
      'projects.regions.jobs',
      'projects/{projectId}/regions/{region}/jobs/{jobId}',
      [u'projectId', u'region', u'jobId'])
  DATAPROC_V1_PROJECTS_REGIONS_OPERATIONS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/v1/',
      'projects.regions.operations',
      'projects/{projectsId}/regions/{regionsId}/operations/{operationsId}',
      [u'projectsId', u'regionsId', u'operationsId'])
  DEPLOYMENTMANAGER_ALPHA_DEPLOYMENTS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/',
      'deployments',
      'projects/{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_ALPHA_MANIFESTS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/',
      'manifests',
      'projects/{project}/global/deployments/{deployment}/manifests/'
      '{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_ALPHA_OPERATIONS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/',
      'operations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_ALPHA_RESOURCES = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/',
      'resources',
      'projects/{project}/global/deployments/{deployment}/resources/'
      '{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_ALPHA_TYPES = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/',
      'types',
      'projects/{project}/global/types/{type}',
      [u'project', u'type'])
  DEPLOYMENTMANAGER_V2_DEPLOYMENTS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/',
      'deployments',
      'projects/{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_V2_MANIFESTS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/',
      'manifests',
      'projects/{project}/global/deployments/{deployment}/manifests/'
      '{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_V2_OPERATIONS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/',
      'operations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_V2_RESOURCES = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/',
      'resources',
      'projects/{project}/global/deployments/{deployment}/resources/'
      '{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_V2BETA_DEPLOYMENTS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/',
      'deployments',
      'projects/{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_V2BETA_MANIFESTS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/',
      'manifests',
      'projects/{project}/global/deployments/{deployment}/manifests/'
      '{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_V2BETA_OPERATIONS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/',
      'operations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_V2BETA_RESOURCES = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/',
      'resources',
      'projects/{project}/global/deployments/{deployment}/resources/'
      '{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_V2BETA_TYPES = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/',
      'types',
      'projects/{project}/global/types/{type}',
      [u'project', u'type'])
  DNS_V1_CHANGES = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/',
      'changes',
      'projects/{project}/managedZones/{managedZone}/changes/{changeId}',
      [u'project', u'managedZone', u'changeId'])
  DNS_V1_MANAGEDZONES = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/',
      'managedZones',
      'projects/{project}/managedZones/{managedZone}',
      [u'project', u'managedZone'])
  DNS_V1_PROJECTS = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/',
      'projects',
      'projects/{project}',
      [u'project'])
  DNS_V1BETA1_CHANGES = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/',
      'changes',
      'projects/{project}/managedZones/{managedZone}/changes/{changeId}',
      [u'project', u'managedZone', u'changeId'])
  DNS_V1BETA1_MANAGEDZONES = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/',
      'managedZones',
      'projects/{project}/managedZones/{managedZone}',
      [u'project', u'managedZone'])
  DNS_V1BETA1_PROJECTS = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/',
      'projects',
      'projects/{project}',
      [u'project'])
  GENOMICS_V1_ANNOTATIONS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'annotations',
      'annotations/{annotationId}',
      [u'annotationId'])
  GENOMICS_V1_ANNOTATIONSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'annotationsets',
      'annotationsets/{annotationSetId}',
      [u'annotationSetId'])
  GENOMICS_V1_CALLSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'callsets',
      'callsets/{callSetId}',
      [u'callSetId'])
  GENOMICS_V1_DATASETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'datasets',
      'datasets/{datasetId}',
      [u'datasetId'])
  GENOMICS_V1_OPERATIONS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  GENOMICS_V1_READGROUPSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'readgroupsets',
      'readgroupsets/{readGroupSetId}',
      [u'readGroupSetId'])
  GENOMICS_V1_REFERENCES = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'references',
      'references/{referenceId}',
      [u'referenceId'])
  GENOMICS_V1_REFERENCESETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'referencesets',
      'referencesets/{referenceSetId}',
      [u'referenceSetId'])
  GENOMICS_V1_VARIANTS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'variants',
      'variants/{variantId}',
      [u'variantId'])
  GENOMICS_V1_VARIANTSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/v1/',
      'variantsets',
      'variantsets/{variantSetId}',
      [u'variantSetId'])
  GENOMICS_V1ALPHA2_OPERATIONS = (
      'genomics',
      'v1alpha2',
      'https://genomics.googleapis.com/v1alpha2/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  GENOMICS_V1ALPHA2_PIPELINES = (
      'genomics',
      'v1alpha2',
      'https://genomics.googleapis.com/v1alpha2/',
      'pipelines',
      'pipelines/{pipelineId}',
      [u'pipelineId'])
  IAM_V1_PROJECTS_SERVICEACCOUNTS = (
      'iam',
      'v1',
      'https://iam.googleapis.com/v1/',
      'projects.serviceAccounts',
      'projects/{projectsId}/serviceAccounts/{serviceAccountsId}',
      [u'projectsId', u'serviceAccountsId'])
  IAM_V1_PROJECTS_SERVICEACCOUNTS_KEYS = (
      'iam',
      'v1',
      'https://iam.googleapis.com/v1/',
      'projects.serviceAccounts.keys',
      'projects/{projectsId}/serviceAccounts/{serviceAccountsId}/keys/'
      '{keysId}',
      [u'projectsId', u'serviceAccountsId', u'keysId'])
  LOGGING_V1BETA3_PROJECTS_LOGSERVICES_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/v1beta3/',
      'projects.logServices.sinks',
      'projects/{projectsId}/logServices/{logServicesId}/sinks/{sinksId}',
      [u'projectsId', u'logServicesId', u'sinksId'])
  LOGGING_V1BETA3_PROJECTS_LOGS_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/v1beta3/',
      'projects.logs.sinks',
      'projects/{projectsId}/logs/{logsId}/sinks/{sinksId}',
      [u'projectsId', u'logsId', u'sinksId'])
  LOGGING_V1BETA3_PROJECTS_METRICS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/v1beta3/',
      'projects.metrics',
      'projects/{projectsId}/metrics/{metricsId}',
      [u'projectsId', u'metricsId'])
  LOGGING_V1BETA3_PROJECTS_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/v1beta3/',
      'projects.sinks',
      'projects/{projectsId}/sinks/{sinksId}',
      [u'projectsId', u'sinksId'])
  LOGGING_V2BETA1_PROJECTS_METRICS = (
      'logging',
      'v2beta1',
      'https://logging.googleapis.com/v2beta1/',
      'projects.metrics',
      'projects/{projectsId}/metrics/{metricsId}',
      [u'projectsId', u'metricsId'])
  LOGGING_V2BETA1_PROJECTS_SINKS = (
      'logging',
      'v2beta1',
      'https://logging.googleapis.com/v2beta1/',
      'projects.sinks',
      'projects/{projectsId}/sinks/{sinksId}',
      [u'projectsId', u'sinksId'])
  MANAGER_V1BETA2_DEPLOYMENTS = (
      'manager',
      'v1beta2',
      'https://www.googleapis.com/manager/v1beta2/',
      'deployments',
      'projects/{projectId}/regions/{region}/deployments/{deploymentName}',
      [u'projectId', u'region', u'deploymentName'])
  MANAGER_V1BETA2_TEMPLATES = (
      'manager',
      'v1beta2',
      'https://www.googleapis.com/manager/v1beta2/',
      'templates',
      'projects/{projectId}/templates/{templateName}',
      [u'projectId', u'templateName'])
  ML_V1ALPHA3_PROJECTS_MODELS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/v1alpha3/',
      'projects.models',
      'projects/{projectsId}/models/{modelsId}',
      [u'projectsId', u'modelsId'])
  ML_V1ALPHA3_PROJECTS_MODELS_VERSIONS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/v1alpha3/',
      'projects.models.versions',
      'projects/{projectsId}/models/{modelsId}/versions/{versionsId}',
      [u'projectsId', u'modelsId', u'versionsId'])
  ML_V1ALPHA3_PROJECTS_OPERATIONS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/v1alpha3/',
      'projects.operations',
      'projects/{projectsId}/operations/{operationsId}',
      [u'projectsId', u'operationsId'])
  ML_V1BETA1_PROJECTS_JOBS = (
      'ml',
      'v1beta1',
      'https://ml.googleapis.com/v1beta1/',
      'projects.jobs',
      'projects/{projectsId}/jobs/{jobsId}',
      [u'projectsId', u'jobsId'])
  ML_V1BETA1_PROJECTS_MODELS = (
      'ml',
      'v1beta1',
      'https://ml.googleapis.com/v1beta1/',
      'projects.models',
      'projects/{projectsId}/models/{modelsId}',
      [u'projectsId', u'modelsId'])
  ML_V1BETA1_PROJECTS_MODELS_VERSIONS = (
      'ml',
      'v1beta1',
      'https://ml.googleapis.com/v1beta1/',
      'projects.models.versions',
      'projects/{projectsId}/models/{modelsId}/versions/{versionsId}',
      [u'projectsId', u'modelsId', u'versionsId'])
  ML_V1BETA1_PROJECTS_OPERATIONS = (
      'ml',
      'v1beta1',
      'https://ml.googleapis.com/v1beta1/',
      'projects.operations',
      'projects/{projectsId}/operations/{operationsId}',
      [u'projectsId', u'operationsId'])
  PUBSUB_V1_PROJECTS_SUBSCRIPTIONS = (
      'pubsub',
      'v1',
      'https://pubsub.googleapis.com/v1/',
      'projects.subscriptions',
      'projects/{projectsId}/subscriptions/{subscriptionsId}',
      [u'projectsId', u'subscriptionsId'])
  PUBSUB_V1_PROJECTS_TOPICS = (
      'pubsub',
      'v1',
      'https://pubsub.googleapis.com/v1/',
      'projects.topics',
      'projects/{projectsId}/topics/{topicsId}',
      [u'projectsId', u'topicsId'])
  REPLICAPOOLUPDATER_V1BETA1_ROLLINGUPDATES = (
      'replicapoolupdater',
      'v1beta1',
      'https://www.googleapis.com/replicapoolupdater/v1beta1/',
      'rollingUpdates',
      'projects/{project}/zones/{zone}/rollingUpdates/{rollingUpdate}',
      [u'project', u'zone', u'rollingUpdate'])
  REPLICAPOOLUPDATER_V1BETA1_ZONEOPERATIONS = (
      'replicapoolupdater',
      'v1beta1',
      'https://www.googleapis.com/replicapoolupdater/v1beta1/',
      'zoneOperations',
      'projects/{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  RUNTIMECONFIG_V1BETA1_PROJECTS_CONFIGS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/v1beta1/',
      'projects.configs',
      'projects/{projectsId}/configs/{configsId}',
      [u'projectsId', u'configsId'])
  RUNTIMECONFIG_V1BETA1_PROJECTS_CONFIGS_OPERATIONS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/v1beta1/',
      'projects.configs.operations',
      'projects/{projectsId}/configs/{configsId}/operations/{operationsId}',
      [u'projectsId', u'configsId', u'operationsId'])
  RUNTIMECONFIG_V1BETA1_PROJECTS_CONFIGS_VARIABLES = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/v1beta1/',
      'projects.configs.variables',
      'projects/{projectsId}/configs/{configsId}/variables/{variablesId}',
      [u'projectsId', u'configsId', u'variablesId'])
  RUNTIMECONFIG_V1BETA1_PROJECTS_CONFIGS_WAITERS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/v1beta1/',
      'projects.configs.waiters',
      'projects/{projectsId}/configs/{configsId}/waiters/{waitersId}',
      [u'projectsId', u'configsId', u'waitersId'])
  SERVICEMANAGEMENT_V1_OPERATIONS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'operations',
      'operations/{operationsId}',
      [u'operationsId'])
  SERVICEMANAGEMENT_V1_SERVICES = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'services',
      'services/{serviceName}',
      [u'serviceName'])
  SERVICEMANAGEMENT_V1_SERVICES_CONFIGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'services.configs',
      'services/{serviceName}/configs/{configId}',
      [u'serviceName', u'configId'])
  SERVICEMANAGEMENT_V1_SERVICES_CUSTOMERSETTINGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'services.customerSettings',
      'services/{serviceName}/customerSettings/{customerId}',
      [u'serviceName', u'customerId'])
  SERVICEMANAGEMENT_V1_SERVICES_PROJECTSETTINGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'services.projectSettings',
      'services/{serviceName}/projectSettings/{consumerProjectId}',
      [u'serviceName', u'consumerProjectId'])
  SERVICEMANAGEMENT_V1_SERVICES_ROLLOUTS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/v1/',
      'services.rollouts',
      'services/{serviceName}/rollouts/{rolloutId}',
      [u'serviceName', u'rolloutId'])
  SERVICEREGISTRY_V1ALPHA_ENDPOINTS = (
      'serviceregistry',
      'v1alpha',
      'https://www.googleapis.com/serviceregistry/v1alpha/',
      'endpoints',
      'projects/{project}/global/endpoints/{endpoint}',
      [u'project', u'endpoint'])
  SERVICEREGISTRY_V1ALPHA_OPERATIONS = (
      'serviceregistry',
      'v1alpha',
      'https://www.googleapis.com/serviceregistry/v1alpha/',
      'operations',
      'projects/{project}/global/operations/{operation}',
      [u'project', u'operation'])
  SOURCE_V1_PROJECTS_REPOS = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos',
      'projects/{projectId}/repos/{repoName}',
      [u'projectId', u'repoName'])
  SOURCE_V1_PROJECTS_REPOS_ALIASES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.aliases',
      'projects/{projectId}/repos/{repoName}/aliases/{kind}/{name}',
      [u'projectId', u'repoName', u'kind', u'name'])
  SOURCE_V1_PROJECTS_REPOS_ALIASES_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.aliases.files',
      'projects/{projectId}/repos/{repoName}/aliases/{kind}/{name}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'kind', u'name', u'filesId'])
  SOURCE_V1_PROJECTS_REPOS_REVISIONS = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.revisions',
      'projects/{projectId}/repos/{repoName}/revisions/{revisionId}',
      [u'projectId', u'repoName', u'revisionId'])
  SOURCE_V1_PROJECTS_REPOS_REVISIONS_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.revisions.files',
      'projects/{projectId}/repos/{repoName}/revisions/{revisionId}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'revisionId', u'filesId'])
  SOURCE_V1_PROJECTS_REPOS_WORKSPACES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.workspaces',
      'projects/{projectId}/repos/{repoName}/workspaces/{name}',
      [u'projectId', u'repoName', u'name'])
  SOURCE_V1_PROJECTS_REPOS_WORKSPACES_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.workspaces.files',
      'projects/{projectId}/repos/{repoName}/workspaces/{name}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'name', u'filesId'])
  SOURCE_V1_PROJECTS_REPOS_WORKSPACES_SNAPSHOTS = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.workspaces.snapshots',
      'projects/{projectId}/repos/{repoName}/workspaces/{name}/snapshots/'
      '{snapshotId}',
      [u'projectId', u'repoName', u'name', u'snapshotId'])
  SOURCE_V1_PROJECTS_REPOS_WORKSPACES_SNAPSHOTS_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/v1/',
      'projects.repos.workspaces.snapshots.files',
      'projects/{projectId}/repos/{repoName}/workspaces/{name}/snapshots/'
      '{snapshotId}/files/{filesId}',
      [u'projectId', u'repoName', u'name', u'snapshotId', u'filesId'])
  SQL_V1BETA3_BACKUPRUNS = (
      'sql',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'backupRuns',
      'projects/{project}/instances/{instance}/backupRuns/'
      '{backupConfiguration}',
      [u'project', u'instance', u'backupConfiguration'])
  SQL_V1BETA3_INSTANCES = (
      'sql',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'instances',
      'projects/{project}/instances/{instance}',
      [u'project', u'instance'])
  SQL_V1BETA3_OPERATIONS = (
      'sql',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'operations',
      'projects/{project}/instances/{instance}/operations/{operation}',
      [u'project', u'instance', u'operation'])
  SQL_V1BETA3_SSLCERTS = (
      'sql',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'sslCerts',
      'projects/{project}/instances/{instance}/sslCerts/{sha1Fingerprint}',
      [u'project', u'instance', u'sha1Fingerprint'])
  SQL_V1BETA4_BACKUPRUNS = (
      'sql',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'backupRuns',
      'projects/{project}/instances/{instance}/backupRuns/{id}',
      [u'project', u'instance', u'id'])
  SQL_V1BETA4_DATABASES = (
      'sql',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'databases',
      'projects/{project}/instances/{instance}/databases/{database}',
      [u'project', u'instance', u'database'])
  SQL_V1BETA4_INSTANCES = (
      'sql',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'instances',
      'projects/{project}/instances/{instance}',
      [u'project', u'instance'])
  SQL_V1BETA4_OPERATIONS = (
      'sql',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'operations',
      'projects/{project}/operations/{operation}',
      [u'project', u'operation'])
  SQL_V1BETA4_SSLCERTS = (
      'sql',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sslCerts',
      'projects/{project}/instances/{instance}/sslCerts/{sha1Fingerprint}',
      [u'project', u'instance', u'sha1Fingerprint'])
  STORAGE_V1_BUCKETACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'bucketAccessControls',
      'b/{bucket}/acl/{entity}',
      [u'bucket', u'entity'])
  STORAGE_V1_BUCKETS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'buckets',
      'b/{bucket}',
      [u'bucket'])
  STORAGE_V1_DEFAULTOBJECTACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'defaultObjectAccessControls',
      'b/{bucket}/defaultObjectAcl/{entity}',
      [u'bucket', u'entity'])
  STORAGE_V1_NOTIFICATIONS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'notifications',
      'notifications/{notification}',
      [u'notification'])
  STORAGE_V1_OBJECTACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'objectAccessControls',
      'b/{bucket}/o/{object}/acl/{entity}',
      [u'bucket', u'object', u'entity'])
  STORAGE_V1_OBJECTS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'objects',
      'b/{bucket}/o/{object}',
      [u'bucket', u'object'])
  TESTING_V1_PROJECTS_DEVICES = (
      'testing',
      'v1',
      'https://testing.googleapis.com/v1/',
      'projects.devices',
      'projects/{projectId}/devices/{deviceId}',
      [u'projectId', u'deviceId'])
  TESTING_V1_PROJECTS_TESTMATRICES = (
      'testing',
      'v1',
      'https://testing.googleapis.com/v1/',
      'projects.testMatrices',
      'projects/{projectId}/testMatrices/{testMatrixId}',
      [u'projectId', u'testMatrixId'])
  TESTING_V1_TESTENVIRONMENTCATALOG = (
      'testing',
      'v1',
      'https://testing.googleapis.com/v1/',
      'testEnvironmentCatalog',
      'testEnvironmentCatalog/{environmentType}',
      [u'environmentType'])
  TOOLRESULTS_V1BETA3_PROJECTS_HISTORIES = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/',
      'projects.histories',
      'projects/{projectId}/histories/{historyId}',
      [u'projectId', u'historyId'])
  TOOLRESULTS_V1BETA3_PROJECTS_HISTORIES_EXECUTIONS = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/',
      'projects.histories.executions',
      'projects/{projectId}/histories/{historyId}/executions/{executionId}',
      [u'projectId', u'historyId', u'executionId'])
  TOOLRESULTS_V1BETA3_PROJECTS_HISTORIES_EXECUTIONS_STEPS = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/',
      'projects.histories.executions.steps',
      'projects/{projectId}/histories/{historyId}/executions/{executionId}/'
      'steps/{stepId}',
      [u'projectId', u'historyId', u'executionId', u'stepId'])

  def __init__(self, api_name, api_version, base_url,
               collection_name, path, params):
    self.api_name = api_name
    self.api_version = api_version
    self.base_url = base_url
    self.collection_name = collection_name
    self.path = path
    self.params = params
