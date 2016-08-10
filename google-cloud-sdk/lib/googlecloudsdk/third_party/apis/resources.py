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

  APIKEYS_PROJECTS_APIKEYS = (
      'apikeys',
      'v1',
      'https://apikeys.googleapis.com/',
      'apikeys.projects.apiKeys',
      'v1/projects/{projectId}/apiKeys/{keyId}',
      [u'projectId', u'keyId'])
  APPENGINE_APPS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps',
      'v1beta5/apps/{appsId}',
      [u'appsId'])
  APPENGINE_APPS_LOCATIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps.locations',
      'v1beta5/apps/{appsId}/locations/{locationsId}',
      [u'appsId', u'locationsId'])
  APPENGINE_APPS_OPERATIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps.operations',
      'v1beta5/apps/{appsId}/operations/{operationsId}',
      [u'appsId', u'operationsId'])
  APPENGINE_APPS_SERVICES = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps.services',
      'v1beta5/apps/{appsId}/services/{servicesId}',
      [u'appsId', u'servicesId'])
  APPENGINE_APPS_SERVICES_VERSIONS = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps.services.versions',
      'v1beta5/apps/{appsId}/services/{servicesId}/versions/{versionsId}',
      [u'appsId', u'servicesId', u'versionsId'])
  APPENGINE_APPS_SERVICES_VERSIONS_INSTANCES = (
      'appengine',
      'v1beta5',
      'https://appengine.googleapis.com/',
      'appengine.apps.services.versions.instances',
      'v1beta5/apps/{appsId}/services/{servicesId}/versions/{versionsId}/'
      'instances/{instancesId}',
      [u'appsId', u'servicesId', u'versionsId', u'instancesId'])
  BIGQUERY_DATASETS = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'bigquery.datasets',
      'projects/{projectId}/datasets/{datasetId}',
      [u'projectId', u'datasetId'])
  BIGQUERY_JOBS = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'bigquery.jobs',
      'projects/{projectId}/jobs/{jobId}',
      [u'projectId', u'jobId'])
  BIGQUERY_TABLES = (
      'bigquery',
      'v2',
      'https://www.googleapis.com/bigquery/v2/',
      'bigquery.tables',
      'projects/{projectId}/datasets/{datasetId}/tables/{tableId}',
      [u'projectId', u'datasetId', u'tableId'])
  BIGTABLEADMIN_OPERATIONS = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/',
      'bigtableadmin.operations',
      'v2/operations/{operationsId}',
      [u'operationsId'])
  BIGTABLEADMIN_PROJECTS_INSTANCES = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/',
      'bigtableadmin.projects.instances',
      'v2/projects/{projectsId}/instances/{instancesId}',
      [u'projectsId', u'instancesId'])
  BIGTABLEADMIN_PROJECTS_INSTANCES_CLUSTERS = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/',
      'bigtableadmin.projects.instances.clusters',
      'v2/projects/{projectsId}/instances/{instancesId}/clusters/{clustersId}',
      [u'projectsId', u'instancesId', u'clustersId'])
  BIGTABLEADMIN_PROJECTS_INSTANCES_TABLES = (
      'bigtableadmin',
      'v2',
      'https://bigtableadmin.googleapis.com/',
      'bigtableadmin.projects.instances.tables',
      'v2/projects/{projectsId}/instances/{instancesId}/tables/{tablesId}',
      [u'projectsId', u'instancesId', u'tablesId'])
  BIGTABLECLUSTERADMIN_OPERATIONS = (
      'bigtableclusteradmin',
      'v1',
      'https://bigtableclusteradmin.googleapis.com/v1/',
      'bigtableclusteradmin.operations',
      '{+name}',
      [u'name'])
  BIGTABLECLUSTERADMIN_PROJECTS_ZONES_CLUSTERS = (
      'bigtableclusteradmin',
      'v1',
      'https://bigtableclusteradmin.googleapis.com/v1/',
      'bigtableclusteradmin.projects.zones.clusters',
      '{+name}',
      [u'name'])
  CLOUDBILLING_BILLINGACCOUNTS = (
      'cloudbilling',
      'v1',
      'https://cloudbilling.googleapis.com/',
      'cloudbilling.billingAccounts',
      'v1/billingAccounts/{billingAccountsId}',
      [u'billingAccountsId'])
  CLOUDBUILD_OPERATIONS = (
      'cloudbuild',
      'v1',
      'https://cloudbuild.googleapis.com/',
      'cloudbuild.operations',
      'v1/operations/{operationsId}',
      [u'operationsId'])
  CLOUDBUILD_PROJECTS_BUILDS = (
      'cloudbuild',
      'v1',
      'https://cloudbuild.googleapis.com/',
      'cloudbuild.projects.builds',
      'v1/projects/{projectId}/builds/{id}',
      [u'projectId', u'id'])
  CLOUDDEBUGGER_DEBUGGER_DEBUGGEES_BREAKPOINTS = (
      'clouddebugger',
      'v2',
      'https://clouddebugger.googleapis.com/',
      'clouddebugger.debugger.debuggees.breakpoints',
      'v2/debugger/debuggees/{debuggeeId}/breakpoints/{breakpointId}',
      [u'debuggeeId', u'breakpointId'])
  CLOUDERRORREPORTING_PROJECTS_GROUPS = (
      'clouderrorreporting',
      'v1beta1',
      'https://clouderrorreporting.googleapis.com/',
      'clouderrorreporting.projects.groups',
      'v1beta1/projects/{projectsId}/groups/{groupsId}',
      [u'projectsId', u'groupsId'])
  CLOUDFUNCTIONS_OPERATIONS = (
      'cloudfunctions',
      'v1beta1',
      'https://cloudfunctions.googleapis.com/',
      'cloudfunctions.operations',
      'v1beta1/operations/{operationsId}',
      [u'operationsId'])
  CLOUDFUNCTIONS_PROJECTS_REGIONS_FUNCTIONS = (
      'cloudfunctions',
      'v1beta1',
      'https://cloudfunctions.googleapis.com/',
      'cloudfunctions.projects.regions.functions',
      'v1beta1/projects/{projectsId}/regions/{regionsId}/functions/'
      '{functionsId}',
      [u'projectsId', u'regionsId', u'functionsId'])
  CLOUDRESOURCEMANAGER_ORGANIZATIONS = (
      'cloudresourcemanager',
      'v1beta1',
      'https://cloudresourcemanager.googleapis.com/',
      'cloudresourcemanager.organizations',
      'v1beta1/organizations/{organizationsId}',
      [u'organizationsId'])
  CLOUDRESOURCEMANAGER_PROJECTS = (
      'cloudresourcemanager',
      'v1beta1',
      'https://cloudresourcemanager.googleapis.com/',
      'cloudresourcemanager.projects',
      'v1beta1/projects/{projectId}',
      [u'projectId'])
  CLOUDUSERACCOUNTS_GLOBALACCOUNTSOPERATIONS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/projects/',
      'clouduseraccounts.globalAccountsOperations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  CLOUDUSERACCOUNTS_GROUPS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/projects/',
      'clouduseraccounts.groups',
      '{project}/global/groups/{groupName}',
      [u'project', u'groupName'])
  CLOUDUSERACCOUNTS_USERS = (
      'clouduseraccounts',
      'alpha',
      'https://www.googleapis.com/clouduseraccounts/alpha/projects/',
      'clouduseraccounts.users',
      '{project}/global/users/{user}',
      [u'project', u'user'])
  CLOUDUSERACCOUNTS_GLOBALACCOUNTSOPERATIONS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/projects/',
      'clouduseraccounts.globalAccountsOperations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  CLOUDUSERACCOUNTS_GROUPS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/projects/',
      'clouduseraccounts.groups',
      '{project}/global/groups/{groupName}',
      [u'project', u'groupName'])
  CLOUDUSERACCOUNTS_USERS = (
      'clouduseraccounts',
      'beta',
      'https://www.googleapis.com/clouduseraccounts/beta/projects/',
      'clouduseraccounts.users',
      '{project}/global/users/{user}',
      [u'project', u'user'])
  COMPUTE_ADDRESSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.addresses',
      '{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_AUTOSCALERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.autoscalers',
      '{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_BACKENDBUCKETS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.backendBuckets',
      '{project}/global/backendBuckets/{backendBucket}',
      [u'project', u'backendBucket'])
  COMPUTE_BACKENDSERVICES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.backendServices',
      '{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_DISKTYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.diskTypes',
      '{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_DISKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.disks',
      '{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_FIREWALLS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.firewalls',
      '{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_FORWARDINGRULES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.forwardingRules',
      '{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_GLOBALADDRESSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.globalAddresses',
      '{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_GLOBALFORWARDINGRULES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.globalForwardingRules',
      '{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_GLOBALOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.globalOperations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_HEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.healthChecks',
      '{project}/global/healthChecks/{healthCheck}',
      [u'project', u'healthCheck'])
  COMPUTE_HTTPHEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.httpHealthChecks',
      '{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_HTTPSHEALTHCHECKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.httpsHealthChecks',
      '{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_IMAGES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.images',
      '{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_INSTANCEGROUPMANAGERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.instanceGroupManagers',
      '{project}/zones/{zone}/instanceGroupManagers/{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_INSTANCEGROUPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.instanceGroups',
      '{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_INSTANCETEMPLATES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.instanceTemplates',
      '{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_INSTANCES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.instances',
      '{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_LICENSES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.licenses',
      '{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_MACHINETYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.machineTypes',
      '{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_NETWORKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.networks',
      '{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_PROJECTS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.projects',
      '{project}',
      [u'project'])
  COMPUTE_REGIONAUTOSCALERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionAutoscalers',
      '{project}/regions/{region}/autoscalers/{autoscaler}',
      [u'project', u'region', u'autoscaler'])
  COMPUTE_REGIONBACKENDSERVICES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionBackendServices',
      '{project}/regions/{region}/backendServices/{backendService}',
      [u'project', u'region', u'backendService'])
  COMPUTE_REGIONDISKTYPES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionDiskTypes',
      '{project}/regions/{region}/diskTypes/{diskType}',
      [u'project', u'region', u'diskType'])
  COMPUTE_REGIONDISKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionDisks',
      '{project}/regions/{region}/disks/{disk}',
      [u'project', u'region', u'disk'])
  COMPUTE_REGIONINSTANCEGROUPMANAGERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionInstanceGroupManagers',
      '{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'region', u'instanceGroupManager'])
  COMPUTE_REGIONINSTANCEGROUPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionInstanceGroups',
      '{project}/regions/{region}/instanceGroups/{instanceGroup}',
      [u'project', u'region', u'instanceGroup'])
  COMPUTE_REGIONOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regionOperations',
      '{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_REGIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.regions',
      '{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_ROUTERS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.routers',
      '{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_ROUTES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.routes',
      '{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_SNAPSHOTS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.snapshots',
      '{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_SSLCERTIFICATES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.sslCertificates',
      '{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_SUBNETWORKS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.subnetworks',
      '{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_TARGETHTTPPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetHttpProxies',
      '{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_TARGETHTTPSPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetHttpsProxies',
      '{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_TARGETINSTANCES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetInstances',
      '{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_TARGETPOOLS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetPools',
      '{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_TARGETSSLPROXIES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetSslProxies',
      '{project}/global/targetSslProxies/{targetSslProxy}',
      [u'project', u'targetSslProxy'])
  COMPUTE_TARGETVPNGATEWAYS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.targetVpnGateways',
      '{project}/regions/{region}/targetVpnGateways/{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_URLMAPS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.urlMaps',
      '{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_VPNTUNNELS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.vpnTunnels',
      '{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_ZONEOPERATIONS = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.zoneOperations',
      '{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_ZONES = (
      'compute',
      'alpha',
      'https://www.googleapis.com/compute/alpha/projects/',
      'compute.zones',
      '{project}/zones/{zone}',
      [u'project', u'zone'])
  COMPUTE_ADDRESSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.addresses',
      '{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_AUTOSCALERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.autoscalers',
      '{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_BACKENDSERVICES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.backendServices',
      '{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_DISKTYPES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.diskTypes',
      '{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_DISKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.disks',
      '{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_FIREWALLS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.firewalls',
      '{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_FORWARDINGRULES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.forwardingRules',
      '{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_GLOBALADDRESSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.globalAddresses',
      '{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_GLOBALFORWARDINGRULES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.globalForwardingRules',
      '{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_GLOBALOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.globalOperations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_HEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.healthChecks',
      '{project}/global/healthChecks/{healthCheck}',
      [u'project', u'healthCheck'])
  COMPUTE_HTTPHEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.httpHealthChecks',
      '{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_HTTPSHEALTHCHECKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.httpsHealthChecks',
      '{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_IMAGES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.images',
      '{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_INSTANCEGROUPMANAGERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.instanceGroupManagers',
      '{project}/zones/{zone}/instanceGroupManagers/{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_INSTANCEGROUPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.instanceGroups',
      '{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_INSTANCETEMPLATES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.instanceTemplates',
      '{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_INSTANCES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.instances',
      '{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_LICENSES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.licenses',
      '{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_MACHINETYPES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.machineTypes',
      '{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_NETWORKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.networks',
      '{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_PROJECTS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.projects',
      '{project}',
      [u'project'])
  COMPUTE_REGIONAUTOSCALERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.regionAutoscalers',
      '{project}/regions/{region}/autoscalers/{autoscaler}',
      [u'project', u'region', u'autoscaler'])
  COMPUTE_REGIONINSTANCEGROUPMANAGERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.regionInstanceGroupManagers',
      '{project}/regions/{region}/instanceGroupManagers/'
      '{instanceGroupManager}',
      [u'project', u'region', u'instanceGroupManager'])
  COMPUTE_REGIONINSTANCEGROUPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.regionInstanceGroups',
      '{project}/regions/{region}/instanceGroups/{instanceGroup}',
      [u'project', u'region', u'instanceGroup'])
  COMPUTE_REGIONOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.regionOperations',
      '{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_REGIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.regions',
      '{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_ROUTERS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.routers',
      '{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_ROUTES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.routes',
      '{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_SNAPSHOTS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.snapshots',
      '{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_SSLCERTIFICATES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.sslCertificates',
      '{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_SUBNETWORKS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.subnetworks',
      '{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_TARGETHTTPPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetHttpProxies',
      '{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_TARGETHTTPSPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetHttpsProxies',
      '{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_TARGETINSTANCES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetInstances',
      '{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_TARGETPOOLS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetPools',
      '{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_TARGETSSLPROXIES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetSslProxies',
      '{project}/global/targetSslProxies/{targetSslProxy}',
      [u'project', u'targetSslProxy'])
  COMPUTE_TARGETVPNGATEWAYS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.targetVpnGateways',
      '{project}/regions/{region}/targetVpnGateways/{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_URLMAPS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.urlMaps',
      '{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_VPNTUNNELS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.vpnTunnels',
      '{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_ZONEOPERATIONS = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.zoneOperations',
      '{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_ZONES = (
      'compute',
      'beta',
      'https://www.googleapis.com/compute/beta/projects/',
      'compute.zones',
      '{project}/zones/{zone}',
      [u'project', u'zone'])
  COMPUTE_ADDRESSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.addresses',
      '{project}/regions/{region}/addresses/{address}',
      [u'project', u'region', u'address'])
  COMPUTE_AUTOSCALERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.autoscalers',
      '{project}/zones/{zone}/autoscalers/{autoscaler}',
      [u'project', u'zone', u'autoscaler'])
  COMPUTE_BACKENDSERVICES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.backendServices',
      '{project}/global/backendServices/{backendService}',
      [u'project', u'backendService'])
  COMPUTE_DISKTYPES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.diskTypes',
      '{project}/zones/{zone}/diskTypes/{diskType}',
      [u'project', u'zone', u'diskType'])
  COMPUTE_DISKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.disks',
      '{project}/zones/{zone}/disks/{disk}',
      [u'project', u'zone', u'disk'])
  COMPUTE_FIREWALLS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.firewalls',
      '{project}/global/firewalls/{firewall}',
      [u'project', u'firewall'])
  COMPUTE_FORWARDINGRULES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.forwardingRules',
      '{project}/regions/{region}/forwardingRules/{forwardingRule}',
      [u'project', u'region', u'forwardingRule'])
  COMPUTE_GLOBALADDRESSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.globalAddresses',
      '{project}/global/addresses/{address}',
      [u'project', u'address'])
  COMPUTE_GLOBALFORWARDINGRULES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.globalForwardingRules',
      '{project}/global/forwardingRules/{forwardingRule}',
      [u'project', u'forwardingRule'])
  COMPUTE_GLOBALOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.globalOperations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  COMPUTE_HTTPHEALTHCHECKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.httpHealthChecks',
      '{project}/global/httpHealthChecks/{httpHealthCheck}',
      [u'project', u'httpHealthCheck'])
  COMPUTE_HTTPSHEALTHCHECKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.httpsHealthChecks',
      '{project}/global/httpsHealthChecks/{httpsHealthCheck}',
      [u'project', u'httpsHealthCheck'])
  COMPUTE_IMAGES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.images',
      '{project}/global/images/{image}',
      [u'project', u'image'])
  COMPUTE_INSTANCEGROUPMANAGERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.instanceGroupManagers',
      '{project}/zones/{zone}/instanceGroupManagers/{instanceGroupManager}',
      [u'project', u'zone', u'instanceGroupManager'])
  COMPUTE_INSTANCEGROUPS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.instanceGroups',
      '{project}/zones/{zone}/instanceGroups/{instanceGroup}',
      [u'project', u'zone', u'instanceGroup'])
  COMPUTE_INSTANCETEMPLATES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.instanceTemplates',
      '{project}/global/instanceTemplates/{instanceTemplate}',
      [u'project', u'instanceTemplate'])
  COMPUTE_INSTANCES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.instances',
      '{project}/zones/{zone}/instances/{instance}',
      [u'project', u'zone', u'instance'])
  COMPUTE_LICENSES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.licenses',
      '{project}/global/licenses/{license}',
      [u'project', u'license'])
  COMPUTE_MACHINETYPES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.machineTypes',
      '{project}/zones/{zone}/machineTypes/{machineType}',
      [u'project', u'zone', u'machineType'])
  COMPUTE_NETWORKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.networks',
      '{project}/global/networks/{network}',
      [u'project', u'network'])
  COMPUTE_PROJECTS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.projects',
      '{project}',
      [u'project'])
  COMPUTE_REGIONOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.regionOperations',
      '{project}/regions/{region}/operations/{operation}',
      [u'project', u'region', u'operation'])
  COMPUTE_REGIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.regions',
      '{project}/regions/{region}',
      [u'project', u'region'])
  COMPUTE_ROUTERS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.routers',
      '{project}/regions/{region}/routers/{router}',
      [u'project', u'region', u'router'])
  COMPUTE_ROUTES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.routes',
      '{project}/global/routes/{route}',
      [u'project', u'route'])
  COMPUTE_SNAPSHOTS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.snapshots',
      '{project}/global/snapshots/{snapshot}',
      [u'project', u'snapshot'])
  COMPUTE_SSLCERTIFICATES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.sslCertificates',
      '{project}/global/sslCertificates/{sslCertificate}',
      [u'project', u'sslCertificate'])
  COMPUTE_SUBNETWORKS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.subnetworks',
      '{project}/regions/{region}/subnetworks/{subnetwork}',
      [u'project', u'region', u'subnetwork'])
  COMPUTE_TARGETHTTPPROXIES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.targetHttpProxies',
      '{project}/global/targetHttpProxies/{targetHttpProxy}',
      [u'project', u'targetHttpProxy'])
  COMPUTE_TARGETHTTPSPROXIES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.targetHttpsProxies',
      '{project}/global/targetHttpsProxies/{targetHttpsProxy}',
      [u'project', u'targetHttpsProxy'])
  COMPUTE_TARGETINSTANCES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.targetInstances',
      '{project}/zones/{zone}/targetInstances/{targetInstance}',
      [u'project', u'zone', u'targetInstance'])
  COMPUTE_TARGETPOOLS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.targetPools',
      '{project}/regions/{region}/targetPools/{targetPool}',
      [u'project', u'region', u'targetPool'])
  COMPUTE_TARGETVPNGATEWAYS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.targetVpnGateways',
      '{project}/regions/{region}/targetVpnGateways/{targetVpnGateway}',
      [u'project', u'region', u'targetVpnGateway'])
  COMPUTE_URLMAPS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.urlMaps',
      '{project}/global/urlMaps/{urlMap}',
      [u'project', u'urlMap'])
  COMPUTE_VPNTUNNELS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.vpnTunnels',
      '{project}/regions/{region}/vpnTunnels/{vpnTunnel}',
      [u'project', u'region', u'vpnTunnel'])
  COMPUTE_ZONEOPERATIONS = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.zoneOperations',
      '{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  COMPUTE_ZONES = (
      'compute',
      'v1',
      'https://www.googleapis.com/compute/v1/projects/',
      'compute.zones',
      '{project}/zones/{zone}',
      [u'project', u'zone'])
  CONTAINER_PROJECTS_ZONES_CLUSTERS = (
      'container',
      'v1',
      'https://container.googleapis.com/',
      'container.projects.zones.clusters',
      'v1/projects/{projectId}/zones/{zone}/clusters/{clusterId}',
      [u'projectId', u'zone', u'clusterId'])
  CONTAINER_PROJECTS_ZONES_CLUSTERS_NODEPOOLS = (
      'container',
      'v1',
      'https://container.googleapis.com/',
      'container.projects.zones.clusters.nodePools',
      'v1/projects/{projectId}/zones/{zone}/clusters/{clusterId}/nodePools/'
      '{nodePoolId}',
      [u'projectId', u'zone', u'clusterId', u'nodePoolId'])
  CONTAINER_PROJECTS_ZONES_OPERATIONS = (
      'container',
      'v1',
      'https://container.googleapis.com/',
      'container.projects.zones.operations',
      'v1/projects/{projectId}/zones/{zone}/operations/{operationId}',
      [u'projectId', u'zone', u'operationId'])
  DATAFLOW_PROJECTS_JOBS = (
      'dataflow',
      'v1b3',
      'https://dataflow.googleapis.com/',
      'dataflow.projects.jobs',
      'v1b3/projects/{projectId}/jobs/{jobId}',
      [u'projectId', u'jobId'])
  DATAPROC_PROJECTS_REGIONS_CLUSTERS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/',
      'dataproc.projects.regions.clusters',
      'v1/projects/{projectId}/regions/{region}/clusters/{clusterName}',
      [u'projectId', u'region', u'clusterName'])
  DATAPROC_PROJECTS_REGIONS_JOBS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/',
      'dataproc.projects.regions.jobs',
      'v1/projects/{projectId}/regions/{region}/jobs/{jobId}',
      [u'projectId', u'region', u'jobId'])
  DATAPROC_PROJECTS_REGIONS_OPERATIONS = (
      'dataproc',
      'v1',
      'https://dataproc.googleapis.com/',
      'dataproc.projects.regions.operations',
      'v1/projects/{projectsId}/regions/{regionsId}/operations/{operationsId}',
      [u'projectsId', u'regionsId', u'operationsId'])
  DEPLOYMENTMANAGER_DEPLOYMENTS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/projects/',
      'deploymentmanager.deployments',
      '{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_MANIFESTS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/projects/',
      'deploymentmanager.manifests',
      '{project}/global/deployments/{deployment}/manifests/{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_OPERATIONS = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/projects/',
      'deploymentmanager.operations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_RESOURCES = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/projects/',
      'deploymentmanager.resources',
      '{project}/global/deployments/{deployment}/resources/{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_TYPES = (
      'deploymentmanager',
      'alpha',
      'https://www.googleapis.com/deploymentmanager/alpha/projects/',
      'deploymentmanager.types',
      '{project}/global/types/{type}',
      [u'project', u'type'])
  DEPLOYMENTMANAGER_DEPLOYMENTS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/projects/',
      'deploymentmanager.deployments',
      '{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_MANIFESTS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/projects/',
      'deploymentmanager.manifests',
      '{project}/global/deployments/{deployment}/manifests/{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_OPERATIONS = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/projects/',
      'deploymentmanager.operations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_RESOURCES = (
      'deploymentmanager',
      'v2',
      'https://www.googleapis.com/deploymentmanager/v2/projects/',
      'deploymentmanager.resources',
      '{project}/global/deployments/{deployment}/resources/{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_DEPLOYMENTS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/projects/',
      'deploymentmanager.deployments',
      '{project}/global/deployments/{deployment}',
      [u'project', u'deployment'])
  DEPLOYMENTMANAGER_MANIFESTS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/projects/',
      'deploymentmanager.manifests',
      '{project}/global/deployments/{deployment}/manifests/{manifest}',
      [u'project', u'deployment', u'manifest'])
  DEPLOYMENTMANAGER_OPERATIONS = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/projects/',
      'deploymentmanager.operations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  DEPLOYMENTMANAGER_RESOURCES = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/projects/',
      'deploymentmanager.resources',
      '{project}/global/deployments/{deployment}/resources/{resource}',
      [u'project', u'deployment', u'resource'])
  DEPLOYMENTMANAGER_TYPES = (
      'deploymentmanager',
      'v2beta',
      'https://www.googleapis.com/deploymentmanager/v2beta/projects/',
      'deploymentmanager.types',
      '{project}/global/types/{type}',
      [u'project', u'type'])
  DNS_CHANGES = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/projects/',
      'dns.changes',
      '{project}/managedZones/{managedZone}/changes/{changeId}',
      [u'project', u'managedZone', u'changeId'])
  DNS_MANAGEDZONES = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/projects/',
      'dns.managedZones',
      '{project}/managedZones/{managedZone}',
      [u'project', u'managedZone'])
  DNS_PROJECTS = (
      'dns',
      'v1',
      'https://www.googleapis.com/dns/v1/projects/',
      'dns.projects',
      '{project}',
      [u'project'])
  DNS_CHANGES = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/projects/',
      'dns.changes',
      '{project}/managedZones/{managedZone}/changes/{changeId}',
      [u'project', u'managedZone', u'changeId'])
  DNS_MANAGEDZONES = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/projects/',
      'dns.managedZones',
      '{project}/managedZones/{managedZone}',
      [u'project', u'managedZone'])
  DNS_PROJECTS = (
      'dns',
      'v1beta1',
      'https://www.googleapis.com/dns/v1beta1/projects/',
      'dns.projects',
      '{project}',
      [u'project'])
  GENOMICS_ANNOTATIONS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.annotations',
      'v1/annotations/{annotationId}',
      [u'annotationId'])
  GENOMICS_ANNOTATIONSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.annotationsets',
      'v1/annotationsets/{annotationSetId}',
      [u'annotationSetId'])
  GENOMICS_CALLSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.callsets',
      'v1/callsets/{callSetId}',
      [u'callSetId'])
  GENOMICS_DATASETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.datasets',
      'v1/datasets/{datasetId}',
      [u'datasetId'])
  GENOMICS_OPERATIONS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.operations',
      'v1/operations/{operationsId}',
      [u'operationsId'])
  GENOMICS_READGROUPSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.readgroupsets',
      'v1/readgroupsets/{readGroupSetId}',
      [u'readGroupSetId'])
  GENOMICS_REFERENCES = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.references',
      'v1/references/{referenceId}',
      [u'referenceId'])
  GENOMICS_REFERENCESETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.referencesets',
      'v1/referencesets/{referenceSetId}',
      [u'referenceSetId'])
  GENOMICS_VARIANTS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.variants',
      'v1/variants/{variantId}',
      [u'variantId'])
  GENOMICS_VARIANTSETS = (
      'genomics',
      'v1',
      'https://genomics.googleapis.com/',
      'genomics.variantsets',
      'v1/variantsets/{variantSetId}',
      [u'variantSetId'])
  GENOMICS_OPERATIONS = (
      'genomics',
      'v1alpha2',
      'https://genomics.googleapis.com/',
      'genomics.operations',
      'v1alpha2/operations/{operationsId}',
      [u'operationsId'])
  GENOMICS_PIPELINES = (
      'genomics',
      'v1alpha2',
      'https://genomics.googleapis.com/',
      'genomics.pipelines',
      'v1alpha2/pipelines/{pipelineId}',
      [u'pipelineId'])
  IAM_PROJECTS_SERVICEACCOUNTS = (
      'iam',
      'v1',
      'https://iam.googleapis.com/',
      'iam.projects.serviceAccounts',
      'v1/projects/{projectsId}/serviceAccounts/{serviceAccountsId}',
      [u'projectsId', u'serviceAccountsId'])
  IAM_PROJECTS_SERVICEACCOUNTS_KEYS = (
      'iam',
      'v1',
      'https://iam.googleapis.com/',
      'iam.projects.serviceAccounts.keys',
      'v1/projects/{projectsId}/serviceAccounts/{serviceAccountsId}/keys/'
      '{keysId}',
      [u'projectsId', u'serviceAccountsId', u'keysId'])
  LOGGING_PROJECTS_LOGSERVICES_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/',
      'logging.projects.logServices.sinks',
      'v1beta3/projects/{projectsId}/logServices/{logServicesId}/sinks/'
      '{sinksId}',
      [u'projectsId', u'logServicesId', u'sinksId'])
  LOGGING_PROJECTS_LOGS_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/',
      'logging.projects.logs.sinks',
      'v1beta3/projects/{projectsId}/logs/{logsId}/sinks/{sinksId}',
      [u'projectsId', u'logsId', u'sinksId'])
  LOGGING_PROJECTS_METRICS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/',
      'logging.projects.metrics',
      'v1beta3/projects/{projectsId}/metrics/{metricsId}',
      [u'projectsId', u'metricsId'])
  LOGGING_PROJECTS_SINKS = (
      'logging',
      'v1beta3',
      'https://logging.googleapis.com/',
      'logging.projects.sinks',
      'v1beta3/projects/{projectsId}/sinks/{sinksId}',
      [u'projectsId', u'sinksId'])
  LOGGING_PROJECTS_METRICS = (
      'logging',
      'v2beta1',
      'https://logging.googleapis.com/',
      'logging.projects.metrics',
      'v2beta1/projects/{projectsId}/metrics/{metricsId}',
      [u'projectsId', u'metricsId'])
  LOGGING_PROJECTS_SINKS = (
      'logging',
      'v2beta1',
      'https://logging.googleapis.com/',
      'logging.projects.sinks',
      'v2beta1/projects/{projectsId}/sinks/{sinksId}',
      [u'projectsId', u'sinksId'])
  MANAGER_DEPLOYMENTS = (
      'manager',
      'v1beta2',
      'https://www.googleapis.com/manager/v1beta2/projects/',
      'manager.deployments',
      '{projectId}/regions/{region}/deployments/{deploymentName}',
      [u'projectId', u'region', u'deploymentName'])
  MANAGER_TEMPLATES = (
      'manager',
      'v1beta2',
      'https://www.googleapis.com/manager/v1beta2/projects/',
      'manager.templates',
      '{projectId}/templates/{templateName}',
      [u'projectId', u'templateName'])
  ML_PROJECTS_MODELS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/',
      'ml.projects.models',
      'v1alpha3/projects/{projectsId}/models/{modelsId}',
      [u'projectsId', u'modelsId'])
  ML_PROJECTS_MODELS_VERSIONS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/',
      'ml.projects.models.versions',
      'v1alpha3/projects/{projectsId}/models/{modelsId}/versions/{versionsId}',
      [u'projectsId', u'modelsId', u'versionsId'])
  ML_PROJECTS_OPERATIONS = (
      'ml',
      'v1alpha3',
      'https://ml.googleapis.com/',
      'ml.projects.operations',
      'v1alpha3/projects/{projectsId}/operations/{operationsId}',
      [u'projectsId', u'operationsId'])
  PUBSUB_PROJECTS_SUBSCRIPTIONS = (
      'pubsub',
      'v1',
      'https://pubsub.googleapis.com/',
      'pubsub.projects.subscriptions',
      'v1/projects/{projectsId}/subscriptions/{subscriptionsId}',
      [u'projectsId', u'subscriptionsId'])
  PUBSUB_PROJECTS_TOPICS = (
      'pubsub',
      'v1',
      'https://pubsub.googleapis.com/',
      'pubsub.projects.topics',
      'v1/projects/{projectsId}/topics/{topicsId}',
      [u'projectsId', u'topicsId'])
  REPLICAPOOLUPDATER_ROLLINGUPDATES = (
      'replicapoolupdater',
      'v1beta1',
      'https://www.googleapis.com/replicapoolupdater/v1beta1/projects/',
      'replicapoolupdater.rollingUpdates',
      '{project}/zones/{zone}/rollingUpdates/{rollingUpdate}',
      [u'project', u'zone', u'rollingUpdate'])
  REPLICAPOOLUPDATER_ZONEOPERATIONS = (
      'replicapoolupdater',
      'v1beta1',
      'https://www.googleapis.com/replicapoolupdater/v1beta1/projects/',
      'replicapoolupdater.zoneOperations',
      '{project}/zones/{zone}/operations/{operation}',
      [u'project', u'zone', u'operation'])
  RUNTIMECONFIG_PROJECTS_CONFIGS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/',
      'runtimeconfig.projects.configs',
      'v1beta1/projects/{projectsId}/configs/{configsId}',
      [u'projectsId', u'configsId'])
  RUNTIMECONFIG_PROJECTS_CONFIGS_OPERATIONS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/',
      'runtimeconfig.projects.configs.operations',
      'v1beta1/projects/{projectsId}/configs/{configsId}/operations/'
      '{operationsId}',
      [u'projectsId', u'configsId', u'operationsId'])
  RUNTIMECONFIG_PROJECTS_CONFIGS_VARIABLES = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/',
      'runtimeconfig.projects.configs.variables',
      'v1beta1/projects/{projectsId}/configs/{configsId}/variables/'
      '{variablesId}',
      [u'projectsId', u'configsId', u'variablesId'])
  RUNTIMECONFIG_PROJECTS_CONFIGS_WAITERS = (
      'runtimeconfig',
      'v1beta1',
      'https://runtimeconfig.googleapis.com/',
      'runtimeconfig.projects.configs.waiters',
      'v1beta1/projects/{projectsId}/configs/{configsId}/waiters/{waitersId}',
      [u'projectsId', u'configsId', u'waitersId'])
  SERVICEMANAGEMENT_OPERATIONS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.operations',
      'v1/operations/{operationsId}',
      [u'operationsId'])
  SERVICEMANAGEMENT_SERVICES = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.services',
      'v1/services/{serviceName}',
      [u'serviceName'])
  SERVICEMANAGEMENT_SERVICES_CONFIGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.services.configs',
      'v1/services/{serviceName}/configs/{configId}',
      [u'serviceName', u'configId'])
  SERVICEMANAGEMENT_SERVICES_CUSTOMERSETTINGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.services.customerSettings',
      'v1/services/{serviceName}/customerSettings/{customerId}',
      [u'serviceName', u'customerId'])
  SERVICEMANAGEMENT_SERVICES_PROJECTSETTINGS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.services.projectSettings',
      'v1/services/{serviceName}/projectSettings/{consumerProjectId}',
      [u'serviceName', u'consumerProjectId'])
  SERVICEMANAGEMENT_SERVICES_ROLLOUTS = (
      'servicemanagement',
      'v1',
      'https://servicemanagement.googleapis.com/',
      'servicemanagement.services.rollouts',
      'v1/services/{serviceName}/rollouts/{rolloutId}',
      [u'serviceName', u'rolloutId'])
  SERVICEREGISTRY_ENDPOINTS = (
      'serviceregistry',
      'v1alpha',
      'https://www.googleapis.com/serviceregistry/v1alpha/projects/',
      'serviceregistry.endpoints',
      '{project}/global/endpoints/{endpoint}',
      [u'project', u'endpoint'])
  SERVICEREGISTRY_OPERATIONS = (
      'serviceregistry',
      'v1alpha',
      'https://www.googleapis.com/serviceregistry/v1alpha/projects/',
      'serviceregistry.operations',
      '{project}/global/operations/{operation}',
      [u'project', u'operation'])
  SOURCE_PROJECTS_REPOS = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos',
      'v1/projects/{projectId}/repos/{repoName}',
      [u'projectId', u'repoName'])
  SOURCE_PROJECTS_REPOS_ALIASES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.aliases',
      'v1/projects/{projectId}/repos/{repoName}/aliases/{kind}/{name}',
      [u'projectId', u'repoName', u'kind', u'name'])
  SOURCE_PROJECTS_REPOS_ALIASES_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.aliases.files',
      'v1/projects/{projectId}/repos/{repoName}/aliases/{kind}/{name}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'kind', u'name', u'filesId'])
  SOURCE_PROJECTS_REPOS_REVISIONS = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.revisions',
      'v1/projects/{projectId}/repos/{repoName}/revisions/{revisionId}',
      [u'projectId', u'repoName', u'revisionId'])
  SOURCE_PROJECTS_REPOS_REVISIONS_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.revisions.files',
      'v1/projects/{projectId}/repos/{repoName}/revisions/{revisionId}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'revisionId', u'filesId'])
  SOURCE_PROJECTS_REPOS_WORKSPACES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.workspaces',
      'v1/projects/{projectId}/repos/{repoName}/workspaces/{name}',
      [u'projectId', u'repoName', u'name'])
  SOURCE_PROJECTS_REPOS_WORKSPACES_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.workspaces.files',
      'v1/projects/{projectId}/repos/{repoName}/workspaces/{name}/files/'
      '{filesId}',
      [u'projectId', u'repoName', u'name', u'filesId'])
  SOURCE_PROJECTS_REPOS_WORKSPACES_SNAPSHOTS = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.workspaces.snapshots',
      'v1/projects/{projectId}/repos/{repoName}/workspaces/{name}/snapshots/'
      '{snapshotId}',
      [u'projectId', u'repoName', u'name', u'snapshotId'])
  SOURCE_PROJECTS_REPOS_WORKSPACES_SNAPSHOTS_FILES = (
      'source',
      'v1',
      'https://source.googleapis.com/',
      'source.projects.repos.workspaces.snapshots.files',
      'v1/projects/{projectId}/repos/{repoName}/workspaces/{name}/snapshots/'
      '{snapshotId}/files/{filesId}',
      [u'projectId', u'repoName', u'name', u'snapshotId', u'filesId'])
  SQL_BACKUPRUNS = (
      'sqladmin',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'sql.backupRuns',
      'projects/{project}/instances/{instance}/backupRuns/'
      '{backupConfiguration}',
      [u'project', u'instance', u'backupConfiguration'])
  SQL_INSTANCES = (
      'sqladmin',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'sql.instances',
      'projects/{project}/instances/{instance}',
      [u'project', u'instance'])
  SQL_OPERATIONS = (
      'sqladmin',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'sql.operations',
      'projects/{project}/instances/{instance}/operations/{operation}',
      [u'project', u'instance', u'operation'])
  SQL_SSLCERTS = (
      'sqladmin',
      'v1beta3',
      'https://www.googleapis.com/sql/v1beta3/',
      'sql.sslCerts',
      'projects/{project}/instances/{instance}/sslCerts/{sha1Fingerprint}',
      [u'project', u'instance', u'sha1Fingerprint'])
  SQL_BACKUPRUNS = (
      'sqladmin',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sql.backupRuns',
      'projects/{project}/instances/{instance}/backupRuns/{id}',
      [u'project', u'instance', u'id'])
  SQL_DATABASES = (
      'sqladmin',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sql.databases',
      'projects/{project}/instances/{instance}/databases/{database}',
      [u'project', u'instance', u'database'])
  SQL_INSTANCES = (
      'sqladmin',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sql.instances',
      'projects/{project}/instances/{instance}',
      [u'project', u'instance'])
  SQL_OPERATIONS = (
      'sqladmin',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sql.operations',
      'projects/{project}/operations/{operation}',
      [u'project', u'operation'])
  SQL_SSLCERTS = (
      'sqladmin',
      'v1beta4',
      'https://www.googleapis.com/sql/v1beta4/',
      'sql.sslCerts',
      'projects/{project}/instances/{instance}/sslCerts/{sha1Fingerprint}',
      [u'project', u'instance', u'sha1Fingerprint'])
  STORAGE_BUCKETACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.bucketAccessControls',
      'b/{bucket}/acl/{entity}',
      [u'bucket', u'entity'])
  STORAGE_BUCKETS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.buckets',
      'b/{bucket}',
      [u'bucket'])
  STORAGE_DEFAULTOBJECTACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.defaultObjectAccessControls',
      'b/{bucket}/defaultObjectAcl/{entity}',
      [u'bucket', u'entity'])
  STORAGE_NOTIFICATIONS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.notifications',
      'notifications/{notification}',
      [u'notification'])
  STORAGE_OBJECTACCESSCONTROLS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.objectAccessControls',
      'b/{bucket}/o/{object}/acl/{entity}',
      [u'bucket', u'object', u'entity'])
  STORAGE_OBJECTS = (
      'storage',
      'v1',
      'https://www.googleapis.com/storage/v1/',
      'storage.objects',
      'b/{bucket}/o/{object}',
      [u'bucket', u'object'])
  TESTING_PROJECTS_DEVICES = (
      'testing',
      'v1',
      'https://testing.googleapis.com/',
      'testing.projects.devices',
      'v1/projects/{projectId}/devices/{deviceId}',
      [u'projectId', u'deviceId'])
  TESTING_PROJECTS_TESTMATRICES = (
      'testing',
      'v1',
      'https://testing.googleapis.com/',
      'testing.projects.testMatrices',
      'v1/projects/{projectId}/testMatrices/{testMatrixId}',
      [u'projectId', u'testMatrixId'])
  TESTING_TESTENVIRONMENTCATALOG = (
      'testing',
      'v1',
      'https://testing.googleapis.com/',
      'testing.testEnvironmentCatalog',
      'v1/testEnvironmentCatalog/{environmentType}',
      [u'environmentType'])
  TOOLRESULTS_PROJECTS_HISTORIES = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/projects/',
      'toolresults.projects.histories',
      '{projectId}/histories/{historyId}',
      [u'projectId', u'historyId'])
  TOOLRESULTS_PROJECTS_HISTORIES_EXECUTIONS = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/projects/',
      'toolresults.projects.histories.executions',
      '{projectId}/histories/{historyId}/executions/{executionId}',
      [u'projectId', u'historyId', u'executionId'])
  TOOLRESULTS_PROJECTS_HISTORIES_EXECUTIONS_STEPS = (
      'toolresults',
      'v1beta3',
      'https://www.googleapis.com/toolresults/v1beta3/projects/',
      'toolresults.projects.histories.executions.steps',
      '{projectId}/histories/{historyId}/executions/{executionId}/steps/'
      '{stepId}',
      [u'projectId', u'historyId', u'executionId', u'stepId'])

  def __init__(self, api_name, api_version, base_url,
               collection_name, path, params):
    self.api_name = api_name
    self.api_version = api_version
    self.base_url = base_url
    self.collection_name = collection_name
    self.path = path
    self.params = params
