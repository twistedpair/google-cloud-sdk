# -*- coding: utf-8 -*- #
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

"""Utilities for building the dataproc clusters CLI."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.api_lib.compute import utils as api_utils
from googlecloudsdk.api_lib.dataproc import compute_helpers
from googlecloudsdk.api_lib.dataproc import constants
from googlecloudsdk.api_lib.dataproc import exceptions
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.compute.instances import flags as instances_flags
from googlecloudsdk.command_lib.dataproc import flags
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


def ArgsForClusterRef(parser, beta=False):
  """Register flags for creating a dataproc cluster.

  Args:
    parser: The argparse.ArgParser to configure with dataproc cluster arguments.
    beta: whether or not this is a beta command (may affect flag visibility)
  """
  labels_util.AddCreateLabelsFlags(parser)
  instances_flags.AddTagsArgs(parser)
  # 30m is backend timeout + 5m for safety buffer.
  flags.AddTimeoutFlag(parser, default='35m')
  flags.AddZoneFlag(parser)

  parser.add_argument(
      '--metadata',
      type=arg_parsers.ArgDict(min_length=1),
      action='append',
      default=None,
      help=('Metadata to be made available to the guest operating system '
            'running on the instances'),
      metavar='KEY=VALUE')

  # Either allow creating a single node cluster (--single-node), or specifying
  # the number of workers in the multi-node cluster (--num-workers and
  # --num-preemptible-workers)
  node_group = parser.add_argument_group(mutex=True)  # Mutually exclusive
  node_group.add_argument(
      '--single-node',
      action='store_true',
      help="""\
      Create a single node cluster.

      A single node cluster has all master and worker components.
      It cannot have any separate worker nodes. If this flag is not
      specified, a cluster with separate workers is created.
      """)
  # Not mutually exclusive
  worker_group = node_group.add_argument_group(help='Multi-node cluster flags')
  worker_group.add_argument(
      '--num-workers',
      type=int,
      help='The number of worker nodes in the cluster. Defaults to '
      'server-specified.')
  worker_group.add_argument(
      '--num-preemptible-workers',
      type=int,
      help='The number of preemptible worker nodes in the cluster.')

  parser.add_argument(
      '--master-machine-type',
      help='The type of machine to use for the master. Defaults to '
      'server-specified.')
  parser.add_argument(
      '--worker-machine-type',
      help='The type of machine to use for workers. Defaults to '
      'server-specified.')
  image_parser = parser.add_mutually_exclusive_group()
  # TODO(b/73291743): Add external doc link to --image
  image_parser.add_argument(
      '--image',
      metavar='IMAGE',
      help='The full custom image URI or the custom image name that '
      'will be used to create a cluster.')
  image_parser.add_argument(
      '--image-version',
      metavar='VERSION',
      help='The image version to use for the cluster. Defaults to the '
      'latest version.')
  parser.add_argument(
      '--bucket',
      help='The Google Cloud Storage bucket to use with the Google Cloud '
      'Storage connector. A bucket is auto created when this parameter is '
      'not specified.')

  netparser = parser.add_mutually_exclusive_group()
  netparser.add_argument(
      '--network',
      help="""\
      The Compute Engine network that the VM instances of the cluster will be
      part of. This is mutually exclusive with --subnet. If neither is
      specified, this defaults to the "default" network.
      """)
  netparser.add_argument(
      '--subnet',
      help="""\
      Specifies the subnet that the cluster will be part of. This is mutally
      exclusive with --network.
      """)
  parser.add_argument(
      '--num-worker-local-ssds',
      type=int,
      help='The number of local SSDs to attach to each worker in a cluster.')
  parser.add_argument(
      '--num-master-local-ssds',
      type=int,
      help='The number of local SSDs to attach to the master in a cluster.')
  parser.add_argument(
      '--initialization-actions',
      type=arg_parsers.ArgList(min_length=1),
      metavar='CLOUD_STORAGE_URI',
      help=('A list of Google Cloud Storage URIs of '
            'executables to run on each node in the cluster.'))
  parser.add_argument(
      '--initialization-action-timeout',
      type=arg_parsers.Duration(),
      metavar='TIMEOUT',
      default='10m',
      help=('The maximum duration of each initialization action. See '
            '$ gcloud topic datetimes for information on duration formats.'))
  parser.add_argument(
      '--num-masters',
      type=arg_parsers.CustomFunctionValidator(
          lambda n: int(n) in [1, 3],
          'Number of masters must be 1 (Standard) or 3 (High Availability)',
          parser=arg_parsers.BoundedInt(1, 3)),
      help="""\
      The number of master nodes in the cluster.

      [format="csv",options="header"]
      |========
      Number of Masters,Cluster Mode
      1,Standard
      3,High Availability
      |========
      """)
  parser.add_argument(
      '--properties',
      type=arg_parsers.ArgDict(),
      metavar='PREFIX:PROPERTY=VALUE',
      default={},
      help="""\
Specifies configuration properties for installed packages, such as Hadoop
and Spark.

Properties are mapped to configuration files by specifying a prefix, such as
"core:io.serializations". The following are supported prefixes and their
mappings:

[format="csv",options="header"]
|========
Prefix,File,Purpose of file
capacity-scheduler,capacity-scheduler.xml,Hadoop YARN Capacity Scheduler configuration
core,core-site.xml,Hadoop general configuration
distcp,distcp-default.xml,Hadoop Distributed Copy configuration
hadoop-env,hadoop-env.sh,Hadoop specific environment variables
hdfs,hdfs-site.xml,Hadoop HDFS configuration
hive,hive-site.xml,Hive configuration
mapred,mapred-site.xml,Hadoop MapReduce configuration
mapred-env,mapred-env.sh,Hadoop MapReduce specific environment variables
pig,pig.properties,Pig configuration
spark,spark-defaults.conf,Spark configuration
spark-env,spark-env.sh,Spark specific environment variables
yarn,yarn-site.xml,Hadoop YARN configuration
yarn-env,yarn-env.sh,Hadoop YARN specific environment variables
|========

See https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties
for more information.

""")
  parser.add_argument(
      '--service-account',
      help='The Google Cloud IAM service account to be authenticated as.')
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      metavar='SCOPE',
      help="""\
Specifies scopes for the node instances. Multiple SCOPEs can be specified,
separated by commas.
Examples:

  $ {{command}} example-cluster --scopes https://www.googleapis.com/auth/bigtable.admin

  $ {{command}} example-cluster --scopes sqlservice,bigquery

The following *minimum scopes* are necessary for the cluster to function
properly and are always added, even if not explicitly specified:

[format="csv"]
|========
{minimum_scopes}
|========

If the `--scopes` flag is not specified, the following *default scopes*
are also included:

[format="csv"]
|========
{additional_scopes}
|========

If you want to enable all scopes use the 'cloud-platform' scope.

SCOPE can be either the full URI of the scope or an alias.
Available aliases are:

[format="csv",options="header"]
|========
Alias,URI
{aliases}
|========

{scope_deprecation_msg}
""".format(
    minimum_scopes='\n'.join(constants.MINIMUM_SCOPE_URIS),
    additional_scopes='\n'.join(constants.ADDITIONAL_DEFAULT_SCOPE_URIS),
    aliases=compute_helpers.SCOPE_ALIASES_FOR_HELP,
    scope_deprecation_msg=compute_constants.DEPRECATED_SCOPES_MESSAGES))

  master_boot_disk_size = parser.add_mutually_exclusive_group()
  worker_boot_disk_size = parser.add_mutually_exclusive_group()

  # Deprecated, to be removed at a future date.
  master_boot_disk_size.add_argument(
      '--master-boot-disk-size-gb',
      action=actions.DeprecationAction(
          '--master-boot-disk-size-gb',
          warn=('The `--master-boot-disk-size-gb` flag is deprecated. '
                'Use `--master-boot-disk-size` flag with "GB" after value.')),
      type=int,
      hidden=True,
      help='Use `--master-boot-disk-size` flag with "GB" after value.')
  worker_boot_disk_size.add_argument(
      '--worker-boot-disk-size-gb',
      action=actions.DeprecationAction(
          '--worker-boot-disk-size-gb',
          warn=('The `--worker-boot-disk-size-gb` flag is deprecated. '
                'Use `--worker-boot-disk-size` flag with "GB" after value.')),
      type=int,
      hidden=True,
      help='Use `--worker-boot-disk-size` flag with "GB" after value.')

  boot_disk_size_detailed_help = """\
      The size of the boot disk. The value must be a
      whole number followed by a size unit of ``KB'' for kilobyte, ``MB''
      for megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For example,
      ``10GB'' will produce a 10 gigabyte disk. The minimum size a boot disk
      can have is 10 GB. Disk size must be a multiple of 1 GB.
      """
  master_boot_disk_size.add_argument(
      '--master-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help=boot_disk_size_detailed_help)
  worker_boot_disk_size.add_argument(
      '--worker-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help=boot_disk_size_detailed_help)
  parser.add_argument(
      '--preemptible-worker-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help=boot_disk_size_detailed_help)

  # Args that are visible only in Beta track
  parser.add_argument(
      '--no-address',
      action='store_true',
      help="""\
      If provided, the instances in the cluster will not be assigned external
      IP addresses.

      Note: Dataproc VMs need access to the Dataproc API. This can be achieved
      without external IP addresses using Private Google Access
      (https://cloud.google.com/compute/docs/private-google-access).
      """,
      hidden=not beta)

  boot_disk_type_detailed_help = """\
      The type of the boot disk. The value must be ``pd-standard'' or
      ``pd-ssd''.
      """
  parser.add_argument(
      '--master-boot-disk-type', help=boot_disk_type_detailed_help)
  parser.add_argument(
      '--worker-boot-disk-type', help=boot_disk_type_detailed_help)
  parser.add_argument(
      '--preemptible-worker-boot-disk-type',
      help=boot_disk_type_detailed_help)


def GetClusterConfig(args, dataproc, project_id, compute_resources, beta=False):
  """Get dataproc cluster configuration.

  Args:
    args: Arguments parsed from argparse.ArgParser.
    dataproc: Dataproc object that contains client, messages, and resources
    project_id: Dataproc project ID
    compute_resources: compute resource for cluster
    beta: use BETA only features

  Returns:
    cluster_config: Dataproc cluster configuration
  """
  master_accelerator_type = None
  worker_accelerator_type = None
  master_accelerator_count = None
  worker_accelerator_count = None
  if beta:
    if args.master_accelerator:
      master_accelerator_type = args.master_accelerator['type']
      master_accelerator_count = args.master_accelerator.get('count', 1)
    if args.worker_accelerator:
      worker_accelerator_type = args.worker_accelerator['type']
      worker_accelerator_count = args.worker_accelerator.get('count', 1)

  # Resolve non-zonal GCE resources
  # We will let the server resolve short names of zonal resources because
  # if auto zone is requested, we will not know the zone before sending the
  # request
  image_ref = args.image and compute_resources.Parse(
      args.image, params={'project': project_id}, collection='compute.images')
  network_ref = args.network and compute_resources.Parse(
      args.network,
      params={'project': project_id},
      collection='compute.networks')
  subnetwork_ref = args.subnet and compute_resources.Parse(
      args.subnet,
      params={
          'project': project_id,
          'region': properties.VALUES.compute.region.GetOrFail,
      },
      collection='compute.subnetworks')
  timeout_str = str(args.initialization_action_timeout) + 's'
  init_actions = [
      dataproc.messages.NodeInitializationAction(
          executableFile=exe, executionTimeout=timeout_str)
      for exe in (args.initialization_actions or [])
  ]
  # Increase the client timeout for each initialization action.
  args.timeout += args.initialization_action_timeout * len(init_actions)

  expanded_scopes = compute_helpers.ExpandScopeAliases(args.scopes)

  software_config = dataproc.messages.SoftwareConfig(
      imageVersion=args.image_version)

  master_boot_disk_size_gb = args.master_boot_disk_size_gb
  if args.master_boot_disk_size:
    master_boot_disk_size_gb = (api_utils.BytesToGb(args.master_boot_disk_size))

  worker_boot_disk_size_gb = args.worker_boot_disk_size_gb
  if args.worker_boot_disk_size:
    worker_boot_disk_size_gb = (api_utils.BytesToGb(args.worker_boot_disk_size))

  preemptible_worker_boot_disk_size_gb = (
      api_utils.BytesToGb(args.preemptible_worker_boot_disk_size))

  if args.single_node or args.num_workers == 0:
    # Explicitly specifying --num-workers=0 gives you a single node cluster,
    # but if --num-workers is omitted, args.num_workers is None (not 0), and
    # this property will not be set
    args.properties[constants.ALLOW_ZERO_WORKERS_PROPERTY] = 'true'

  if args.properties:
    software_config.properties = encoding.DictToMessage(
        args.properties, dataproc.messages.SoftwareConfig.PropertiesValue)

  if beta:
    if args.components:
      software_config_cls = dataproc.messages.SoftwareConfig
      software_config.optionalComponents.extend(list(map(
          software_config_cls.OptionalComponentsValueListEntryValuesEnum,
          args.components)))

  gce_cluster_config = dataproc.messages.GceClusterConfig(
      networkUri=network_ref and network_ref.SelfLink(),
      subnetworkUri=subnetwork_ref and subnetwork_ref.SelfLink(),
      internalIpOnly=args.no_address,
      serviceAccount=args.service_account,
      serviceAccountScopes=expanded_scopes,
      zoneUri=properties.VALUES.compute.zone.GetOrFail())

  if args.tags:
    gce_cluster_config.tags = args.tags

  if args.metadata:
    flat_metadata = dict((k, v) for d in args.metadata for k, v in d.items())
    gce_cluster_config.metadata = encoding.DictToMessage(
        flat_metadata, dataproc.messages.GceClusterConfig.MetadataValue)

  master_accelerators = []
  if master_accelerator_type:
    master_accelerators.append(
        dataproc.messages.AcceleratorConfig(
            acceleratorTypeUri=master_accelerator_type,
            acceleratorCount=master_accelerator_count))
  worker_accelerators = []
  if worker_accelerator_type:
    worker_accelerators.append(
        dataproc.messages.AcceleratorConfig(
            acceleratorTypeUri=worker_accelerator_type,
            acceleratorCount=worker_accelerator_count))

  cluster_config = dataproc.messages.ClusterConfig(
      configBucket=args.bucket,
      gceClusterConfig=gce_cluster_config,
      masterConfig=dataproc.messages.InstanceGroupConfig(
          numInstances=args.num_masters,
          imageUri=image_ref and image_ref.SelfLink(),
          machineTypeUri=args.master_machine_type,
          accelerators=master_accelerators,
          diskConfig=GetDiskConfig(
              dataproc,
              args.master_boot_disk_type,
              master_boot_disk_size_gb,
              args.num_master_local_ssds
          )),
      workerConfig=dataproc.messages.InstanceGroupConfig(
          numInstances=args.num_workers,
          imageUri=image_ref and image_ref.SelfLink(),
          machineTypeUri=args.worker_machine_type,
          accelerators=worker_accelerators,
          diskConfig=GetDiskConfig(
              dataproc,
              args.worker_boot_disk_type,
              worker_boot_disk_size_gb,
              args.num_worker_local_ssds,
          )),
      initializationActions=init_actions,
      softwareConfig=software_config,
  )

  if beta:
    cluster_config.masterConfig.minCpuPlatform = args.master_min_cpu_platform
    cluster_config.workerConfig.minCpuPlatform = args.worker_min_cpu_platform

  if beta:
    lifecycle_config = dataproc.messages.LifecycleConfig()
    changed_config = False
    if args.max_age is not None:
      lifecycle_config.autoDeleteTtl = str(args.max_age) + 's'
      changed_config = True
    if args.expiration_time is not None:
      lifecycle_config.autoDeleteTime = times.FormatDateTime(
          args.expiration_time)
      changed_config = True
    if args.max_idle is not None:
      lifecycle_config.idleDeleteTtl = str(args.max_idle) + 's'
      changed_config = True
    if changed_config:
      cluster_config.lifecycleConfig = lifecycle_config

  if beta and hasattr(args.CONCEPTS, 'kms_key'):
    kms_ref = args.CONCEPTS.kms_key.Parse()
    if kms_ref:
      encryption_config = dataproc.messages.EncryptionConfig()
      encryption_config.gcePdKmsKeyName = kms_ref.RelativeName()
      cluster_config.encryptionConfig = encryption_config
    else:
      # Did user use any gce-pd-kms-key flags?
      for keyword in [
          'gce-pd-kms-key', 'gce-pd-kms-key-project', 'gce-pd-kms-key-location',
          'gce-pd-kms-key-keyring'
      ]:
        if getattr(args, keyword.replace('-', '_'), None):
          raise exceptions.ArgumentError(
              '--gce-pd-kms-key was not fully specified.')

  # Secondary worker group is optional. However, users may specify
  # future pVMs configuration at creation time.
  if (args.num_preemptible_workers is not None or
      preemptible_worker_boot_disk_size_gb is not None or
      args.preemptible_worker_boot_disk_type is not None or
      (beta and args.worker_min_cpu_platform is not None)):
    cluster_config.secondaryWorkerConfig = (
        dataproc.messages.InstanceGroupConfig(
            numInstances=args.num_preemptible_workers,
            diskConfig=GetDiskConfig(
                dataproc,
                args.preemptible_worker_boot_disk_type,
                preemptible_worker_boot_disk_size_gb,
                None,
            )))
    if beta and args.worker_min_cpu_platform:
      cluster_config.secondaryWorkerConfig.minCpuPlatform = (
          args.worker_min_cpu_platform)

  return cluster_config


def GetDiskConfig(dataproc,
                  boot_disk_type,
                  boot_disk_size,
                  num_local_ssds):
  """Get dataproc cluster disk configuration.

  Args:
    dataproc: Dataproc object that contains client, messages, and resources
    boot_disk_type: Type of the boot disk
    boot_disk_size: Size of the boot disk
    num_local_ssds: Number of the Local SSDs

  Returns:
    disk_config: Dataproc cluster disk configuration
  """

  return dataproc.messages.DiskConfig(
      bootDiskType=boot_disk_type,
      bootDiskSizeGb=boot_disk_size,
      numLocalSsds=num_local_ssds)


def CreateCluster(dataproc, cluster, is_async, timeout):
  """Create a cluster.

  Args:
    dataproc: Dataproc object that contains client, messages, and resources
    cluster: Cluster to create
    is_async: Whether to wait for the operation to complete
    timeout: Timeout used when waiting for the operation to complete

  Returns:
    Created cluster, or None if async
  """
  # Get project id and region.
  cluster_ref = util.ParseCluster(cluster.clusterName, dataproc)
  request_id = util.GetUniqueId()
  request = dataproc.messages.DataprocProjectsRegionsClustersCreateRequest(
      cluster=cluster,
      projectId=cluster_ref.projectId,
      region=cluster_ref.region,
      requestId=request_id)
  operation = dataproc.client.projects_regions_clusters.Create(request)

  if is_async:
    log.status.write('Creating [{0}] with operation [{1}].'.format(
        cluster_ref, operation.name))
    return

  operation = util.WaitForOperation(
      dataproc,
      operation,
      message='Waiting for cluster creation operation',
      timeout_s=timeout)

  get_request = dataproc.messages.DataprocProjectsRegionsClustersGetRequest(
      projectId=cluster_ref.projectId,
      region=cluster_ref.region,
      clusterName=cluster_ref.clusterName)
  cluster = dataproc.client.projects_regions_clusters.Get(get_request)
  if cluster.status.state == (
      dataproc.messages.ClusterStatus.StateValueValuesEnum.RUNNING):

    zone_uri = cluster.config.gceClusterConfig.zoneUri
    zone_short_name = zone_uri.split('/')[-1]

    # Log the URL of the cluster
    log.CreatedResource(
        cluster_ref,
        # Also indicate which zone the cluster was placed in. This is helpful
        # if the server picked a zone (auto zone)
        details='Cluster placed in zone [{0}]'.format(zone_short_name))
  else:
    log.error('Create cluster failed!')
    if operation.details:
      log.error('Details:\n' + operation.details)
  return cluster
