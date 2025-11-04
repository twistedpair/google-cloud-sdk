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

from googlecloudsdk.api_lib.hypercomputecluster import utils as api_utils
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.command_lib.cluster_director.clusters import flag_types
from googlecloudsdk.command_lib.cluster_director.clusters import utils


def AddConfig(parser, api_version=None, required=False, hidden=False):
  """Adds a config flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--config",
      help="Configuration of the cluster specs in the form of a JSON object.",
      type=arg_parsers.ArgObject(
          spec=utils.GetClusterFlagType(api_version=api_version),
          enable_shorthand=True,
      ),
      required=required,
      hidden=hidden,
  )


def AddUpdateMask(parser, api_version=None, required=False, hidden=False):
  """Adds an update mask flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--update-mask",
      help=textwrap.dedent("""
        Update mask to specify the fields to update.

        For e.g. --update-mask "description,labels"
      """),
      type=arg_parsers.ArgObject(value_type=str, enable_shorthand=True),
      required=required,
      hidden=hidden,
  )


def AddDescription(parser, api_version=None, hidden=False):
  """Adds a description flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--create-network",
      help=textwrap.dedent("""
        Parameters to create a network.

        For e.g. --create-network name={network},description={description}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "description": str,
          },
          required_keys=["name"],
          enable_shorthand=True,
      ),
      hidden=hidden,
  )


def AddNetworkSource(parser, api_version=None, required=False, hidden=False):
  """Adds a network flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--network",
      help=textwrap.dedent("""
        Reference of existing network name.

        For e.g. --network {network}
      """),
      type=str,
      required=required,
      hidden=hidden,
  )


def AddSubnetSource(parser, api_version=None, required=False, hidden=False):
  """Adds a subnet flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  parser.add_argument(
      "--subnet",
      help=textwrap.dedent("""
        Reference of existing subnetwork name.

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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  if include_update_flags:
    name = "add-new-filestore-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent("""
        Parameters to create a filestore instance.

        For e.g. --create-filestores name=locations/{location}/instances/{filestore},tier=REGIONAL,capacityGb={filestoreSize},fileshare={fileshare}

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
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "tier": messages.NewFilestoreConfig.TierValueValuesEnum,
              "capacityGb": int,
              "fileshare": str,
              "protocol": messages.NewFilestoreConfig.ProtocolValueValuesEnum,
              "description": str,
          },
          required_keys=["name", "tier", "capacityGb", "fileshare"],
          enable_shorthand=True,
          repeated=True,
      ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  if include_update_flags:
    name = "add-new-storage-buckets"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to create a Google Cloud Storage bucket.

        For e.g. --{name} name={{bucket-path}}

        Supported storageClass values:
        - STANDARD
        - NEARLINE
        - COLDLINE
        - ARCHIVE

        Defaults:
        - storageClass: STANDARD

        Note:
        - Either storageClass or enableAutoclass can be set.
        - if enableAutoclass is set, enableHNS should not be set.
        - HNS: Hierarchical namespace
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "storageClass": (
                  messages.NewBucketConfig.StorageClassValueValuesEnum
              ),
              "enableAutoclass": bool,
              "enableHNS": bool,
          },
          required_keys=["name"],
          enable_shorthand=True,
          repeated=True,
      ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-storage-{name}"
  if include_update_flags:
    name = f"add-storage-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Reference of existing Google Cloud Storage bucket.

        For e.g. --{name} {{bucket-path}}
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  if include_update_flags:
    name = "add-new-lustre-instances"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to create a Lustre instance.

        For e.g. --{name} name=locations/{{location}}/instances/{{lustre}},capacityGb={{lustreSize}},filesystem={{filesystem}}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "filesystem": str,
              "capacityGb": int,
              "description": str,
          },
          required_keys=["name", "capacityGb", "filesystem"],
          enable_shorthand=True,
          repeated=True,
      ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster on demand instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "zone": str,
              "machineType": str,
          },
          required_keys=["id", "zone", "machineType"],
          enable_shorthand=True,
          repeated=True,
      ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster spot instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "zone": str,
              "machineType": str,
          },
          required_keys=["id", "zone", "machineType"],
          enable_shorthand=True,
          repeated=True,
      ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster reserved instances.

        For e.g. --{name} id={{computeId}},reservation=zones/{{zone}}/reservations/{{reservation}},machineType={{machineType}}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "reservation": str,
              "machineType": str,
          },
          required_keys=["id", "reservation", "machineType"],
          enable_shorthand=True,
          repeated=True,
      ),
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


def AddDwsFlexInstances(
    parser,
    name="dws-flex-instances",
    api_version=None,
    hidden=False,
    include_update_flags=False,
):
  """Adds an DWS Flex instances flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define cluster DWS Flex instances.

        For e.g. --{name} id={{computeId}},zone={{zone}},machineType={{machineType}},maxDuration=10000s
      """),
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "zone": str,
              "machineType": str,
              "maxDuration": str,
          },
          required_keys=["id", "zone", "machineType", "maxDuration"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )
  if include_update_flags:
    parser.add_argument(
        f"--{remove_flag_name}",
        help=textwrap.dedent(f"""
          Parameters to remove DWS Flex instance config by compute id.

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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  update_flag_name = f"update-{name}"
  remove_flag_name = f"remove-{name}"
  if include_update_flags:
    name = f"add-{name}"
  parser.add_argument(
      f"--{name}",
      help=textwrap.dedent(f"""
        Parameters to define slurm cluster nodeset config.

        For e.g. --{name} id={{nodesetId}},computeId={{computeId}},staticNodeCount={{staticNodeCount}},maxDynamicNodeCount={{maxDynamicNodeCount}},startupScript="echo hello",labels="{{key1=value1,key2=value2}}"

        Defaults:
        - staticNodeCount: 1

        Note:
        - startupScript:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, only absolute path is supported.
      """),
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "computeId": str,
              "staticNodeCount": int,
              "maxDynamicNodeCount": int,
              "startupScript": arg_parsers.ArgObject(),
              "labels": flag_types.LABEL,
          },
          required_keys=["id", "computeId"],
          enable_shorthand=True,
          repeated=True,
      ),
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
        """),
        type=arg_parsers.ArgObject(
            spec={
                "id": str,
                "staticNodeCount": int,
                "maxDynamicNodeCount": int,
            },
            required_keys=["id"],
            enable_shorthand=True,
            repeated=True,
        ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
      type=arg_parsers.ArgObject(
          spec={
              "id": str,
              "nodesetIds": arg_parsers.ArgObject(
                  value_type=str, repeated=True
              ),
              "exclusive": bool,
          },
          required_keys=["id", "nodesetIds"],
          enable_shorthand=True,
          repeated=True,
      ),
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
        type=arg_parsers.ArgObject(
            spec={
                "id": str,
                "nodesetIds": arg_parsers.ArgObject(
                    value_type=str, repeated=True
                ),
                "exclusive": bool,
            },
            required_keys=["id"],
            enable_shorthand=True,
            repeated=True,
        ),
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
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
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  flag_name = name
  if include_update_flags:
    flag_name = f"update-{name}"
    help_text = f"""
        Parameters to update slurm cluster login node.
        Only count and startupScript can be updated.

        For e.g. --{flag_name} count=2,startupScript="echo hello"
    """
    spec = {
        "count": int,
        "startupScript": arg_parsers.ArgObject(),
    }
    req_keys = []
  else:
    help_text = """
        Parameters to define slurm cluster login node.

        For e.g. --slurm-login-node machineType={machineType},zone={zone},count={count},enableOSLogin=true,enablePublicIPs=true,startupScript="echo hello",labels="{key1=value1,key2=value2}"

        Defaults:
        - count: 1
        - enableOSLogin: true
        - enablePublicIPs: true

        Note:
        - startupScript:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, only absolute path is supported.
      """
    spec = {
        "machineType": str,
        "zone": str,
        "count": int,
        "enableOSLogin": bool,
        "enablePublicIPs": bool,
        "startupScript": arg_parsers.ArgObject(),
        "labels": flag_types.LABEL,
    }
    req_keys = ["machineType", "zone"]
  parser.add_argument(
      f"--{flag_name}",
      help=textwrap.dedent(help_text),
      type=arg_parsers.ArgObject(
          spec=spec,
          required_keys=req_keys,
          enable_shorthand=True,
      ),
      required=required,
      hidden=hidden,
  )
