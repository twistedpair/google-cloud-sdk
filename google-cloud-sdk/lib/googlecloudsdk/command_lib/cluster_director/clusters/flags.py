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
from googlecloudsdk.command_lib.cluster_director.clusters import flag_types
from googlecloudsdk.command_lib.cluster_director.clusters import utils


def AddConfig(group, api_version=None, hidden=False):
  """Adds a config flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--config",
      help="Configuration of the cluster specs in the form of a JSON object.",
      type=arg_parsers.ArgObject(
          spec=utils.GetClusterFlagType(api_version=api_version),
          enable_shorthand=True,
      ),
      hidden=hidden,
  )


def AddDescription(group, api_version=None, hidden=False):
  """Adds a description flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--description",
      help=textwrap.dedent("""
        Description of the cluster.

        For e.g. --description {description}
      """),
      type=str,
      hidden=hidden,
  )


def AddLabels(group, api_version=None, hidden=False):
  """Adds a labels flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--labels",
      help=textwrap.dedent("""
        Cluster labels as key value pairs.

        For e.g. --labels key1=value1,key2=value2
      """),
      type=flag_types.LABEL,
      hidden=hidden,
  )


def AddCreateNetwork(group, api_version=None, hidden=False):
  """Adds a create network flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--create-network",
      help=textwrap.dedent("""
        Name of the network to be created.

        For e.g. --create-network {network}
      """),
      type=str,
      hidden=hidden,
  )


def AddNetworkSource(group, api_version=None, hidden=False):
  """Adds a network flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--network",
      help=textwrap.dedent("""
        Reference of existing network name.

        For e.g. --network {network}
      """),
      type=str,
      hidden=hidden,
  )


def AddSubnetSource(group, api_version=None, hidden=False):
  """Adds a subnet flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--subnet",
      help=textwrap.dedent("""
        Reference of existing subnetwork name.

        For e.g. --subnet regions/{region}/subnetworks/{subnetwork}
      """),
      type=str,
      hidden=hidden,
  )


def AddCreateFilestores(group, api_version=None, hidden=False):
  """Adds a create filestores flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  group.add_argument(
      "--create-filestores",
      help=textwrap.dedent("""
        Parameters to create a filestore instance.

        For e.g. --create-filestores name=locations/{location}/instances/{filestore},tier=TIER_BASIC_HDD,sizeGb=100,fileshare=nfsshare

        Supported tier values:
        - TIER_BASIC_HDD
        - TIER_BASIC_SSD
        - TIER_HIGH_SCALE_SSD
        - TIER_ZONAL
        - TIER_ENTERPRISE
        - TIER_REGIONAL

        Supported protocol values:
        - PROTOCOL_NFSV3
        - PROTOCOL_NFSV41
        - If not specified, defaults to PROTOCOL_NFSV3

        Defaults:
        - protocol: PROTOCOL_NFSV3
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "tier": messages.FilestoreInitializeParams.TierValueValuesEnum,
              "sizeGb": int,
              "fileshare": str,
              "protocol": (
                  messages.FilestoreInitializeParams.ProtocolValueValuesEnum
              ),
              "description": str,
          },
          required_keys=["name", "tier", "sizeGb", "fileshare"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddFilestores(group, api_version=None, hidden=False):
  """Adds a filestores flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--filestores",
      help=textwrap.dedent("""
        Reference of existing filestore instance.

        For e.g. --filestores locations/{location}/instances/{filestore}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddCreateGcsBuckets(group, api_version=None, hidden=False):
  """Adds a create Google Cloud Storage buckets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  group.add_argument(
      "--create-gcs-buckets",
      help=textwrap.dedent("""
        Parameters to create a Google Cloud Storage bucket.

        For e.g. --create-gcs-buckets name={bucket-path}

        Supported storageClass values:
        - STORAGE_CLASS_STANDARD
        - STORAGE_CLASS_NEARLINE
        - STORAGE_CLASS_COLDLINE
        - STORAGE_CLASS_ARCHIVE

        Defaults:
        - storageClass: STORAGE_CLASS_STANDARD

        Note:
        - Either storageClass or enableAutoclass can be set.
        - if enableAutoclass is set, enableHNS should not be set.
        - HNS: Hierarchical namespace
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "storageClass": (
                  messages.GcsInitializeParams.StorageClassValueValuesEnum
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


def AddGcsBuckets(group, api_version=None, hidden=False):
  """Adds a Google Cloud Storage buckets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--gcs-buckets",
      help=textwrap.dedent("""
        Reference of existing Google Cloud Storage bucket.

        For e.g. --gcs-buckets {bucket-path}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddCreateLustres(group, api_version=None, hidden=False):
  """Adds a create lustres flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--create-lustres",
      help=textwrap.dedent("""
        Parameters to create a Lustre instance.

        For e.g. --create-lustres name=locations/{location}/instances/{lustre},sizeGb={lustreSize},filesystem={filesystem}
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "filesystem": str,
              "sizeGb": int,
              "description": str,
          },
          required_keys=["name", "sizeGb", "filesystem"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddLustres(group, api_version=None, hidden=False):
  """Adds a lustres flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--lustres",
      help=textwrap.dedent("""
        Reference of existing Lustre instance.

        For e.g. --lustres locations/{location}/instances/{lustre}
      """),
      type=arg_parsers.ArgList(element_type=str),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddComputeResources(group, api_version=None, hidden=False):
  """Adds a compute resources flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  group.add_argument(
      "--compute-resources",
      help=textwrap.dedent("""
        Parameters to define cluster compute resource.

        For e.g. --compute-resources name={computeId},zone={zone},machineType={machineType}

        Supported provisioningModel values:
        - PROVISIONING_MODEL_STANDARD
        - PROVISIONING_MODEL_SPOT
        - PROVISIONING_MODEL_FLEX_START
        - PROVISIONING_MODEL_RESERVATION_BOUND

        Supported terminationAction values:
        - TERMINATION_ACTION_DELETE
        - TERMINATION_ACTION_STOP
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "zone": str,
              "machineType": str,
              "provisioningModel": (
                  messages.ResourceRequest.ProvisioningModelValueValuesEnum
              ),
              "maxRunDuration": int,
              "terminationAction": (
                  messages.ResourceRequest.TerminationActionValueValuesEnum
              ),
              "guestAcceleratorType": str,
              "guestAcceleratorCount": int,
          },
          required_keys=["name", "zone", "machineType"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      required=True,
      hidden=hidden,
  )


def AddComputeResourceDisks(group, api_version=None, hidden=False):
  """Adds a compute resource disks flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--compute-resource-disks",
      help=textwrap.dedent("""
        Parameters to define disk config for compute resource.

        For e.g. --compute-resource-disks computeId={computeId},type={diskType},boot=true,sizeGb={diskSize},sourceImage={family/{image-family} | {image}}

        Note:
        - for boot disk, all fields are required.
        - for non-boot disk, only computeId, type and sizeGb are required.
      """),
      type=arg_parsers.ArgObject(
          spec={
              "computeId": str,
              "type": str,
              "boot": bool,
              "sizeGb": int,
              "sourceImage": str,
          },
          required_keys=["computeId", "type", "sizeGb"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      required=True,
      hidden=hidden,
  )


def AddComputeResourceReservations(group, api_version=None, hidden=False):
  """Adds a compute resource reservations flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  group.add_argument(
      "--compute-resource-reservations",
      help=textwrap.dedent("""
        Parameters to define reservation for compute resource.

        For e.g. --compute-resource-reservations computeId={computeId},type=RESERVATION_TYPE_SPECIFIC_RESERVATION,values=zones/{zone}/reservations/{reservation}

        Supported type values:
        - RESERVATION_TYPE_NO_RESERVATION
        - RESERVATION_TYPE_ANY_RESERVATION
        - RESERVATION_TYPE_SPECIFIC_RESERVATION

        Defaults:
        - key: compute.googleapis.com/reservation-name (if type is RESERVATION_TYPE_SPECIFIC_RESERVATION or RESERVATION_TYPE_ANY_RESERVATION)
      """),
      type=arg_parsers.ArgObject(
          spec={
              "computeId": str,
              "type": messages.ReservationAffinity.TypeValueValuesEnum,
              "key": str,
              "values": arg_parsers.ArgList(element_type=str),
          },
          required_keys=["computeId", "type"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      hidden=hidden,
  )


def AddSlurmNodeSets(group, api_version=None, hidden=False):
  """Adds a slurm node sets flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--slurm-node-sets",
      help=textwrap.dedent("""
        Parameters to define slurm cluster nodeset config.

        For e.g. --slurm-node-sets name={nodesetId},computeId={computeId},staticNodeCount={staticNodeCount},maxDynamicNodeCount={maxDynamicNodeCount},enableOSLogin=true,enableIPForward=false,enablePublicIPs=false,serviceAccountEmail={serviceAccountEmail},serviceAccountScopes=[scope1,scope2],startupScript="echo hello",labels="{key1=value1,key2=value2}"

        Defaults:
        - staticNodeCount: 1
        - enableOSLogin: true

        Note:
        - startupScript:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, absolute or relative path to current work directory is supported.
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "computeId": str,
              "staticNodeCount": int,
              "maxDynamicNodeCount": int,
              "enableOSLogin": bool,
              "enableIPForward": bool,
              "enablePublicIPs": bool,
              "serviceAccountEmail": str,
              "serviceAccountScopes": arg_parsers.ArgObject(
                  value_type=str, repeated=True
              ),
              "startupScript": arg_parsers.ArgObject(),
              "labels": flag_types.LABEL,
          },
          required_keys=["name", "computeId"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      required=True,
      hidden=hidden,
  )


def AddSlurmPartitions(group, api_version=None, hidden=False):
  """Adds a slurm partitions flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--slurm-partitions",
      help=textwrap.dedent("""
        Parameters to define slurm cluster partitions.

        For e.g. --slurm-partitions name={partitionId},nodesetIds=[{nodesetId1},{nodesetId2}],exclusive=false
      """),
      type=arg_parsers.ArgObject(
          spec={
              "name": str,
              "nodesetIds": arg_parsers.ArgObject(
                  value_type=str, repeated=True
              ),
              "exclusive": bool,
          },
          required_keys=["name", "nodesetIds"],
          enable_shorthand=True,
          repeated=True,
      ),
      action=arg_parsers.FlattenAction(),
      required=True,
      hidden=hidden,
  )


def AddSlurmDefaultPartition(group, api_version=None, hidden=False):
  """Adds a slurm default partition flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--slurm-default-partition",
      help=textwrap.dedent("""
        Parameters to define slurm cluster default partition.

        For e.g. --slurm-default-partition {partitionId}
      """),
      type=str,
      hidden=hidden,
  )


def AddSlurmLoginNode(group, api_version=None, hidden=False):
  """Adds a slurm login node flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--slurm-login-node",
      help=textwrap.dedent("""
        Parameters to define slurm cluster login node.

        For e.g. --slurm-login-node machineType={machineType},zone={zone},count={count},enableOSLogin=true,enablePublicIPs=true,serviceAccountEmail={serviceAccountEmail},serviceAccountScopes=[scope1,scope2],startupScript="echo hello",labels="{key1=value1,key2=value2}"

        Defaults:
        - count: 1
        - enableOSLogin: true
        - enablePublicIPs: true

        Note:
        - startupScript:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, absolute or relative path to current work directory is supported.
      """),
      type=arg_parsers.ArgObject(
          spec={
              "machineType": str,
              "zone": str,
              "count": int,
              "enableOSLogin": bool,
              "enablePublicIPs": bool,
              "serviceAccountEmail": str,
              "serviceAccountScopes": arg_parsers.ArgList(element_type=str),
              "startupScript": arg_parsers.ArgObject(),
              "labels": flag_types.LABEL,
          },
          required_keys=["machineType", "zone"],
          enable_shorthand=True,
      ),
      required=True,
      hidden=hidden,
  )


def AddSlurmLoginNodeDisks(group, api_version=None, hidden=False):
  """Adds a slurm login node disks flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  group.add_argument(
      "--slurm-login-node-disks",
      help=textwrap.dedent("""
        Parameters to define disk config for slurm cluster login node.

        For e.g. --slurm-login-node-disks type={diskType},boot=true,sizeGb={diskSize},sourceImage={family/{image-family} | {image}}

        Note:
        - for boot disk, all fields are required.
        - for non-boot disk, only type and sizeGb are required.
      """),
      type=flag_types.DISK,
      action=arg_parsers.FlattenAction(),
      required=True,
      hidden=hidden,
  )


def AddSlurmConfig(group, api_version=None, hidden=False):
  """Adds a slurm config flag for the given API version."""
  if api_version not in ["v1alpha"]:
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  messages = api_utils.GetMessagesModule(api_utils.GetReleaseTrack(api_version))
  group.add_argument(
      "--slurm-config",
      help=textwrap.dedent("""
        Parameters to define slurm cluster config.

        For e.g. --slurm-config requeueExitCodes=[1,2,3],requeueHoldExitCodes=[4,5,6],prologFlags=[ALLOC,CONTAIN,NO_HOLD],prologEpilogTimeout=10000s,jobPrologBashScripts=["echo hello",...],jobEpilogBashScripts=["echo goodbye",...],taskPrologBashScripts=["echo hi",...],taskEpilogBashScripts=["echo bye",...]

        Supported prologFlags values:
        - ALLOC
        - CONTAIN
        - DEFER_BATCH
        - NO_HOLD
        - FORCE_REQUEUE_ON_FAIL
        - RUN_IN_JOB
        - SERIAL
        - X11

        Note:
        - jobPrologBashScripts, jobEpilogBashScripts, taskPrologBashScripts, taskEpilogBashScripts:
          - Either str or file_path
          - For file_path, only bash file format (.sh or .bash) is supported.
          - For file_path, absolute or relative path to current work directory is supported.
      """),
      type=arg_parsers.ArgObject(
          spec={
              "requeueExitCodes": arg_parsers.ArgObject(
                  value_type=int, repeated=True
              ),
              "requeueHoldExitCodes": arg_parsers.ArgObject(
                  value_type=int, repeated=True
              ),
              "prologFlags": arg_parsers.ArgObject(
                  value_type=messages.SlurmConfig.PrologFlagsValueListEntryValuesEnum,
                  repeated=True,
              ),
              "prologEpilogTimeout": str,
              "jobPrologBashScripts": arg_parsers.ArgObject(
                  value_type=str,
                  repeated=True,
              ),
              "jobEpilogBashScripts": arg_parsers.ArgObject(
                  value_type=str,
                  repeated=True,
              ),
              "taskPrologBashScripts": arg_parsers.ArgObject(
                  value_type=str,
                  repeated=True,
              ),
              "taskEpilogBashScripts": arg_parsers.ArgObject(
                  value_type=str,
                  repeated=True,
              ),
          },
          enable_shorthand=True,
      ),
      hidden=hidden,
  )
