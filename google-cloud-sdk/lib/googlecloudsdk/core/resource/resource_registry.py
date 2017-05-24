# Copyright 2017 Google Inc. All Rights Reserved.
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
from googlecloudsdk.core.resource import resource_info

RESOURCE_REGISTRY = {

    # cloud billing
    'cloudbilling.billingAccounts':
        resource_info.ResourceInfo(
            cache_command='billing accounts list',
            # TODO(b/22402915) Delete this when OP resource completion is
            # supported.
            bypass_cache=True,
            list_format="""
          table(
            name.basename():label=ID,
            displayName:label=NAME,
            open
          )
        """,),

    # cloud build
    'cloudbuild.projects.builds':
        resource_info.ResourceInfo(
            cache_command='cloud build list',
            bypass_cache=True,
            async_collection='cloudbuild.projects.builds',
            list_format="""
          table(
            id,
            createTime.date('%Y-%m-%dT%H:%M:%S%Oz', undefined='-'),
            duration(start=startTime,end=finishTime,precision=0,calendar=false,undefined="  -").slice(2:).join(""):label=DURATION,
            build_source(undefined="-"):label=SOURCE,
            build_images(undefined="-"):label=IMAGES,
            status
          )
        """,),

    # cloud key management system
    'cloudkms.projects.locations':
        resource_info.ResourceInfo(
            bypass_cache=True,
            list_command='kms locations list --format=value(location_id)',
            list_format="""
          table(
            locationId
          )
        """,),

    # Cloud SDK client side resources

    # 'coudsdk.*': ...

    # compute
    'compute.addresses':
        resource_info.ResourceInfo(
            cache_command='compute addresses list',
            list_format="""
          table(
            name,
            region.basename(),
            address,
            status
          )
        """,),
    'compute.autoscalers':
        resource_info.ResourceInfo(
            async_collection='compute.operations',
            cache_command='compute autoscaler list',
            list_format="""
          table(
            name,
            target.basename(),
            autoscalingPolicy.policy():label=POLICY
          )
        """,),
    'compute.backendBuckets':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            bucketName:label=GCS_BUCKET_NAME,
            enableCdn
          )
        """,),
    'compute.backendServiceGroupHealth':
        resource_info.ResourceInfo(
            list_format="""
          default
        """,),
    'compute.backendServices':
        resource_info.ResourceInfo(
            cache_command='compute backend-services list',
            list_format="""
          table(
            name,
            backends[].group.list():label=BACKENDS,
            protocol
          )
        """,),
    'compute.backendServices.alpha':
        resource_info.ResourceInfo(
            cache_command='compute backend-services list',
            list_format="""
          table(
            name,
            backends[].group.list():label=BACKENDS,
            protocol,
            loadBalancingScheme,
            healthChecks.map().basename().list()
          )
        """,),
    'compute.regionBackendServices':
        resource_info.ResourceInfo(
            cache_command='compute backend-services list',
            list_format="""
          table(
            name,
            backends[].group.list():label=BACKENDS,
            protocol,
            loadBalancingScheme,
            healthChecks.map().basename().list()
          )
        """,),
    'compute.commitments':
        resource_info.ResourceInfo(
            cache_command='compute commitments list',
            list_format="""
          table(name,
                region.basename(),
                endTimestamp,
                status)
                """,),
    'compute.disks':
        resource_info.ResourceInfo(
            cache_command='compute disks list',
            list_format="""
          table(
            name,
            zone.basename(),
            sizeGb,
            type.basename(),
            status
          )
        """,),
    'compute.diskTypes':
        resource_info.ResourceInfo(
            cache_command='compute disk-types list',
            list_format="""
          table(
            name,
            zone.basename(),
            validDiskSize:label=VALID_DISK_SIZES
          )
        """,),
    'compute.diskTypes.alpha':
        resource_info.ResourceInfo(
            cache_command='compute disk-types list',
            list_format="""
          table(
            name,
            location():label=LOCATION,
            location_scope():label=SCOPE,
            validDiskSize:label=VALID_DISK_SIZES
          )
        """,),
    'compute.firewalls':
        resource_info.ResourceInfo(
            cache_command='compute firewall-rules list',
            list_format="""
          table(
            name,
            network.basename(),
            sourceRanges.list():label=SRC_RANGES,
            allowed[].map().firewall_rule().list():label=RULES,
            sourceTags.list():label=SRC_TAGS,
            targetTags.list():label=TARGET_TAGS
          )
        """,),
    'compute.firewalls.alpha':
        resource_info.ResourceInfo(
            cache_command='compute firewall-rules list',
            list_format="""
          table(
            name,
            network.basename(),
            direction,
            priority,
            allowed[].map().firewall_rule().list():label=ALLOW,
            denied[].map().firewall_rule().list():label=DENY
          )
        """,),
    'compute.forwardingRules':
        resource_info.ResourceInfo(
            cache_command='compute forwarding-rules list',
            list_format="""
          table(
            name,
            region.basename(),
            IPAddress,
            IPProtocol,
            firstof(
                target,
                backendService).scope():label=TARGET
          )
        """,),
    'compute.groups':
        resource_info.ResourceInfo(
            cache_command='compute groups list',
            list_format="""
          table(
            name,
            members.len():label=NUM_MEMBERS,
            description
          )
        """,),
    'compute.healthChecks':
        resource_info.ResourceInfo(
            cache_command='compute health-checks list',
            list_format="""
          table(
            name,
            type:label=PROTOCOL
          )
        """,),
    'compute.hosts':
        resource_info.ResourceInfo(
            cache_command='compute sole-tenancy hosts list',
            list_format="""
          table(
            name,
            zone.basename(),
            instances.len():label=INSTANCES,
            status
          )
        """,),
    'compute.hostTypes':
        resource_info.ResourceInfo(
            cache_command='compute sole-tenancy host-types list',
            list_format="""
          table(
            name,
            zone.basename(),
            guestCpus:label=CPUs,
            memoryMb,
            localSsdGb,
            deprecated.state:label=DEPRECATED
          )
        """,),
    'compute.httpHealthChecks':
        resource_info.ResourceInfo(
            cache_command='compute http-health-checks list',
            list_format="""
          table(
            name,
            host,
            port,
            requestPath
          )
        """,),
    'compute.httpsHealthChecks':
        resource_info.ResourceInfo(
            cache_command='compute https-health-checks list',
            list_format="""
          table(
            name,
            host,
            port,
            requestPath
          )
        """,),
    'compute.images':
        resource_info.ResourceInfo(
            cache_command='compute images list',
            list_format="""
          table(
            name,
            selfLink.map().scope(projects).segment(0):label=PROJECT,
            family,
            deprecated.state:label=DEPRECATED,
            status
          )
        """,),
    'compute.instanceGroups':
        resource_info.ResourceInfo(
            cache_command='compute instance-groups list',
            list_format="""
          table(
            name,
            location():label=LOCATION,
            location_scope():label=SCOPE,
            network.basename(),
            isManaged:label=MANAGED,
            size:label=INSTANCES
          )
        """,),
    'compute.instanceGroupManagers':
        resource_info.ResourceInfo(
            cache_command='compute instance-groups managed list',
            list_format="""
          table(
            name,
            location():label=LOCATION,
            location_scope():label=SCOPE,
            baseInstanceName,
            size,
            targetSize,
            instanceTemplate.basename(),
            autoscaled
          )
        """,),
    'compute.instances':
        resource_info.ResourceInfo(
            async_collection='compute.operations',
            cache_command='compute instances list',
            list_format="""
          table(
            name,
            zone.basename(),
            machineType.machine_type().basename(),
            scheduling.preemptible.yesno(yes=true, no=''),
            networkInterfaces[].networkIP.notnull().list():label=INTERNAL_IP,
            networkInterfaces[].accessConfigs[0].natIP.notnull().list()\
            :label=EXTERNAL_IP,
            status
          )
        """,),
    'compute.instanceTemplates':
        resource_info.ResourceInfo(
            cache_command='compute instance-templates list',
            list_format="""
          table(
            name,
            properties.machineType.machine_type(),
            properties.scheduling.preemptible.yesno(yes=true, no=''),
            creationTimestamp
          )
        """,),
    'compute.invalidations':
        resource_info.ResourceInfo(
            cache_command='beta compute url-maps list-cdn-cache-invalidations',
            list_format="""
          table(
            description,
            operation_http_status():label=HTTP_STATUS,
            status,
            insertTime:label=TIMESTAMP
          )
        """,),
    'compute.machineTypes':
        resource_info.ResourceInfo(
            cache_command='compute machine-types list',
            list_format="""
          table(
            name,
            zone.basename(),
            guestCpus:label=CPUS,
            memoryMb.size(units_in=MiB, units_out=GiB, precision=2):label=MEMORY_GB,
            deprecated.state:label=DEPRECATED
          )
        """,),
    'compute.networks':
        resource_info.ResourceInfo(
            cache_command='compute networks list',
            list_format="""
          table(
            name,
            x_gcloud_mode:label=MODE,
            IPv4Range:label=IPV4_RANGE,
            gatewayIPv4
          )
        """,),
    'compute.operations':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            operationType:label=TYPE,
            targetLink.scope():label=TARGET,
            operation_http_status():label=HTTP_STATUS,
            status,
            insertTime:label=TIMESTAMP
          )
        """,),
    'compute.peerings':
        resource_info.ResourceInfo(
            cache_command='beta compute networks peerings list',
            list_format="""
          table(
            name,
            source_network.basename():label=NETWORK,
            network.map().scope(projects).segment(0):label=PEER_PROJECT,
            network.basename():label=PEER_NETWORK,
            autoCreateRoutes,
            state,
            stateDetails
          )
        """,),
    'compute.projects':
        resource_info.ResourceInfo(
            list_format="""
          value(
            format("There is no API support yet.")
          )
        """,),
    'compute.xpnProjects':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            creationTimestamp,
            xpnProjectStatus
          )
        """,),
    'compute.xpnResourceId':
        resource_info.ResourceInfo(
            list_format="""
          table(
            id:label=RESOURCE_ID,
            type:label=RESOURCE_TYPE)
        """,),
    'compute.regions':
        resource_info.ResourceInfo(
            cache_command='compute regions list',
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
        """,),
    'compute.routers':
        resource_info.ResourceInfo(
            cache_command='compute routers list',
            list_format="""
          table(
            name,
            region.basename(),
            network.basename()
          )
        """,),
    'compute.routes':
        resource_info.ResourceInfo(
            cache_command='compute routes list',
            list_format="""
          table(
            name,
            network.basename(),
            destRange,
            firstof(
                nextHopInstance,
                nextHopGateway,
                nextHopIp,
                nextHopVpnTunnel,
                nextHopPeering).scope()
              :label=NEXT_HOP,
            priority
          )
        """,),
    'compute.snapshots':
        resource_info.ResourceInfo(
            cache_command='compute snapshots list',
            list_format="""
          table(
            name,
            diskSizeGb,
            sourceDisk.scope():label=SRC_DISK,
            status
          )
        """,),
    'compute.sslCertificates':
        resource_info.ResourceInfo(
            cache_command='compute ssl-certificates list',
            list_format="""
          table(
            name,
            creationTimestamp
          )
        """,),
    'compute.subnetworks':
        resource_info.ResourceInfo(
            cache_command='compute networks subnets list',
            list_format="""
          table(
            name,
            region.basename(),
            network.basename(),
            ipCidrRange:label=RANGE
          )
        """,),
    'compute.targetHttpProxies':
        resource_info.ResourceInfo(
            cache_command='compute target-http-proxies list',
            list_format="""
          table(
            name,
            urlMap.basename()
          )
        """,),
    'compute.targetHttpsProxies':
        resource_info.ResourceInfo(
            cache_command='compute target-https-proxies list',
            list_format="""
          table(
            name,
            sslCertificates.map().basename().list():label=SSL_CERTIFICATES,
            urlMap.basename()
          )
        """,),
    'compute.targetInstances':
        resource_info.ResourceInfo(
            cache_command='compute target-instances list',
            list_format="""
          table(
            name,
            zone.basename(),
            instance.basename(),
            natPolicy
          )
        """,),
    'compute.targetPoolInstanceHealth':
        resource_info.ResourceInfo(
            list_format="""
          default
        """,),
    'compute.targetPools':
        resource_info.ResourceInfo(
            cache_command='compute target-pools list',
            list_format="""
          table(
            name,
            region.basename(),
            sessionAffinity,
            backupPool.basename():label=BACKUP,
            healthChecks[].map().basename().list():label=HEALTH_CHECKS
          )
        """,),
    'compute.targetSslProxies':
        resource_info.ResourceInfo(
            cache_command='compute target-ssl-proxies list',),
    'compute.targetTcpProxies':
        resource_info.ResourceInfo(
            cache_command='compute target-tcp-proxies list',),
    'compute.targetVpnGateways':
        resource_info.ResourceInfo(
            cache_command='compute target-vpn-gateways list',
            list_format="""
          table(
            name,
            network.basename(),
            region.basename()
          )
        """,),
    'compute.urlMaps':
        resource_info.ResourceInfo(
            cache_command='compute url-maps list',
            list_format="""
          table(
            name,
            defaultService
          )
        """,),
    'compute.users':
        resource_info.ResourceInfo(
            cache_command='compute users list',
            list_format="""
          table(
            name,
            owner,
            description
          )
        """,),
    'compute.vpnTunnels':
        resource_info.ResourceInfo(
            cache_command='compute vpn-tunnels list',
            list_format="""
          table(
            name,
            region.basename(),
            targetVpnGateway.basename():label=GATEWAY,
            peerIp:label=PEER_ADDRESS
          )
        """,),
    'compute.zones':
        resource_info.ResourceInfo(
            cache_command='compute zones list',
            list_format="""
          table(
            name,
            region.basename(),
            status():label=STATUS,
            maintenanceWindows.next_maintenance():label=NEXT_MAINTENANCE,
            deprecated.deleted:label=TURNDOWN_DATE
          )
        """,),

    # container
    'container.images':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name
          )
        """,),
    'container.tags':
        resource_info.ResourceInfo(
            list_format="""
          table(
            digest.slice(7:19).join(''),
            tags.list(),
            timestamp.date():optional,
            BUILD_DETAILS.buildDetails.provenance.sourceProvenance.sourceContext.context.cloudRepo.revisionId.notnull().list().slice(:8).join(''):optional:label=GIT_SHA,
            PACKAGE_VULNERABILITY.vulnerabilityDetails.severity.notnull().count().list():optional:label=VULNERABILITIES,
            IMAGE_BASIS.derivedImage.sort(distance).map().extract(baseResourceUrl).slice(:1).map().list().list().split('//').slice(1:).list().split('@').slice(:1).list():optional:label=FROM,
            BUILD_DETAILS.buildDetails.provenance.id.notnull().list():optional:label=BUILD
          )
        """,),
    'container.projects.zones.clusters':
        resource_info.ResourceInfo(
            async_collection='container.projects.zones.clusters',
            list_format="""
          table(
            name,
            zone,
            master_version():label=MASTER_VERSION,
            endpoint:label=MASTER_IP,
            nodePools[0].config.machineType,
            currentNodeVersion:label=NODE_VERSION,
            currentNodeCount:label=NUM_NODES,
            status
          )
        """,),
    'container.projects.zones.clusters.nodePools':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            config.machineType,
            config.diskSizeGb,
            version:label=NODE_VERSION
          )
        """,),
    'container.projects.zones.operations':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            operationType:label=TYPE,
            zone,
            targetLink.basename():label=TARGET,
            statusMessage,
            status
          )
        """,),

    # debug
    'debug.logpoints':
        resource_info.ResourceInfo(
            list_format="""
          table(
            userEmail.if(all_users),
            location,
            condition,
            logLevel,
            logMessageFormat,
            id,
            full_status():label=STATUS)
            :(isFinalState:sort=1, createTime:sort=2)
        """,),
    'debug.logpoints.create':
        resource_info.ResourceInfo(
            list_format="""
          list(
            format("id: {0}", id),
            format("location: {0}", location),
            format("logLevel: {0}", logLevel),
            format("logMessageFormat: {0}", logMessageFormat),
            format("condition: {0}", condition),
            format("logViewUrl: {0}", logViewUrl),
            format("status: {0}", full_status())
          )
        """,),
    'debug.snapshots':
        resource_info.ResourceInfo(list_format="""
          table(
            short_status():label=STATUS,
            userEmail.if(all_users),
            location,
            condition,
            finalTime.if(include_inactive != 0):label=COMPLETED_TIME,
            id,
            consoleViewUrl:label=VIEW
          )
        """),
    'debug.snapshots.create':
        resource_info.ResourceInfo(list_format="""
          list(
            format("id: {0}", id),
            format("location: {0}", location),
            format("status: {0}", full_status()),
            format("consoleViewUrl: {0}", consoleViewUrl)
          )
        """),
    'debug.targets':
        resource_info.ResourceInfo(list_format="""
          table(
            name,
            target_id:label=ID,
            description
          )
        """),

    # deployment manager v2
    'deploymentmanager.deployments':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            operation.operationType:label=LAST_OPERATION_TYPE,
            operation.status,
            description,
            manifest.basename(),
            operation.error.errors.group(code)
          )
        """,),
    'deploymentmanager.operations':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            operationType:label=TYPE,
            status,
            targetLink.basename():label=TARGET,
            error.errors.group(code)
          )
        """,),
    'deploymentmanager.resources':
        resource_info.ResourceInfo(
            async_collection='deploymentmanager.operations',
            list_format="""
          table(
            name,
            type,
            update.state.yesno(no="COMPLETED"),
            update.error.errors.group(code),
            update.intent
          )
        """,),
    'deploymentmanager.resources_and_outputs':
        resource_info.ResourceInfo(
            async_collection='deploymentmanager.operations',
            list_format="""
          table(
            resources:format='table(
              name,
              type,
              update.state.yesno(no="COMPLETED"),
              update.error.errors.group(code),
              update.intent)',
            outputs:format='table(
              name:label=OUTPUTS,
              finalValue:label=VALUE)'
          )
        """,),
    'deploymentmanager.deployments_and_resources_and_outputs':
        resource_info.ResourceInfo(
            list_format="""
              table(
                deployment:format='default(name, id, description, fingerprint,
                insertTime, manifest.basename(), labels, operation.operationType,
                operation.name, operation.progress, operation.status,
                operation.user, operation.endTime, operation.startTime,
                operation.error, update)',
                resources:format='table(
                  name:label=NAME,
                  type:label=TYPE,
                  update.state.yesno(no="COMPLETED"),
                  update.intent)',
              outputs:format='table(
                name:label=OUTPUTS,
                finalValue:label=VALUE)'
             )
             """,),
    'deploymentmanager.types':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name
          )
        """,),
    'deploymentmanager.type_providers':
        resource_info.ResourceInfo(
            async_collection='deploymentmanager.operations',
            list_format="""
          table(
            name,
            insertTime.date(format="%Y-%m-%d"):label=INSERT_DATE
          )
        """,),

    # iam
    'iam.service_accounts':
        resource_info.ResourceInfo(
            list_command='iam service-accounts list --format=value(email)',
            bypass_cache=True,
            list_format="""
          table(
            displayName:label=NAME,
            email
          )
        """,),

    # runtime config
    'runtimeconfig.configurations':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            description
          )
        """,),
    'runtimeconfig.variables':
        resource_info.ResourceInfo(
            list_format="""
          table(
            name,
            updateTime.date()
          )
        """,),
    'runtimeconfig.waiters':
        resource_info.ResourceInfo(
            async_collection='runtimeconfig.waiters',
            list_format="""
          table(
            name,
            createTime.date(),
            waiter_status(),
            error.message
          )
        """,),

    # firebase test
    'test.android.devices':
        resource_info.ResourceInfo(  # Deprecated
            list_format="""
          table[box](
            id:label=DEVICE_ID,
            manufacturer:label=MAKE,
            name:label=MODEL_NAME,
            form.color(blue=VIRTUAL,yellow=PHYSICAL):label=FORM,
            format("{0:4} x {1}", screenY, screenX):label=RESOLUTION,
            supportedVersionIds.list(undefined="none"):label=OS_VERSION_IDS,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,),
    'firebase.test.android.models':
        resource_info.ResourceInfo(
            list_format="""
          table[box](
            id:label=MODEL_ID,
            manufacturer:label=MAKE,
            name:label=MODEL_NAME,
            form.color(blue=VIRTUAL,yellow=PHYSICAL):label=FORM,
            format("{0:4} x {1}", screenY, screenX):label=RESOLUTION,
            supportedVersionIds.list(undefined="none"):label=OS_VERSION_IDS,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,),
    'firebase.test.android.versions':
        resource_info.ResourceInfo(
            list_format="""
          table[box](
            id:label=OS_VERSION_ID:align=center,
            versionString:label=VERSION:align=center,
            codeName,
            apiLevel:align=center,
            releaseDate.date(format='%Y-%m-%d'):align=center,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,),
    'firebase.test.android.locales':
        resource_info.ResourceInfo(
            list_format="""
          table[box](
            id:label=LOCALE,
            name,
            region,
            tags.list().color(green=default,red=deprecated,yellow=preview)
          )
        """,),
    'firebase.test.android.run.outcomes':
        resource_info.ResourceInfo(
            async_collection='firebase.test.android.run.url',
            list_format="""
          table[box](
            outcome.color(red=Fail, green=Pass, yellow=Inconclusive),
            axis_value:label=TEST_AXIS_VALUE,
            test_details:label=TEST_DETAILS
          )
        """,),
    'firebase.test.android.run.url':
        resource_info.ResourceInfo(
            list_format="""
          value(format(
            'Final test results will be available at [{0}].', [])
          )
        """,),
    'firebase.test.network-profiles':
        resource_info.ResourceInfo(
            list_format="""
          table[box](
            id:label=PROFILE_ID,
            synthesize((rule:up, upRule),(rule:down, downRule)):
              format="table[box](
                rule,
                delay,
                packetLossRatio:label=LOSS_RATIO,
                packetDuplicationRatio:label=DUPLICATION_RATIO,
                bandwidth,
                burst
              )"
          )
        """,),

    # special IAM roles completion case
    'iam.roles':
        resource_info.ResourceInfo(
            bypass_cache=True,),

    # generic
    'default':
        resource_info.ResourceInfo(
            list_format="""
          default
        """,),
    'uri':
        resource_info.ResourceInfo(
            list_format="""
          table(
            uri():sort=1:label=""
          )
        """,),
}


def Get(collection, must_be_registered=False):
  """Returns the ResourceInfo for collection or None if not registered.

  Args:
    collection: The resource collection.
    must_be_registered: Raises exception if True, otherwise returns None.

  Raises:
    UnregisteredCollectionError: If collection is not registered and
      must_be_registered is True.

  Returns:
    The ResourceInfo for collection or an default ResourceInfo if not
      registered.
  """
  info = RESOURCE_REGISTRY.get(collection, None)
  if not info:
    if not must_be_registered:
      return resource_info.ResourceInfo()
    raise resource_exceptions.UnregisteredCollectionError(
        'Collection [{0}] is not registered.'.format(collection))
  info.collection = collection
  return info
