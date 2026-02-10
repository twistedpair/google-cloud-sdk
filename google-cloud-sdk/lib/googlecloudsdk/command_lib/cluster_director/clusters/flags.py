# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Flag utils for clusters command group."""

import textwrap

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.calliope.exceptions import core_exceptions
from googlecloudsdk.command_lib.cluster_director.clusters import flag_types


class ClusterDirectorError(core_exceptions.Error):
  """Error for Cluster Director commands."""


def AddConfig(parser, api_version=None, required=False, hidden=False):
  """Adds a config flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--config",
      help="Configuration of the cluster specs in the form of a JSON object.",
      type=arg_parsers.ArgObject(
          spec=flag_types.API_VERSION_TO_CLUSTER_FLAG_TYPE[api_version],
          enable_shorthand=True,
      ),
      required=required,
      hidden=hidden,
  )


def AddUpdateMask(parser, api_version=None, required=False, hidden=False):
  """Adds an update mask flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--update-mask",
      help=textwrap.dedent("""
        Update mask to specify the fields to update.

        For e.g. --update-mask "description,labels"
      """),
      type=flag_types.UPDATE_MASK_OBJECT,
      required=required,
      hidden=hidden,
  )


def AddDescription(parser, api_version=None, hidden=False):
  """Adds a description flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--description",
      help=textwrap.dedent("""
        Description of the cluster.

        For e.g. --description {description}
      """),
      type=str,
      hidden=hidden,
  )


def AddLabels(
    parser,
    name="labels",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds a labels flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Cluster labels as key value pairs.

        For e.g. --{name} key1=value1,key2=value2
      """),
      type=flag_types.LABEL,
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove cluster label by key.

          For e.g. --{remove_flag_name} {{key1}},{{key2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddCreateNetwork(parser, api_version=None, hidden=False):
  """Adds a create network flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--create-network",
      help=textwrap.dedent("""
        Parameters to create a network.
        Name: Must match the regex `[a-z]([-a-z0-9]*[a-z0-9])?`, be 1-63
        characters in length, and comply with RFC1035.

        Description: A description of the network. Maximum of 2048 characters.

        For e.g. --create-network name={network},description={description}
      """),
      type=flag_types.NETWORK_OBJECT,
      hidden=hidden,
  )


def AddNetworkSource(parser, api_version=None, required=False, hidden=False):
  """Adds a network flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--network",
      help=textwrap.dedent("""
        Reference of existing network name.
        If the network is in a different project (Shared VPC), specify
        the project ID using --network-project.

        For e.g. --network {network}
      """),
      type=str,
      required=required,
      hidden=hidden,
  )


def AddNetworkProject(parser, api_version=None, hidden=False):
  """Adds a network project flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--network-project",
      help=textwrap.dedent("""\
        Project ID of the project containing the network and subnetwork
        resources, if different from the cluster project (e.g. for Shared VPC).
      """),
      type=str,
      hidden=hidden,
  )


def AddSubnetSource(parser, api_version=None, required=False, hidden=False):
  """Adds a subnet flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--subnet",
      help=textwrap.dedent("""
        Reference of existing subnetwork name.
        If the subnetwork is in a different project (Shared VPC), specify
        the project ID using --network-project.

        For e.g. --subnet regions/{region}/subnetworks/{subnetwork}
      """),
      type=str,
      required=required,
      hidden=hidden,
  )


def AddCreateFilestores(
    parser,
    name="create-filestores",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds a create filestores flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  if include_update_flags:
    name = "add-new-filestore-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent("""
        Parameters to create a filestore instance.

        For e.g. --create-filestores name=locations/{location}/instances/{filestore},tier=REGIONAL,capacityGb={filestoreSize},fileshare={fileshare}

        capacityGb: Size of the filestore in GB. Must be between 1024 and 102400, and must meet scalability requirements described at
        https://cloud.google.com/filestore/docs/service-tiers.

        fileshare: The directory on a Filestore instance where all shared files
        are stored. Must match the regex `[a-z]([-a-z0-9]*[a-z0-9])?`, be 1-63
        characters in length, and comply with RFC1035.
        Supported tier values:
        - ZONAL
        - REGIONAL

        Supported protocol values:
        - NFSV3
        - NFSV41
        - If not specified, defaults to NFSV3

        Defaults:
        - protocol: NFSV3
      """),
      type=flag_types.FILESTORES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddFilestores(
    parser,
    name="filestores",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds a filestores flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = "remove-filestore-instances"
  if include_update_flags:
    name = "add-filestore-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Reference of existing filestore instance.

        For e.g. --{name} locations/{{location}}/instances/{{filestore}}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove filestore instance config by filestore name.

          For e.g. --{remove_flag_name} locations/{{location}}/instances/{{filestore1}},locations/{{location}}/instances/{{filestore2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddCreateGcsBuckets(
    parser: parser_arguments.ArgumentInterceptor,
    name: str = "create-buckets",
    api_version: str = None,
    hidden: bool = False,
    include_update_flags: bool = False,
):
  """Adds a create Google Cloud Storage buckets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  if include_update_flags:
    name = "add-new-storage-buckets"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to create a Google Cloud Storage bucket.

        For e.g. --{name} name={{bucket-path}},storageClass=STANDARD,autoclassTerminalStorageClass=TERMINAL_STORAGE_CLASS_NEARLINE,enableHNS=true

        Supported storageClass values:
        - STANDARD
        - NEARLINE
        - COLDLINE
        - ARCHIVE

        Supported autoclassTerminalStorageClass values:
        - TERMINAL_STORAGE_CLASS_NEARLINE
        - TERMINAL_STORAGE_CLASS_ARCHIVE

        Defaults:
        - storageClass: STANDARD

        Note:
        - Either storageClass or enableAutoclass can be set.
        - HNS: Hierarchical namespace
      """),
      type=flag_types.GCS_BUCKETS_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddGcsBuckets(
    parser: parser_arguments.ArgumentInterceptor,
    name: str = "buckets",
    api_version: str = None,
    hidden: bool = False,
    include_update_flags: bool = False,
):
  """Adds a Google Cloud Storage buckets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-storage-{name}"
  if include_update_flags:
    name = f"add-storage-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Reference of existing Google Cloud Storage bucket.

        For e.g. --{name} {{existing-bucket-name eg. my-bucket}}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove Google Cloud Storage bucket by bucket name.

          For e.g. --{remove_flag_name} {{bucket1}},{{bucket2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddCreateLustres(
    parser: parser_arguments.ArgumentInterceptor,
    name: str = "create-lustres",
    api_version: str = None,
    hidden: bool = False,
    include_update_flags: bool = False,
):
  """Adds a create lustres flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  if include_update_flags:
    name = "add-new-lustre-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to create a Lustre instance.

        For e.g. --{name} name=locations/{{location}}/instances/{{lustre}},capacityGb={{lustreSize}},filesystem={{filesystem}}
      """),
      type=flag_types.LUSTRES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddLustres(
    parser,
    name="lustres",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds a lustres flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = "remove-lustre-instances"
  if include_update_flags:
    name = "add-lustre-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Reference of existing Lustre instance.

        For e.g. --{name} locations/{{location}}/instances/{{lustre}}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove lustre instance config by lustre name.

          For e.g. --{remove_flag_name} locations/{{location}}/instances/{{lustre1}},locations/{{location}}/instances/{{lustre2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddOnDemandInstances(
    parser,
    name="on-demand-instances",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds an on demand instances flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  spec = {
      "id": str,
      "zone": str,
      "machineType": str,
  }
  if api_version == "v1alpha":
    spec["atmTags"] = flag_types.LABEL
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster on demand instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}}
      """),
      type=flag_types.ON_DEMAND_INSTANCES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove on demand instances config by compute id.

          For e.g. --{remove_flag_name} {{computeId1}},{{computeId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddSpotInstances(
    parser,
    name="spot-instances",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds an spot instances flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  spec = {"id": str, "zone": str, "machineType": str, "terminationAction": str}
  if api_version == "v1alpha":
    spec["atmTags"] = flag_types.LABEL
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster spot instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}}
      """),
      type=flag_types.SPOT_INSTANCES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove spot instance config by compute id.

          For e.g. --{remove_flag_name} {{computeId1}},{{computeId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddReservedInstances(
    parser,
    name="reserved-instances",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds an reserved instances flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  spec = {
      "id": str,
      "reservation": str,
      "machineType": str,
  }
  if api_version == "v1alpha":
    spec["atmTags"] = flag_types.LABEL
    spec["reservationBlock"] = str
    spec["reservationSubBlock"] = str
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster reserved instances.

        For e.g. --{name} id={{computeId}},reservation=zones/{{zone}}/reservations/{{reservation}}
      """),
      type=flag_types.RESERVED_INSTANCES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove reserved instance config by compute id.

          For e.g. --{remove_flag_name} {{computeId1}},{{computeId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddFlexStartInstances(
    parser,
    name="flex-start-instances",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds an Flex Start instances flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  spec = {
      "id": str,
      "zone": str,
      "machineType": str,
      "maxDuration": str,
  }
  if api_version == "v1alpha":
    spec["atmTags"] = flag_types.LABEL
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster Flex Start instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}},maxDuration=10000s
      """),
      type=flag_types.FLEX_START_INSTANCES_OBJECT,
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove Flex Start instance config by compute id.

          For e.g. --{remove_flag_name} {{computeId1}},{{computeId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddSlurmNodeSets(
    parser,
    name="slurm-node-sets",
    api_version=None,
    required=False,
    hidden=False,
    include_update_flags=False,
):
  """Adds a slurm node sets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  update_flag_name = f"update-{name}"
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define slurm cluster nodeset config.

        For e.g. --{name} id={{nodesetId}},computeId={{computeId}},staticNodeCount={{staticNodeCount}},maxDynamicNodeCount={{maxDynamicNodeCount}},startupScript="echo hello",labels="{{key1=value1,key2=value2}}"

        To configure a node set backed by GKE, use container-resource-labels or container-startup-script.
        For e.g. --{name} id={{nodesetId}},container-resource-labels="key1=val1",container-startup-script="echo hello"

        Defaults:
        - staticNodeCount: 1

        Note:
        - startupScript:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, only absolute path is supported.
      """),
      type=flag_types.SLURM_NODE_SETS_OBJECT,
      action=arg_parsers.FlattenAction(),
      required=required,
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{update_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to define and update slurm cluster nodeset config.

          For e.g. --{update_flag_name} id={{nodesetId}},staticNodeCount={{staticNodeCount}},maxDynamicNodeCount={{maxDynamicNodeCount}}

          To update a node set backed by GKE, use container-resource-labels or container-startup-script.
          For e.g. --{update_flag_name} id={{nodesetId}},container-resource-labels="key1=val1",container-startup-script="echo hello"
        """),
        type=flag_types.SLURM_NODE_SETS_OBJECT,
        action=arg_parsers.FlattenAction(),
        required=required,
        hidden=hidden,
    )
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove slurm nodeset config by nodeset id.

          For e.g. --{remove_flag_name} {{nodesetId1}},{{nodesetId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        required=required,
        hidden=hidden,
    )


def AddSlurmPartitions(
    parser,
    name="slurm-partitions",
    api_version=None,
    required=False,
    hidden=False,
    include_update_flags=False,
):
  """Adds a slurm partitions flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  update_flag_name = f"update-{name}"
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define slurm cluster partitions.

        For e.g. --{name} id={{partitionId}},nodesetIds=[{{nodesetId1}},{{nodesetId2}}],exclusive=false
      """),
      type=flag_types.SLURM_PARTITIONS_OBJECT,
      action=arg_parsers.FlattenAction(),
      required=required,
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{update_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to define and update slurm cluster partition config.

          For e.g. --{update_flag_name} id={{partitionId}},nodesetIds=[{{nodesetId1}},{{nodesetId2}}],exclusive=false
        """),
        type=flag_types.SLURM_PARTITIONS_UPDATE_OBJECT,
        action=arg_parsers.FlattenAction(),
        required=required,
        hidden=hidden,
    )
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove slurm partition config by partition id.

          For e.g. --{remove_flag_name} {{partitionId1}},{{partitionId2}},...
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        required=required,
        hidden=hidden,
    )


def AddSlurmDefaultPartition(parser, api_version=None, hidden=False):
  """Adds a slurm default partition flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--slurm-default-partition",
      help=textwrap.dedent("""
        Parameters to define slurm cluster default partition.

        For e.g. --slurm-default-partition {partitionId}
      """),
      type=str,
      hidden=hidden,
  )


def AddSlurmLoginNode(
    parser,
    name="slurm-login-node",
    api_version=None,
    required=False,
    hidden=False,
    include_update_flags=False,
):
  """Adds a slurm login node flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  flag_name = name
  if include_update_flags:
    flag_name = f"update-{name}"
    help_text = textwrap.dedent(f"""
      Parameters to update slurm cluster login node.
      Only bootDisk, count and startupScript can be updated.

      For e.g. --{flag_name} count=2,startupScript="echo hello"
    """)
    spec = {
        "count": int,
        "startupScript": arg_parsers.ArgObject(),
        "bootDisk": flag_types.PROTO_BOOT_DISK_TYPE,
    }
    if api_version == "v1alpha":
      spec["serviceAccount"] = flag_types.SERVICE_ACCOUNT_TYPE
  else:
    help_text = textwrap.dedent("""
      Parameters to define slurm cluster login node.

      For e.g. --slurm-login-node machineType={machineType},zone={zone},count={count},enableOSLogin=true,enablePublicIPs=true,startupScript="echo hello",labels="{key1=value1,key2=value2}",bootDisk={type=pd-standard,sizeGb=100}

        If bootDisk is specified, sizeGb must be greater than 50.

      Defaults:
      - count: 1
      - enableOSLogin: true
      - enablePublicIPs: true
      - bootDisk.sizeGb: 100

      Note:
      - startupScript:
        - Either str or file_path
        - For file_path, only bash file format (.sh or .bash) is supported.
        - For file_path, only absolute path is supported.
    """)
    spec = {
        "machineType": str,
        "zone": str,
        "count": int,
        "enableOSLogin": bool,
        "enablePublicIPs": bool,
        "startupScript": arg_parsers.ArgObject(),
        "labels": flag_types.LABEL,
        "bootDisk": flag_types.PROTO_BOOT_DISK_TYPE,
    }
    if api_version == "v1alpha":
      spec["serviceAccount"] = flag_types.SERVICE_ACCOUNT_TYPE
  parser.add_argument(
      f"--{flag_name}",
      help=help_text,
      type=flag_types.SLURM_LOGIN_NODE_UPDATE_OBJECT
      if include_update_flags
      else flag_types.SLURM_LOGIN_NODE_OBJECT,
      required=required,
      hidden=hidden,
  )


def _AddScriptFlags(
    parser, name, help_kind, api_version, hidden, include_update_flags
):
  """Helper to add script flags."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    flag_name = f"add-{name}"
  else:
    flag_name = name
  parser.add_argument(
      f"--{flag_name}",
      help=textwrap.dedent(f"""
        {help_kind}.

        For e.g. --{flag_name} script1.sh,script2.sh
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Scripts to remove from {help_kind}.

          For e.g. --{remove_flag_name} script1.sh,script2.sh
        """),
        type=arg_parsers.ArgList(element_type=str),
        action=arg_parsers.FlattenAction(),
        hidden=hidden,
    )


def AddSlurmPrologBashScripts(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm prolog bash scripts flag for the given API version."""
  _AddScriptFlags(
      parser,
      "slurm-prolog-scripts",
      "Slurm prolog bash scripts",
      api_version,
      hidden,
      include_update_flags,
  )


def AddSlurmEpilogBashScripts(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm epilog bash scripts flag for the given API version."""
  _AddScriptFlags(
      parser,
      "slurm-epilog-scripts",
      "Slurm epilog bash scripts",
      api_version,
      hidden,
      include_update_flags,
  )


def AddSlurmTaskPrologBashScripts(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm task prolog bash scripts flag for the given API version."""
  _AddScriptFlags(
      parser,
      "slurm-task-prolog-scripts",
      "Slurm task prolog bash scripts",
      api_version,
      hidden,
      include_update_flags,
  )


def AddSlurmTaskEpilogBashScripts(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm task epilog bash scripts flag for the given API version."""
  _AddScriptFlags(
      parser,
      "slurm-task-epilog-scripts",
      "Slurm task epilog bash scripts",
      api_version,
      hidden,
      include_update_flags,
  )


def AddSlurmConfig(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm config flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  flag_name = "slurm-config"
  if include_update_flags:
    flag_name = f"update-{flag_name}"
  parser.add_argument(
      f"--{flag_name}",
      help=textwrap.dedent(f"""
        Parameters to define slurm cluster config.

        For e.g. --{flag_name} healthCheckInterval=10,healthCheckNodeState=IDLE,healthCheckProgram=/usr/bin/true
      """),
      type=flag_types.SLURM_CONFIG_TYPE,
      hidden=hidden,
  )


def AddSlurmDisableHealthCheckProgram(
    parser, api_version=None, hidden=False, include_update_flags=False
):
  """Adds a slurm disable health check program flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise ValueError(f"Unsupported API version: {api_version}")
  flag_name = "slurm-disable-health-check-program"
  if include_update_flags:
    flag_name = f"update-{flag_name}"
  parser.add_argument(
      f"--{flag_name}",
      help=textwrap.dedent(f"""
        If true, health checking is disabled, and health_check_interval,
        health_check_node_state, and health_check_program should not be passed in.

        For e.g. --{flag_name}
      """),
      action="store_true",
      hidden=hidden,
  )
