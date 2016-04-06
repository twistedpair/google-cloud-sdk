# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Resource info registry."""

from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_transform


class ResourceInfo(object):
  """collection => resource information mapping support.

  Attributes:
    async_collection: The operations collection when --async is set.
    bypass_cache: True if cache_command output should be used instead of cache.
    collection: Memoized collection name set by Get().
    cache_command: The gcloud command string that updates the URI cache.
    list_format: The default list format string for resource_printer.Print().
    simple_format: The --simple-list format string for resource_printer.Print().
    defaults: The resource projection transform defaults.
    transforms: Memoized combined transform symbols dict set by GetTransforms().

  Special format values:
    None: Ignore this format.
    'default': calliope.base.DEFAULT_FORMAT.
    'error': Resource print using this format is an error.
    'none': Do not print anything.
  """

  def __init__(self, async_collection=None, bypass_cache=False,
               cache_command=None, list_format=None, simple_format=None,
               defaults=None, transforms=None):
    self.collection = None  # memoized by Get().
    self.async_collection = async_collection
    self.bypass_cache = bypass_cache
    self.cache_command = cache_command
    self.list_format = list_format
    self.simple_format = simple_format
    self.defaults = defaults
    self.transforms = transforms  # memoized by GetTransforms().

  def GetTransforms(self):
    """Returns the combined transform symbols dict.

    Returns:
      The builtin transforms combined with the collection specific transforms
      if any.
    """
    if self.transforms:
      return self.transforms

    # The builtin transforms are always available.
    self.transforms = resource_transform.GetTransforms()

    # Check if there are any collection specific transforms.
    specific_transforms = resource_transform.GetTransforms(self.collection)
    if not specific_transforms:
      return self.transforms
    builtin_transforms = self.transforms
    self.transforms = {}
    self.transforms.update(builtin_transforms)
    self.transforms.update(specific_transforms)
    return self.transforms


RESOURCE_REGISTRY = {

    # apheleia

    'apheleia.projects.regions.functions': ResourceInfo(
        list_format="""
          table(
            name,
            status,
            triggers.len()
          )
        """,
    ),

    # appengine

    'app.instances': ResourceInfo(
        list_format="""
          table(
            service:sort=1,
            version:sort=2,
            id:sort=3,
            instance.status
          )
        """,
    ),

    'app.module_versions': ResourceInfo(
        list_format="""
          table(
            module,
            version,
            traffic_split.format("{0:.2f}", .)
          )
        """,
    ),

    'app.services': ResourceInfo(
        list_format="""
          table(
            id:label=SERVICE:sort=1,
            versions.len():label=NUM_VERSIONS
          )
        """,
    ),

    'app.versions': ResourceInfo(
        list_format="""
          table(
            service,
            id:label=VERSION,
            traffic_split.format("{0:.2f}", .),
            last_deployed_time.date("%Y-%m-%dT%H:%M:%S%Oz", undefined="-")
              :label=LAST_DEPLOYED,
            version.servingStatus
          )
        """,
    ),

    # autoscaler

    'autoscaler.instances': ResourceInfo(
        list_format="""
          table(
            name,
            description.yesno(no="-"),
            state.yesno(no="-"),
            state_details.yesno(no="-")
          )
        """,
    ),

    # bigquery

    'bigquery.datasets': ResourceInfo(
        list_format="""
          table(
            datasetReference.datasetId
          )
        """,
    ),

    'bigquery.jobs.describe': ResourceInfo(
        list_format="""
          table(
            job_type,
            state,
            start_time,
            duration,
            bytes_processed
          )
        """,
    ),

    'bigquery.jobs.list': ResourceInfo(
        list_format="""
          table(
            job_id,
            job_type,
            state,
            start_time,
            duration
          )
        """,
    ),

    'bigquery.jobs.wait': ResourceInfo(
        list_format="""
          table(
            job_type,
            state,
            start_time,
            duration,
            bytes_processed
          )
        """,
    ),

    'bigquery.projects': ResourceInfo(
        list_format="""
          table(
            projectReference.projectId,
            friendlyName
          )
        """,
    ),

    'bigquery.tables.list': ResourceInfo(
        list_format="""
          table(
            id,
            type:label=TABLE_OR_VIEW
          )
        """,
    ),

    # cloud billing

    'cloudbilling.billingAccounts': ResourceInfo(
        cache_command='billing accounts list',
        # TODO(b/22402915) Delete this when OP resource completion is supported.
        bypass_cache=True,
        list_format="""
          table(
            name.basename():label=ID,
            displayName:label=NAME,
            open
          )
        """,
    ),

    'cloudbilling.projectBillingInfo': ResourceInfo(
        list_format="""
          table(
            projectId,
            billingAccountName.basename():label=BILLING_ACCOUNT_ID,
            billingEnabled
          )
        """,
    ),

    # cloud resource manager

    'cloudresourcemanager.projects': ResourceInfo(
        cache_command='projects list',
        list_format="""
          table(
            projectId,
            name,
            projectNumber
          )
        """,
    ),

    # Cloud SDK client side resources

    # 'coudsdk.*': ...

    # compute

    'compute.addresses': ResourceInfo(
        # cache_command='compute addresses list',
        list_format="""
          table(
            name,
            region.basename(),
            address,
            status
          )
        """,
    ),

    'compute.autoscalers': ResourceInfo(
        async_collection='compute.operations',
        # cache_command='compute autoscaler list',
        list_format="""
          table(
            name,
            target.basename(),
            autoscalingPolicy.policy():label=POLICY
          )
        """,
    ),

    'compute.backendBuckets': ResourceInfo(
        # cache_command='compute backend-buckets list',
        list_format="""
          table(
            name,
            bucketName:label=GCS_BUCKET_NAME
          )
        """,
    ),

    'compute.backendServices': ResourceInfo(
        # cache_command='compute backend-services list',
        list_format="""
          table(
            name,
            backends[].group.list():label=BACKENDS,
            protocol
          )
        """,
    ),

    'compute.disks': ResourceInfo(
        # cache_command='compute disks list',
        list_format="""
          table(
            name,
            zone.basename(),
            sizeGb,
            type.basename(),
            status
          )
        """,
    ),

    'compute.diskTypes': ResourceInfo(
        # cache_command='compute disk-types list',
        list_format="""
          table(
            name,
            zone.basename(),
            validDiskSize:label=VALID_DISK_SIZES
          )
        """,
    ),

    'compute.firewalls': ResourceInfo(
        # cache_command='compute firewall-rules list',
        list_format="""
          table(
            name,
            network.basename(),
            sourceRanges.list():label=SRC_RANGES,
            allowed[].map().firewall_rule().list():label=RULES,
            sourceTags.list():label=SRC_TAGS,
            targetTags.list():label=TARGET_TAGS
          )
        """,
    ),

    'compute.forwardingRules': ResourceInfo(
        # cache_command='compute forwarding-rules list',
        list_format="""
          table(
            name,
            region.basename(),
            IPAddress,
            IPProtocol,
            target.scope()
          )
        """,
    ),

    'compute.groups': ResourceInfo(
        # cache_command='compute groups list',
        list_format="""
          table(
            name,
            members.len():label=NUM_MEMBERS,
            description
          )
        """,
    ),

    'compute.httpHealthChecks': ResourceInfo(
        # cache_command='compute http-health-checks list',
        list_format="""
          table(
            name,
            host,
            port,
            requestPath
          )
        """,
    ),

    'compute.httpsHealthChecks': ResourceInfo(
        # cache_command='compute https-health-checks list',
        list_format="""
          table(
            name,
            host,
            port,
            requestPath
          )
        """,
    ),

    'compute.images': ResourceInfo(
        # cache_command='compute images list',
        list_format="""
          table(
            name,
            selfLink.map().scope(projects).segment(0):label=PROJECT,
            image_alias():label=ALIAS,
            deprecated.state:label=DEPRECATED,
            status
          )
        """,
    ),

    'compute.instanceGroups': ResourceInfo(
        # cache_command='compute instance-groups list',
        list_format="""
          table(
            name,
            zone.basename(),
            network.basename(),
            isManaged:label=MANAGED,
            size:label=INSTANCES
          )
        """,
    ),

    'compute.instanceGroupManagers': ResourceInfo(
        # cache_command='compute instance-groups managed list',
        list_format="""
          table(
            name,
            zone.basename(),
            baseInstanceName,
            size,
            instanceGroup.basename():label=GROUP,
            instanceTemplate.basename(),
            autoscaled
          )
        """,
    ),

    'compute.instances': ResourceInfo(
        # cache_command='compute instances list',
        list_format="""
          table(
            name,
            zone.basename(),
            machineType.basename(),
            scheduling.preemptible.yesno(yes=true, no=''),
            networkInterfaces[0].networkIP:label=INTERNAL_IP,
            networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP,
            status
          )
        """,
    ),

    'compute.instanceTemplates': ResourceInfo(
        # cache_command='compute instance-templates list',
        list_format="""
          table(
            name,
            properties.machineType,
            properties.scheduling.preemptible.yesno(yes=true, no=''),
            creationTimestamp
          )
        """,
    ),

    'compute.machineTypes': ResourceInfo(
        # cache_command='compute machine-types list',
        list_format="""
          table(
            name,
            zone.basename(),
            guestCpus:label=CPUS,
            memoryMb.size(units_in=MiB, units_out=GiB):label=MEMORY_GB,
            deprecated.state:label=DEPRECATED
          )
        """,
    ),

    'compute.networks': ResourceInfo(
        # cache_command='compute networks list',
        list_format="""
          table(
            name,
            IPv4Range:label=IPV4_RANGE,
            gatewayIPv4
          )
        """,
    ),

    'compute.operations': ResourceInfo(
        list_format="""
          table(
            name,
            operationType:label=TYPE,
            targetLink.scope():label=TARGET,
            operation_http_status():label=HTTP_STATUS,
            status,
            insertTime:label=TIMESTAMP
          )
        """,
    ),

    'compute.projects': ResourceInfo(
        list_format="""
          value(
            format("There is no API support yet.")
          )
        """,
    ),

    'compute.regions': ResourceInfo(
        # cache_command='compute regions list',
        list_format="""
          table(
            name,
            quotas.metric.CPUS.quota():label=CPUS,
            quotas.metric.DISKS_TOTAL_GB.quota():label=DISKS_GB,
            quotas.metric.IN_USE_ADDRESSES.quota():label=ADDRESSES,
            quotas.metric.STATIC_ADDRESSES.quota():label=RESERVED_ADDRESSES,
            status():label=STATUS,
            deprecated.deleted:label=TURNDOWN_DATE
          )
        """,
    ),

    'compute.replicaPools': ResourceInfo(
        list_format="""
          table(
            name,
            currentNumReplicas
          )
        """,
    ),

    'compute.replicaPoolsReplicas': ResourceInfo(
        list_format="""
          table(
            name,
            status.templateVersion,
            status.state:label=STATUS
          )
        """,
    ),

    'compute.resourceViews': ResourceInfo(
        list_format="""
          value(
            uri()
          )
        """,
    ),

    'compute.resourceViewsResources': ResourceInfo(
        list_format="""
          value(
            uri()
          )
        """,
    ),

    'compute.routes': ResourceInfo(
        # cache_command='compute routes list',
        list_format="""
          table(
            name,
            network.basename(),
            destRange,
            firstof(nextHopInstance, nextHopGateway, nextHopIp).scope()
              :label=NEXT_HOP,
            priority
          )
        """,
    ),

    'compute.snapshots': ResourceInfo(
        # cache_command='compute snapshots list',
        list_format="""
          table(
            name,
            diskSizeGb,
            sourceDisk.scope():label=SRC_DISK,
            status
          )
        """,
    ),

    'compute.sslCertificates': ResourceInfo(
        # cache_command='compute ssl-certificates list',
        list_format="""
          table(
            name,
            creationTimestamp
          )
        """,
    ),

    'compute.targetHttpProxies': ResourceInfo(
        # cache_command='compute target-http-proxies list',
        list_format="""
          table(
            name,
            urlMap.basename()
          )
        """,
    ),

    'compute.targetHttpsProxies': ResourceInfo(
        # cache_command='compute target-https-proxies list',
        list_format="""
          table(
            name,
            sslCertificates.map().basename().list():label=SSL_CERTIFICATES,
            urlMap.basename()
          )
        """,
    ),

    'compute.targetSslProxies': ResourceInfo(
        # cache_command='compute target-ssl-proxies list',
        list_format="""
          table(
            name,
            sslCertificates.map().basename().list():label=SSL_CERTIFICATES
            service.basename()
            proxyHeader
          )
        """,
    ),

    'compute.targetInstances': ResourceInfo(
        # cache_command='compute target-instances list',
        list_format="""
          table(
            name,
            zone.basename(),
            instance.basename(),
            natPolicy
          )
        """,
    ),

    'compute.targetPools': ResourceInfo(
        # cache_command='compute pools list',
        list_format="""
          table(
            name,
            region.basename(),
            sessionAffinity,
            backupPool.basename():label=BACKUP,
            healthChecks[].map().basename().list():label=HEALTH_CHECKS
          )
        """,
    ),

    'compute.targetVpnGateways': ResourceInfo(
        # cache_command='compute vpn-gateways list',
        list_format="""
          table(
            name,
            network.basename(),
            region.basename()
          )
        """,
    ),

    'compute.urlMaps': ResourceInfo(
        # # cache_command='compute url-maps list',
        list_format="""
          table(
            name,
            defaultService.basename()
          )
        """,
    ),

    'compute.users': ResourceInfo(
        # cache_command='compute users list',
        list_format="""
          table(
            name,
            owner,
            description
          )
        """,
    ),

    'compute.vpnTunnels': ResourceInfo(
        # cache_command='compute vpn-tunnels list',
        list_format="""
          table(
            name,
            region.basename(),
            targetVpnGateway.basename():label=GATEWAY,
            peerIp:label=PEER_ADDRESS
          )
        """,
    ),

    'compute.zones': ResourceInfo(
        # cache_command='compute zones list',
        list_format="""
          table(
            name,
            region.basename(),
            status():label=STATUS,
            maintenanceWindows.next_maintenance():label=NEXT_MAINTENANCE,
            deprecated.deleted:label=TURNDOWN_DATE
          )
        """,
    ),

    # container

    'container.projects.zones.clusters': ResourceInfo(
        list_format="""
          table(
            name,
            zone,
            clusterApiVersion,
            endpoint:label=MASTER_IP,
            machineType,
            sourceImage,
            numNodes:label=NODES,
            status
          )
        """,
    ),

    'container.projects.zones.nodePools': ResourceInfo(
        list_format="""
          table(
            name,
            zone,
            machineType,
            diskSizeGb,
            version
          )
        """,
    ),

    'container.projects.zones.operations': ResourceInfo(
        list_format="""
          table(
            name,
            operationType:label=TYPE,
            zone,
            target,
            status,
            errorMessage
          )
        """,
    ),

    # dataflow

    'dataflow.jobs': ResourceInfo(
        list_format="""
          table(
            job_id:label=ID,
            job_name:label=NAME,
            job_type:label=TYPE,
            creation_time.yesno(no="-"),
            status
          )
        """,
    ),

    # dataproc

    'dataproc.clusters': ResourceInfo(
        list_format="""
          table(
            clusterName:label=NAME,
            configuration.numWorkers:label=WORKER_COUNT,
            status.state:label=STATUS,
            configuration.gceClusterConfiguration.zoneUri.zone()
          )
        """,
    ),

    'dataproc.jobs': ResourceInfo(
        async_collection='dataproc.operations',
        list_format="""
          table(
            reference.jobId,
            type.yesno(no="-"),
            status.state:label=STATUS
          )
        """,
    ),

    'dataproc.operations': ResourceInfo(
        list_format="""
          table(
            name:label=OPERATION_NAME,
            done
          )
        """,
    ),

    # debug

    'debug.logpoints': ResourceInfo(
        list_format="""
          table(
            id,
            location,
            logLevel:label=LEVEL,
            short_status():label=STATUS,
            condition,
            log_message_format
          )
        """,
    ),

    'debug.snapshots': ResourceInfo(
        list_format="""
          table(
            id,
            location,
            short_status():label=STATUS,
            consoleViewUrl:label=VIEW
          )
        """
    ),

    'debug.targets': ResourceInfo(
        list_format="""
          table(
            name,
            target_id:label=ID,
            description
          )
        """
    ),

    # deployment manager v2

    'deploymentmanager.deployments': ResourceInfo(
        async_collection='deployments.operations',
        list_format="""
          table(
            name,
            operation.operationType:label=LAST_OPERATION_TYPE,
            operation.status,
            description,
            manifest.basename(),
            update.errors.group(code, message)
          )
        """,
        simple_format="""
          [legend-log=status,
           empty-legend="No Deployments were found in your project!"]
          value(
            name
          )
        """,
    ),

    'deploymentmanager.operations': ResourceInfo(
        list_format="""
          table(
            name,
            operationType:label=TYPE,
            status,
            targetLink.basename():label=TARGET,
            error.errors.group(code, message)
          )
        """,
        simple_format="""
          [legend-log=status,
           empty-legend="No Operations were found in your project!"]
          value(
            name
          )
        """,
    ),

    'deploymentmanager.resources': ResourceInfo(
        list_format="""
          table(
            name,
            operationType,
            status.yesno(no="COMPLETED"):label=UPDATE_STATE,
            update.error.errors.group(code, message)
          )
        """,
        simple_format="""
          [legend-log=status,
           empty-legend="No Resources were found in your deployment!"]
          value(
            name
          )
        """,
    ),

    # dns

    'dns.changes': ResourceInfo(
        list_format="""
          table(
            id,
            startTime,
            status
          )
        """,
    ),

    'dns.managedZones': ResourceInfo(
        cache_command='dns managed-zones list',
        list_format="""
          table(
            name,
            dnsName,
            description
          )
        """,
    ),

    'dns.resourceRecordSets': ResourceInfo(
        list_format="""
          table(
                name,
                type,
                ttl,
                rrdatas.list():label=DATA
              )
        """,
    ),

    # genomics

    'genomics.datasets': ResourceInfo(
        list_format="""
          table(
            id,
            name
          )
        """,
    ),

    # logging

    'logging.logs': ResourceInfo(
        list_format="""
          table(
            name
          )
        """,
    ),

    'logging.sinks': ResourceInfo(
        list_format="""
          table(
            name,
            destination
          )
        """,
    ),

    'logging.metrics': ResourceInfo(
        list_format="""
          table(
            name,
            description,
            filter
          )
        """,
    ),

    'logging.typedSinks': ResourceInfo(
        list_format="""
          table(
            name,
            destination,
            type
          )
        """,
    ),

    # projects

    'developerprojects.projects': ResourceInfo(
        list_format="""
          table(
            projectId,
            title,
            projectNumber
          )
        """,
    ),

    # pubsub

    'pubsub.subscriptions': ResourceInfo(
        list_format="""
          table[box](
            projectId:label=PROJECT,
            subscriptionId:label=SUBSCRIPTION,
            topicId:label=TOPIC,
            type,
            ackDeadlineSeconds:label=ACK_DEADLINE
          )
        """,
    ),

    # service management (inception)

    'servicemanagement-v1.services': ResourceInfo(
        list_format="""
          table(
            serviceName:label=NAME,
            serviceConfig.title
          )
        """,
        simple_format="""
          value(
            serviceName
          )
        """,
    ),

    # service registry

    'service_registry.endpoints': ResourceInfo(
        async_collection='service_registry.operations',
        list_format="""
          table[empty-legend="No endpoints were found in your project"](
            name,
            description,
            state,
            addresses[].address:label=ADDRESSES
          )
        """,
        simple_format="""
          [legend-log=status,
           empty-legend="No endpoints were found in your project"],
           value(
            name
          )
        """,
    ),

    'service_registry.operations': ResourceInfo(
        list_format="""
          table[empty-legend="No operations were found in your project"](
            name,
            operationType:label=TYPE,
            status,
            targetLink.basename():label=TARGET,
            insertTime.date(format="%Y-%m-%d"):label=DATE,
            error.errors.group(code, message)
          )
        """,
        simple_format="""
          [legend-log=status,
           empty-legend="No operations were found in your project"]
          value(
            name
          )
        """,
    ),

    # source

    'source.jobs.list': ResourceInfo(
        list_format="""
          table(
            name.YesNo(no="default"):label=REPO_NAME,
            projectId,
            vcs,
            state,
            createTime
          )
        """,
    ),

    # sql

    'sql.backupRuns': ResourceInfo(
        list_format="""
          table(
            dueTime.iso(),
            error.code.yesno(no="-"):label=ERROR,
            status
          )
        """,
    ),

    'sql.backupRuns.v1beta4': ResourceInfo(
        list_format="""
          table(
            id,
            windowStartTime.iso(),
            error.code.yesno(no="-"):label=ERROR,
            status
          )
        """,
    ),

    'sql.flags': ResourceInfo(
        list_format="""
          table(
            name,
            type,
            allowedStringValues.list():label=ALLOWED_VALUES
          )
        """,
    ),

    'sql.instances': ResourceInfo(
        async_collection='sql.operations',
        cache_command='sql instances list',
        list_format="""
          table(
            instance:label=NAME,
            region,
            settings.tier,
            ipAddresses[0].ipAddress.yesno(no="-"):label=ADDRESS,
            state:label=STATUS
          )
        """,
    ),

    'sql.instances.v1beta4': ResourceInfo(
        async_collection='sql.operations.v1beta4',
        cache_command='sql instances list',
        list_format="""
          table(
            name,
            region,
            settings.tier,
            ipAddresses[0].ipAddress.yesno(no="-"):label=ADDRESS,
            state:label=STATUS
          )
        """,
    ),

    'sql.operations': ResourceInfo(
        list_format="""
          table(
            operation,
            operationType:label=TYPE,
            startTime.iso():label=START,
            endTime.iso():label=END,
            error[0].code.yesno(no="-"):label=ERROR,
            state:label=STATUS
          )
        """,
    ),

    'sql.operations.v1beta4': ResourceInfo(
        list_format="""
          table(
            name,
            operationType:label=TYPE,
            startTime.iso():label=START,
            endTime.iso():label=END,
            error[0].code.yesno(no="-"):label=ERROR,
            state:label=STATUS
          )
        """,
    ),

    'sql.sslCerts': ResourceInfo(
        async_collection='sql.operations',
        list_format="""
          table(
            commonName:label=NAME,
            sha1Fingerprint,
            expirationTime.yesno(no="-"):label=EXPIRATION
          )
        """,
    ),

    'sql.tiers': ResourceInfo(
        list_format="""
          table(
            tier,
            region.list():label=AVAILABLE_REGIONS,
            RAM.size(),
            DiskQuota.size():label=DISK
          )
        """,
    ),

    # test

    'test.android.devices': ResourceInfo(
        list_format="""
          table[box](
            id:label=DEVICE_ID,
            manufacturer:label=MAKE,
            name:label=MODEL_NAME,
            form.color(blue=VIRTUAL,yellow=PHYSICAL),
            format("{0:4} x {1}", screenY, screenX):label=RESOLUTION,
            supportedVersionIds.list("none"):label=OS_VERSION_IDS,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,
    ),

    'test.android.versions': ResourceInfo(
        list_format="""
          table[box](
            id:label=OS_VERSION_ID:align=center,
            versionString:label=VERSION:align=center,
            codeName,
            apiLevel:align=center,
            releaseDate.date(format='%Y-%m-%d'):align=center,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,
    ),

    'test.android.locales': ResourceInfo(
        list_format="""
          table[box](
            id:label=LOCALE,
            name,
            region,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,
    ),

    'test.android.run.outcomes': ResourceInfo(
        async_collection='test.android.run.url',
        list_format="""
          table[box](
            outcome.color(red=Fail, green=Pass, yellow=Inconclusive),
            axis_value:label=TEST_AXIS_VALUE,
            test_details:label=TEST_DETAILS
          )
        """,
    ),

    'test.android.run.url': ResourceInfo(
        list_format="""
          value(format(
            'Final test results will be available at [{0}].', [])
          )
        """,
    ),

    'test.web.browsers': ResourceInfo(
        list_format="""
          table[box](
            id:label=BROWSER_ID,
            name,
            release,
            versionString:label=VERSION,
            androidCatalog.yesno("*", "-"),
            linuxCatalog.yesno("*", "-"),
            windowsCatalog.yesno("*", "-")
          )
        """,
    ),

    # updater

    'replicapoolupdater.rollingUpdates': ResourceInfo(
        list_format="""
          table(
            id,
            instanceGroupManager.basename():label=GROUP_NAME,
            instanceTemplate.basename("-"):label=TEMPLATE_NAME,
            status,
            statusMessage
          )
        """,
    ),

    'replicapoolupdater.rollingUpdates.instanceUpdates': ResourceInfo(
        list_format="""
          table(
            instance.basename():label=INSTANCE_NAME,
            status
          )
        """,
    ),

    # generic

    'uri': ResourceInfo(
        list_format="""
          table(
            uri():sort=101:label=""
          )
        """,
    ),

}


def Get(collection, must_be_registered=True):
  """Returns the ResourceInfo for collection or None if not registered.

  Args:
    collection: The resource collection.
    must_be_registered: Raises exception if True, otherwise returns None.

  Raises:
    UnregisteredCollectionError: If collection is not registered and
      must_be_registered is True.

  Returns:
    The ResourceInfo for collection or None if not registered.
  """
  info = RESOURCE_REGISTRY.get(collection, None)
  if not info:
    if not must_be_registered:
      return None
    raise resource_exceptions.UnregisteredCollectionError(
        'Collection [{0}] is not registered.'.format(collection))
  info.collection = collection
  return info
