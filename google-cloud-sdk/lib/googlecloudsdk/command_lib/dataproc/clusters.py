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

from apitools.base.py import encoding

from googlecloudsdk.api_lib.compute import constants as compute_constants
from googlecloudsdk.api_lib.compute import utils as api_utils
from googlecloudsdk.api_lib.dataproc import compute_helpers
from googlecloudsdk.api_lib.dataproc import constants
from googlecloudsdk.api_lib.dataproc import util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.compute.instances import flags as instances_flags
from googlecloudsdk.command_lib.util import labels_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


def ArgsForClusterRef(parser):
  """Register flags for creating a dataproc cluster.

  Args:
    parser: The argparse.ArgParser to configure with dataproc cluster arguments.
  """
  labels_util.AddCreateLabelsFlags(parser)
  instances_flags.AddTagsArgs(parser)
  # 30m is backend timeout + 5m for safety buffer.
  util.AddTimeoutFlag(parser, default='35m')
  parser.add_argument(
      '--metadata',
      type=arg_parsers.ArgDict(min_length=1),
      action='append',
      default=None,
      help=('Metadata to be made available to the guest operating system '
            'running on the instances'),
      metavar='KEY=VALUE')

  parser.add_argument(
      '--num-workers',
      type=int,
      help='The number of worker nodes in the cluster. Defaults to '
      'server-specified.')
  parser.add_argument(
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
  parser.add_argument('--image', hidden=True)
  parser.add_argument(
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
      help='The maximum duration of each initialization action.')
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
Prefix,Target Configuration File
core,core-site.xml
hdfs,hdfs-site.xml
mapred,mapred-site.xml
yarn,yarn-site.xml
hive,hive-site.xml
pig,pig.properties
spark,spark-defaults.conf
|========

""")
  parser.add_argument(
      '--service-account',
      help='The Google Cloud IAM service account to be authenticated as.')
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      metavar='SCOPE',
      help="""\
Specifies scopes for the node instances. The project's default service account
is used. Multiple SCOPEs can specified, separated by commas.
Examples:

  $ {{command}} example-cluster --scopes https://www.googleapis.com/auth/bigtable.admin

  $ {{command}} example-cluster --scopes sqlservice,bigquery

The following scopes necessary for the cluster to function properly are always
added, even if not explicitly specified:

[format="csv"]
|========
{minimum_scopes}
|========

If this flag is not specified the following default scopes are also included:

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

  master_boot_disk = parser.add_mutually_exclusive_group()
  worker_boot_disk = parser.add_mutually_exclusive_group()

  # Deprecated, to be removed at a future date.
  master_boot_disk.add_argument(
      '--master-boot-disk-size-gb',
      action=actions.DeprecationAction(
          '--master-boot-disk-size-gb',
          warn=('The `--master-boot-disk-size-gb` flag is deprecated. '
                'Use `--master-boot-disk-size` flag with "GB" after value.')),
      type=int,
      hidden=True)
  worker_boot_disk.add_argument(
      '--worker-boot-disk-size-gb',
      action=actions.DeprecationAction(
          '--worker-boot-disk-size-gb',
          warn=('The `--worker-boot-disk-size-gb` flag is deprecated. '
                'Use `--worker-boot-disk-size` flag with "GB" after value.')),
      type=int,
      hidden=True)

  boot_disk_size_detailed_help = """\
      The size of the boot disk. The value must be a
      whole number followed by a size unit of ``KB'' for kilobyte, ``MB''
      for megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For example,
      ``10GB'' will produce a 10 gigabyte disk. The minimum size a boot disk
      can have is 10 GB. Disk size must be a multiple of 1 GB.
      """
  master_boot_disk.add_argument(
      '--master-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help=boot_disk_size_detailed_help)
  worker_boot_disk.add_argument(
      '--worker-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help=boot_disk_size_detailed_help)

  parser.add_argument(
      '--preemptible-worker-boot-disk-size',
      type=arg_parsers.BinarySize(lower_bound='10GB'),
      help="""\
      The size of the boot disk. The value must be a
      whole number followed by a size unit of ``KB'' for kilobyte, ``MB''
      for megabyte, ``GB'' for gigabyte, or ``TB'' for terabyte. For example,
      ``10GB'' will produce a 10 gigabyte disk. The minimum size a boot disk
      can have is 10 GB. Disk size must be a multiple of 1 GB.
      """)


def GetClusterConfig(args, dataproc, project_id, compute_resources,
                     use_accelerators=False, use_auto_delete_ttl=False):
  """Get dataproc cluster configuration.

  Args:
    args: Arguments parsed from argparse.ArgParser.
    dataproc: Dataproc object that contains client, messages, and resources
    project_id: Dataproc project ID
    compute_resources: compute resource for cluster
    use_accelerators: use accelerators in BETA only.
    use_auto_delete_ttl: use to configure auto-delete/TTL in BETA only.

  Returns:
    cluster_config: Dataproc cluster configuration
  """
  master_accelerator_type = None
  worker_accelerator_type = None
  master_accelerator_count = None
  worker_accelerator_count = None
  if use_accelerators:
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
          diskConfig=dataproc.messages.DiskConfig(
              bootDiskSizeGb=master_boot_disk_size_gb,
              numLocalSsds=args.num_master_local_ssds,),),
      workerConfig=dataproc.messages.InstanceGroupConfig(
          numInstances=args.num_workers,
          imageUri=image_ref and image_ref.SelfLink(),
          machineTypeUri=args.worker_machine_type,
          accelerators=worker_accelerators,
          diskConfig=dataproc.messages.DiskConfig(
              bootDiskSizeGb=worker_boot_disk_size_gb,
              numLocalSsds=args.num_worker_local_ssds,),),
      initializationActions=init_actions,
      softwareConfig=software_config,)

  if use_auto_delete_ttl:
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

  # Secondary worker group is optional. However, users may specify
  # future pVM disk size at creation time.
  if (args.num_preemptible_workers is not None or
      preemptible_worker_boot_disk_size_gb is not None):
    cluster_config.secondaryWorkerConfig = (
        dataproc.messages.InstanceGroupConfig(
            numInstances=args.num_preemptible_workers,
            diskConfig=dataproc.messages.DiskConfig(
                bootDiskSizeGb=preemptible_worker_boot_disk_size_gb,)))

  return cluster_config
