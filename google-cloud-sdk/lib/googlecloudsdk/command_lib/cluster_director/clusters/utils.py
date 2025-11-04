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

"""Utility functions for clusters command group."""

from __future__ import annotations

import collections
import os
import re
from typing import Any, Dict, List, Set

from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.cluster_director.clusters import flag_types
from googlecloudsdk.command_lib.util.apis import yaml_data
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs
from googlecloudsdk.core.util import files


def AddClusterNameArgToParser(parser, api_version=None):
  """Adds a cluster name resource argument."""
  cluster_data = yaml_data.ResourceYAMLData.FromPath(
      "cluster_director.clusters.projects_locations_clusters"
  )
  resource_spec = concepts.ResourceSpec.FromYaml(
      cluster_data.GetData(), is_positional=True, api_version=api_version
  )
  presentation_spec = presentation_specs.ResourcePresentationSpec(
      name="cluster",
      concept_spec=resource_spec,
      required=True,
      group_help="""
        Name of the cluster resource.
        Formats: cluster | projects/{project}/locations/{locations}/clusters/{cluster}
      """,
  )
  concept_parsers.ConceptParser([presentation_spec]).AddToParser(parser)


def GetClusterFlagType(api_version=None) -> dict[str, Any]:
  """Returns the cluster spec for the given API version."""
  if (
      not api_version
      or api_version not in flag_types.API_VERSION_TO_CLUSTER_FLAG_TYPE
  ):
    raise exceptions.ToolException(f"Unsupported API version: {api_version}")
  return flag_types.API_VERSION_TO_CLUSTER_FLAG_TYPE[api_version]


class ClusterUtil:
  """Represents a cluster utility class."""

  def __init__(
      self,
      args,
      message_module,
      existing_cluster=None,
      update_mask: Set[str] = None,
  ):
    """Initializes the cluster utility class."""
    self.args = args
    self.message_module = message_module
    self.cluster_ref = self.args.CONCEPTS.cluster.Parse()
    self.existing_cluster = existing_cluster
    self.update_mask: Set[str] = update_mask if update_mask else set()

  def MakeClusterFromConfig(self):
    """Returns a cluster message from the config JSON string."""
    return messages_util.DictToMessageWithErrorCheck(
        self.args.config, self.message_module.Cluster
    )

  def MakeCluster(self):
    """Returns a cluster message from the granular flags."""
    cluster = self.MakeClusterBasic()
    cluster.networkResources = self.MakeClusterNetworks()
    cluster.storageResources = self.MakeClusterStorages()
    cluster.computeResources = self.MakeClusterCompute()
    cluster.orchestrator = self.message_module.Orchestrator(
        slurm=self.MakeClusterSlurmOrchestrator(cluster)
    )
    return cluster

  def MakeClusterBasic(self):
    """Makes a cluster message with basic fields."""
    cluster_ref = self.args.CONCEPTS.cluster.Parse()
    cluster = self.message_module.Cluster(name=cluster_ref.Name())
    if self.args.IsSpecified("description"):
      cluster.description = self.args.description
    if self.args.IsSpecified("labels"):
      cluster.labels = self.MakeLabels(
          self.args.labels, self.message_module.Cluster.LabelsValue
      )
    return cluster

  def MakeClusterNetworks(self):
    """Makes a cluster message with network fields."""
    networks = self.message_module.Cluster.NetworkResourcesValue()
    if self.args.IsSpecified("create_network"):
      network_id = self.args.create_network.get("name")
      network_name = self._GetNetworkName(network_id)
      networks.additionalProperties.append(
          self.message_module.Cluster.NetworkResourcesValue.AdditionalProperty(
              key=f"net-{network_id}",
              value=self.message_module.NetworkResource(
                  config=self.message_module.NetworkResourceConfig(
                      newNetwork=self.message_module.NewNetworkConfig(
                          network=network_name,
                          description=self.args.create_network.get(
                              "description"
                          ),
                      )
                  )
              ),
          )
      )
    if self.args.IsSpecified("network") and self.args.IsSpecified("subnet"):
      network_id = self.args.network
      network_name = self._GetNetworkName(network_id)
      networks.additionalProperties.append(
          self.message_module.Cluster.NetworkResourcesValue.AdditionalProperty(
              key=f"net-{network_id}",
              value=self.message_module.NetworkResource(
                  config=self.message_module.NetworkResourceConfig(
                      existingNetwork=self.message_module.ExistingNetworkConfig(
                          network=network_name,
                          subnetwork=self._GetSubNetworkName(self.args.subnet),
                      )
                  )
              ),
          )
      )
    return networks

  def MakeClusterStorages(self):
    """Makes a cluster message with storage fields."""
    storages = self.message_module.Cluster.StorageResourcesValue()
    # Gives a range of 10 to 99 for storage IDs, required for deterministic
    # sorting.
    storage_counter = 10
    if self.args.IsSpecified("create_filestores"):
      for filestore in self.args.create_filestores:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        newFilestore=self.message_module.NewFilestoreConfig(
                            filestore=self._GetFilestoreName(
                                filestore.get("name")
                            ),
                            tier=filestore.get("tier"),
                            fileShares=[
                                self.message_module.FileShareConfig(
                                    capacityGb=filestore.get("capacityGb"),
                                    fileShare=filestore.get("fileshare"),
                                )
                            ],
                            protocol=filestore.get("protocol"),
                            description=filestore.get("description"),
                        )
                    ),
                ),
            )
        )
    if self.args.IsSpecified("filestores"):
      for filestore in self.args.filestores:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        existingFilestore=self.message_module.ExistingFilestoreConfig(
                            filestore=self._GetFilestoreName(filestore),
                        )
                    ),
                ),
            )
        )
    if self.args.IsSpecified("create_lustres"):
      for lustre in self.args.create_lustres:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        newLustre=self.message_module.NewLustreConfig(
                            lustre=self._GetLustreName(lustre.get("name")),
                            filesystem=lustre.get("filesystem"),
                            capacityGb=lustre.get("capacityGb"),
                            description=lustre.get("description"),
                        )
                    ),
                ),
            )
        )
    if self.args.IsSpecified("lustres"):
      for lustre in self.args.lustres:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        existingLustre=self.message_module.ExistingLustreConfig(
                            lustre=self._GetLustreName(lustre),
                        )
                    ),
                ),
            )
        )
    if self.args.IsSpecified("create_buckets"):
      for gcs_bucket in self.args.create_buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        gcs = self.message_module.NewBucketConfig(
            bucket=gcs_bucket.get("name"),
        )
        if "storageClass" in gcs_bucket:
          gcs.storageClass = gcs_bucket.get("storageClass")
        if not gcs.storageClass and "enableAutoclass" in gcs_bucket:
          gcs.autoclass = self.message_module.GcsAutoclassConfig(
              enabled=gcs_bucket.get("enableAutoclass")
          )
        # If neither storageClass nor autoclass is set, set storageClass to
        # STANDARD by default.
        if not gcs.storageClass and not gcs.autoclass:
          gcs.storageClass = (
              self.message_module.NewBucketConfig.StorageClassValueValuesEnum.STANDARD
          )
        if "enableHNS" in gcs_bucket:
          gcs.hierarchicalNamespace = (
              self.message_module.GcsHierarchicalNamespaceConfig(
                  enabled=gcs_bucket.get("enableHNS"),
              )
          )
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        newBucket=gcs
                    )
                ),
            ),
        )
    if self.args.IsSpecified("buckets"):
      for gcs_bucket in self.args.buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        storages.additionalProperties.append(
            self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
                key=storage_id,
                value=self.message_module.StorageResource(
                    config=self.message_module.StorageResourceConfig(
                        existingBucket=self.message_module.ExistingBucketConfig(
                            bucket=gcs_bucket,
                        )
                    ),
                ),
            )
        )
    return storages

  def MakeClusterCompute(self):
    """Makes a cluster message with compute fields."""
    if (
        not self.args.IsSpecified("on_demand_instances")
        and not self.args.IsSpecified("spot_instances")
        and not self.args.IsSpecified("reserved_instances")
        and not self.args.IsSpecified("dws_flex_instances")
    ):
      raise exceptions.ToolException(
          "At least one of on_demand_instances, spot_instances,"
          " reserved_instances, or dws_flex_instances flag must be specified."
      )
    compute_ids = set()
    compute = self.message_module.Cluster.ComputeResourcesValue()
    if self.args.IsSpecified("on_demand_instances"):
      for instance in self.args.on_demand_instances:
        compute_id = instance.get("id")
        compute_ids.add(compute_id)
        compute.additionalProperties.append(
            self.message_module.Cluster.ComputeResourcesValue.AdditionalProperty(
                key=compute_id,
                value=self._MakeOnDemandComputeResource(instance),
            )
        )
    if self.args.IsSpecified("spot_instances"):
      for instance in self.args.spot_instances:
        compute_id = instance.get("id")
        compute_ids.add(compute_id)
        compute.additionalProperties.append(
            self.message_module.Cluster.ComputeResourcesValue.AdditionalProperty(
                key=compute_id,
                value=self._MakeSpotComputeResource(instance),
            )
        )
    if self.args.IsSpecified("reserved_instances"):
      for instance in self.args.reserved_instances:
        compute_id = instance.get("id")
        compute_ids.add(compute_id)
        compute.additionalProperties.append(
            self.message_module.Cluster.ComputeResourcesValue.AdditionalProperty(
                key=compute_id,
                value=self._MakeReservedComputeResource(instance),
            )
        )
    if self.args.IsSpecified("dws_flex_instances"):
      for instance in self.args.dws_flex_instances:
        compute_id = instance.get("id")
        compute_ids.add(compute_id)
        compute.additionalProperties.append(
            self.message_module.Cluster.ComputeResourcesValue.AdditionalProperty(
                key=compute_id,
                value=self._MakeDwsFlexComputeResource(instance),
            )
        )
    if len(compute_ids) != len(compute.additionalProperties):
      raise exceptions.ToolException(
          "Compute instances with duplicate ids are not supported."
      )
    return compute

  def MakeClusterSlurmOrchestrator(self, cluster):
    """Makes a cluster message with slurm orchestrator fields."""
    slurm = self.message_module.SlurmOrchestrator()
    storage_configs: List[self.message_module.StorageConfig] = (
        self._GetStorageConfigs(cluster)
    )
    if self.args.IsSpecified("slurm_node_sets"):
      for node_set in self.args.slurm_node_sets:
        compute_id = node_set.get("computeId")
        machine_type = self._GetComputeMachineTypeFromArgs(compute_id)
        slurm.nodeSets.append(
            self._MakeSlurmNodeSet(node_set, machine_type, storage_configs)
        )

    if self.args.IsSpecified("slurm_partitions"):
      for partition in self.args.slurm_partitions:
        slurm.partitions.append(self._MakeSlurmPartition(partition))

    if self.args.IsSpecified("slurm_default_partition"):
      slurm.defaultPartition = self.args.slurm_default_partition

    if self.args.IsSpecified("slurm_login_node"):
      login_node = self.args.slurm_login_node
      machine_type = login_node.get("machineType")
      slurm.loginNodes = self.message_module.SlurmLoginNodes(
          count=login_node.get("count", 1),
          machineType=machine_type,
          zone=login_node.get("zone"),
          storageConfigs=storage_configs,
          enableOsLogin=login_node.get("enableOSLogin", True),
          enablePublicIps=login_node.get("enablePublicIps", True),
          startupScript=self._GetBashScript(login_node.get("startupScript")),
          labels=self.MakeLabels(
              label_args=login_node.get("labels"),
              label_cls=self.message_module.SlurmLoginNodes.LabelsValue,
          ),
      )
      slurm.loginNodes.disks.append(self.MakeDisk(machine_type=machine_type))
    return slurm

  def MakeLabels(self, label_args, label_cls):
    """Returns the labels message."""
    if not label_args:
      return None
    return label_cls(
        additionalProperties=[
            label_cls.AdditionalProperty(key=key, value=value)
            for key, value in sorted(label_args.items())
        ]
    )

  def MakeDisk(
      self,
      machine_type: str,
      boot: bool = True,
      source_image: str = "",
  ):
    """Returns the disk message, defaults to boot disk with empty source image."""
    disk_type = "pd-standard"
    if machine_type.startswith(
        ("a3-megagpu", "a3-ultragpu", "a4-highgpu", "a4x-highgpu")
    ):
      disk_type = "hyperdisk-balanced"
    return self.message_module.Disk(
        type=disk_type,
        boot=boot,
        sourceImage=source_image,
    )

  def MakeClusterPatchFromConfig(self):
    """Returns the cluster message from the config."""
    cluster = self.MakeClusterFromConfig()
    return cluster, self.args.update_mask

  def MakeClusterPatch(self):
    """Returns the cluster patch message and update mask."""
    cluster = self.MakeClusterBasicPatch()
    cluster.storageResources = self.MakeClusterStoragesPatch()
    cluster.computeResources = self.MakeClusterComputePatch()
    cluster.orchestrator = self.message_module.Orchestrator(
        slurm=self.MakeClusterSlurmOrchestratorPatch(cluster)
    )
    return cluster, ",".join(sorted(self.update_mask))

  def MakeClusterBasicPatch(self):
    """Makes a cluster patch message with basic fields."""
    cluster = self.message_module.Cluster()
    if self.args.IsSpecified("description"):
      cluster.description = self.args.description
      self.update_mask.add("description")

    labels = self._ConvertMessageToDict(self.existing_cluster.labels)
    is_labels_updated = False
    exception_message = "Label with key={0} not found."
    if self.args.IsSpecified("remove_labels"):
      for key in self.args.remove_labels:
        self._RemoveKeyFromDictSpec(key, labels, exception_message)
        is_labels_updated = True
    if self.args.IsSpecified("add_labels"):
      labels.update(self.args.add_labels)
      is_labels_updated = True
    if is_labels_updated:
      cluster.labels = self.MakeLabels(
          label_args=labels,
          label_cls=self.message_module.Cluster.LabelsValue,
      )
      self.update_mask.add("labels")
    return cluster

  def MakeClusterStoragesPatch(self):
    """Makes a cluster patch message with storage fields."""
    storage_resources = self.message_module.Cluster.StorageResourcesValue()
    storages = self._ConvertMessageToDict(
        self.existing_cluster.storageResources
    )
    is_storage_updated = False

    if self.args.IsSpecified("remove_filestore_instances"):
      filestores_to_remove = {
          self._GetFilestoreName(f)
          for f in self.args.remove_filestore_instances
      }
      storage_ids_to_remove = set()
      found_filestores = set()

      for storage_id, storage_resource in storages.items():
        config = storage_resource.config
        filestore_name = None
        if config and config.newFilestore:
          filestore_name = config.newFilestore.filestore
        elif config and config.existingFilestore:
          filestore_name = config.existingFilestore.filestore

        if filestore_name in filestores_to_remove:
          storage_ids_to_remove.add(storage_id)
          found_filestores.add(filestore_name)

      if found_filestores != filestores_to_remove:
        not_found = filestores_to_remove - found_filestores
        raise exceptions.ToolException(
            f"Filestore(s) not found: {', '.join(not_found)}"
        )

      for storage_id in storage_ids_to_remove:
        storages.pop(storage_id)
      is_storage_updated = True

    if self.args.IsSpecified("remove_storage_buckets"):
      buckets_to_remove = set(self.args.remove_storage_buckets)
      storage_ids_to_remove = set()
      found_buckets = set()

      for storage_id, storage_resource in storages.items():
        config = storage_resource.config
        bucket_name = None
        if config:
          if config.newBucket:
            bucket_name = config.newBucket.bucket
          elif config.existingBucket:
            bucket_name = config.existingBucket.bucket

        if bucket_name in buckets_to_remove:
          storage_ids_to_remove.add(storage_id)
          found_buckets.add(bucket_name)

      if found_buckets != buckets_to_remove:
        not_found = buckets_to_remove - found_buckets
        raise exceptions.ToolException(
            "Cloud Storage bucket(s) not found:"
            f" {', '.join(sorted(list(not_found)))}"
        )

      for storage_id in storage_ids_to_remove:
        storages.pop(storage_id)
      is_storage_updated = True

    if self.args.IsSpecified("remove_lustre_instances"):
      lustres_to_remove = {
          self._GetLustreName(f) for f in self.args.remove_lustre_instances
      }
      storage_ids_to_remove = set()
      found_lustres = set()

      for storage_id, storage_resource in storages.items():
        config = storage_resource.config
        lustre_name = None
        if config and config.newLustre:
          lustre_name = config.newLustre.lustre
        elif config and config.existingLustre:
          lustre_name = config.existingLustre.lustre

        if lustre_name in lustres_to_remove:
          storage_ids_to_remove.add(storage_id)
          found_lustres.add(lustre_name)

      if found_lustres != lustres_to_remove:
        not_found = lustres_to_remove - found_lustres
        raise exceptions.ToolException(
            f"Lustre(s) not found: {', '.join(not_found)}"
        )

      for storage_id in storage_ids_to_remove:
        storages.pop(storage_id)
      is_storage_updated = True

    storage_counter = 10
    if storages:
      storage_ids = [
          int(k[len("storage") :])
          for k in storages.keys()
          if k.startswith("storage") and k[len("storage") :].isdigit()
      ]
      if storage_ids:
        storage_counter = max(storage_ids) + 1

    if self.args.IsSpecified("add_new_filestore_instances"):
      for filestore in self.args.add_new_filestore_instances:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        filestore_name = self._GetFilestoreName(filestore.get("name"))
        for storage_resource in storages.values():
          config = storage_resource.config
          if config and (
              (
                  config.newFilestore
                  and config.newFilestore.filestore == filestore_name
              )
              or (
                  config.existingFilestore
                  and config.existingFilestore.filestore == filestore_name
              )
          ):
            raise exceptions.ToolException(
                f"Filestore {filestore_name} already exists."
            )

        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(
                newFilestore=self.message_module.NewFilestoreConfig(
                    filestore=filestore_name,
                    tier=filestore.get("tier"),
                    fileShares=[
                        self.message_module.FileShareConfig(
                            capacityGb=filestore.get("capacityGb"),
                            fileShare=filestore.get("fileshare"),
                        )
                    ],
                    protocol=filestore.get("protocol"),
                    description=filestore.get("description"),
                )
            )
        )
      is_storage_updated = True

    if self.args.IsSpecified("add_filestore_instances"):
      for filestore in self.args.add_filestore_instances:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        filestore_name = self._GetFilestoreName(filestore)
        for storage_resource in storages.values():
          config = storage_resource.config
          if config and (
              (
                  config.newFilestore
                  and config.newFilestore.filestore == filestore_name
              )
              or (
                  config.existingFilestore
                  and config.existingFilestore.filestore == filestore_name
              )
          ):
            raise exceptions.ToolException(
                f"Filestore {filestore_name} already exists."
            )

        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(
                existingFilestore=self.message_module.ExistingFilestoreConfig(
                    filestore=filestore_name,
                )
            )
        )
      is_storage_updated = True

    if self.args.IsSpecified("add_new_lustre_instances"):
      for lustre in self.args.add_new_lustre_instances:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        lustre_name = self._GetLustreName(lustre.get("name"))
        for storage_resource in storages.values():
          config = storage_resource.config
          if config and (
              (config.newLustre and config.newLustre.lustre == lustre_name)
              or (
                  config.existingLustre
                  and config.existingLustre.lustre == lustre_name
              )
          ):
            raise exceptions.ToolException(
                f"Lustre {lustre_name} already exists."
            )

        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(
                newLustre=self.message_module.NewLustreConfig(
                    lustre=self._GetLustreName(lustre.get("name")),
                    filesystem=lustre.get("filesystem"),
                    capacityGb=lustre.get("capacityGb"),
                    description=lustre.get("description"),
                )
            )
        )
      is_storage_updated = True

    if self.args.IsSpecified("add_lustre_instances"):
      for lustre in self.args.add_lustre_instances:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        lustre_name = self._GetLustreName(lustre)
        for storage_resource in storages.values():
          config = storage_resource.config
          if config and (
              (config.newLustre and config.newLustre.lustre == lustre_name)
              or (
                  config.existingLustre
                  and config.existingLustre.lustre == lustre_name
              )
          ):
            raise exceptions.ToolException(
                f"Lustre {lustre_name} already exists."
            )

        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(
                existingLustre=self.message_module.ExistingLustreConfig(
                    lustre=lustre_name,
                )
            )
        )
      is_storage_updated = True

    if self.args.IsSpecified("add_storage_buckets"):
      for bucket in self.args.add_storage_buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        # Check for duplicates
        for storage_resource in storages.values():
          config = storage_resource.config
          bucket_name_in_config = None
          if config:
            if config.newBucket:
              bucket_name_in_config = config.newBucket.bucket
            elif config.existingBucket:
              bucket_name_in_config = config.existingBucket.bucket

          if bucket_name_in_config == bucket:
            raise exceptions.ToolException(
                f"Cloud Storage bucket {bucket} already exists."
            )

        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(
                existingBucket=self.message_module.ExistingBucketConfig(
                    bucket=bucket,
                )
            )
        )
      is_storage_updated = True

    if self.args.IsSpecified("add_new_storage_buckets"):
      for gcs_bucket in self.args.add_new_storage_buckets:
        storage_id = self._GetNextStorageId(storage_counter)
        storage_counter += 1
        bucket_name = gcs_bucket.get("name")
        for storage_resource in storages.values():
          config = storage_resource.config
          b_name = None
          if config:
            if config.newBucket:
              b_name = config.newBucket.bucket
            elif config.existingBucket:
              b_name = config.existingBucket.bucket
          if b_name == bucket_name:
            raise exceptions.ToolException(
                f"Cloud Storage bucket {bucket_name} already exists."
            )
        gcs = self.message_module.NewBucketConfig(
            bucket=gcs_bucket.get("name"),
        )
        if "storageClass" in gcs_bucket:
          gcs.storageClass = gcs_bucket.get("storageClass")
        if not gcs.storageClass and "enableAutoclass" in gcs_bucket:
          gcs.autoclass = self.message_module.GcsAutoclassConfig(
              enabled=gcs_bucket.get("enableAutoclass")
          )
        if not gcs.storageClass and not gcs.autoclass:
          gcs.storageClass = (
              self.message_module.NewBucketConfig.StorageClassValueValuesEnum.STANDARD
          )
        if "enableHNS" in gcs_bucket:
          gcs.hierarchicalNamespace = (
              self.message_module.GcsHierarchicalNamespaceConfig(
                  enabled=gcs_bucket.get("enableHNS"),
              )
          )
        storages[storage_id] = self.message_module.StorageResource(
            config=self.message_module.StorageResourceConfig(newBucket=gcs)
        )
      is_storage_updated = True

    if is_storage_updated:
      storage_resources.additionalProperties = [
          self.message_module.Cluster.StorageResourcesValue.AdditionalProperty(
              key=key, value=value
          )
          for key, value in storages.items()
      ]
      self.update_mask.add("storage_resources")
    return storage_resources

  def MakeClusterComputePatch(self):
    """Makes a cluster compute patch message with compute fields."""
    compute_resources = self.message_module.Cluster.ComputeResourcesValue()
    compute = self._ConvertMessageToDict(self.existing_cluster.computeResources)
    is_compute_updated = False
    ex_msg_not_found = "Compute instances with id={0} not found."
    ex_msg_already_exist = "Compute instances with id={0} already exist."
    if self.args.IsSpecified("remove_on_demand_instances"):
      for compute_id in self.args.remove_on_demand_instances:
        self._RemoveKeyByAttrFromDictSpec(
            key=compute_id,
            dict_spec=compute,
            attrs=["newOnDemandInstances"],
            key_exception_message=ex_msg_not_found,
            attr_exception_message=f"On demand {ex_msg_not_found}",
        )
        is_compute_updated = True
    if self.args.IsSpecified("remove_spot_instances"):
      for compute_id in self.args.remove_spot_instances:
        self._RemoveKeyByAttrFromDictSpec(
            key=compute_id,
            dict_spec=compute,
            attrs=["newSpotInstances"],
            key_exception_message=ex_msg_not_found,
            attr_exception_message=f"Spot {ex_msg_not_found}",
        )
        is_compute_updated = True
    if self.args.IsSpecified("remove_reserved_instances"):
      for compute_id in self.args.remove_reserved_instances:
        self._RemoveKeyByAttrFromDictSpec(
            key=compute_id,
            dict_spec=compute,
            attrs=["newReservedInstances"],
            key_exception_message=ex_msg_not_found,
            attr_exception_message=f"Reserved {ex_msg_not_found}",
        )
        is_compute_updated = True
    if self.args.IsSpecified("remove_dws_flex_instances"):
      for compute_id in self.args.remove_dws_flex_instances:
        self._RemoveKeyByAttrFromDictSpec(
            key=compute_id,
            dict_spec=compute,
            attrs=["newDwsFlexInstances", "newFlexStartInstances"],
            key_exception_message=ex_msg_not_found,
            attr_exception_message=f"DWS Flex {ex_msg_not_found}",
        )
        is_compute_updated = True
    if self.args.IsSpecified("add_on_demand_instances"):
      for instance in self.args.add_on_demand_instances:
        self._AddKeyToDictSpec(
            key=instance.get("id"),
            dict_spec=compute,
            value=self._MakeOnDemandComputeResource(instance),
            exception_message=ex_msg_already_exist,
        )
        is_compute_updated = True
    if self.args.IsSpecified("add_spot_instances"):
      for instance in self.args.add_spot_instances:
        self._AddKeyToDictSpec(
            key=instance.get("id"),
            dict_spec=compute,
            value=self._MakeSpotComputeResource(instance),
            exception_message=ex_msg_already_exist,
        )
        is_compute_updated = True
    if self.args.IsSpecified("add_reserved_instances"):
      for instance in self.args.add_reserved_instances:
        self._AddKeyToDictSpec(
            key=instance.get("id"),
            dict_spec=compute,
            value=self._MakeReservedComputeResource(instance),
            exception_message=ex_msg_already_exist,
        )
        is_compute_updated = True
    if self.args.IsSpecified("add_dws_flex_instances"):
      for instance in self.args.add_dws_flex_instances:
        self._AddKeyToDictSpec(
            key=instance.get("id"),
            dict_spec=compute,
            value=self._MakeDwsFlexComputeResource(instance),
            exception_message=ex_msg_already_exist,
        )
        is_compute_updated = True
    if is_compute_updated:
      compute_resources.additionalProperties = [
          self.message_module.Cluster.ComputeResourcesValue.AdditionalProperty(
              key=key, value=value
          )
          for key, value in compute.items()
      ]
      if not compute_resources.additionalProperties:
        raise exceptions.ToolException("Compute instances cannot be empty.")
      self.update_mask.add("compute.resource_requests")
    return compute_resources

  def MakeClusterSlurmOrchestratorPatch(self, cluster_patch):
    """Makes a cluster slurm orchestrator patch message with slurm fields."""
    slurm = self.message_module.SlurmOrchestrator()
    if self.args.IsSpecified("slurm_default_partition"):
      slurm.defaultPartition = self.args.slurm_default_partition
      self.update_mask.add("orchestrator.slurm.default_partition")

    slurm_node_sets = self._ConvertSlurmMessageToDict(
        self.existing_cluster.orchestrator.slurm.nodeSets
    )
    is_node_sets_updated = False
    ex_msg_not_found = "Slurm nodesets with id={0} not found."
    ex_msg_already_exist = "Slurm nodesets with id={0} already exist."
    if self.args.IsSpecified("remove_slurm_node_sets"):
      for node_set_id in self.args.remove_slurm_node_sets:
        self._RemoveKeyFromDictSpec(
            node_set_id, slurm_node_sets, ex_msg_not_found
        )
        is_node_sets_updated = True
    if self.args.IsSpecified("update_slurm_node_sets"):
      for node_set in self.args.update_slurm_node_sets:
        node_set_id = node_set.get("id")
        existing_node_set = self._GetValueFromDictSpec(
            node_set_id, slurm_node_sets, ex_msg_not_found
        )
        if "staticNodeCount" in node_set:
          existing_node_set.staticNodeCount = node_set.get("staticNodeCount")
        if "maxDynamicNodeCount" in node_set:
          existing_node_set.maxDynamicNodeCount = node_set.get(
              "maxDynamicNodeCount"
          )
        slurm_node_sets[node_set_id] = existing_node_set
        is_node_sets_updated = True
    if self.args.IsSpecified("add_slurm_node_sets"):
      for node_set in self.args.add_slurm_node_sets:
        storage_configs_source = self.existing_cluster
        if (
            cluster_patch.storageResources
            and cluster_patch.storageResources.additionalProperties
        ):
          storage_configs_source = cluster_patch
        storage_configs = self._GetStorageConfigs(storage_configs_source)
        compute_id = node_set.get("computeId")
        machine_type = self._GetComputeMachineTypeFromCluster(
            compute_id, cluster_patch, use_existing_cluster=True
        )
        self._AddKeyToDictSpec(
            key=node_set.get("id"),
            dict_spec=slurm_node_sets,
            value=self._MakeSlurmNodeSet(
                node_set, machine_type, storage_configs
            ),
            exception_message=ex_msg_already_exist,
        )
        is_node_sets_updated = True
    if is_node_sets_updated:
      slurm.nodeSets = list(slurm_node_sets.values())
      if not slurm.nodeSets:
        raise exceptions.ToolException("Slurm nodesets cannot be empty.")
      self.update_mask.add("orchestrator.slurm.node_sets")

    slurm_partitions = self._ConvertSlurmMessageToDict(
        self.existing_cluster.orchestrator.slurm.partitions
    )
    is_partitions_updated = False
    ex_msg_not_found = "Slurm partitions with id={0} not found."
    ex_msg_already_exist = "Slurm partitions with id={0} already exist."
    if self.args.IsSpecified("remove_slurm_partitions"):
      for partition_id in self.args.remove_slurm_partitions:
        self._RemoveKeyFromDictSpec(
            partition_id, slurm_partitions, ex_msg_not_found
        )
        is_partitions_updated = True
    if self.args.IsSpecified("update_slurm_partitions"):
      for partition in self.args.update_slurm_partitions:
        partition_id = partition.get("id")
        existing_partition = self._GetValueFromDictSpec(
            partition_id, slurm_partitions, ex_msg_not_found
        )
        if "nodesetIds" in partition:
          existing_partition.nodeSetIds = partition.get("nodesetIds")
        if "exclusive" in partition:
          existing_partition.exclusive = partition.get("exclusive")
        slurm_partitions[partition_id] = existing_partition
        is_partitions_updated = True
    if self.args.IsSpecified("add_slurm_partitions"):
      for partition in self.args.add_slurm_partitions:
        self._AddKeyToDictSpec(
            key=partition.get("id"),
            dict_spec=slurm_partitions,
            value=self._MakeSlurmPartition(partition),
            exception_message=ex_msg_already_exist,
        )
        is_partitions_updated = True
    if is_partitions_updated:
      slurm.partitions = list(slurm_partitions.values())
      if not slurm.partitions:
        raise exceptions.ToolException("Slurm partitions cannot be empty.")
      self.update_mask.add("orchestrator.slurm.partitions")

    if self.args.IsSpecified("update_slurm_login_node"):
      if not self.existing_cluster.orchestrator.slurm.loginNodes:
        raise exceptions.ToolException(
            "Login node is not part of existing cluster spec and cannot be"
            " updated."
        )
      login_nodes = self.existing_cluster.orchestrator.slurm.loginNodes
      login_node_patch = self.args.update_slurm_login_node

      if (count := login_node_patch.get("count")) is not None:
        login_nodes.count = count
      if (startup_script := login_node_patch.get("startupScript")) is not None:
        login_nodes.startupScript = self._GetBashScript(startup_script)
      slurm.loginNodes = login_nodes
      self.update_mask.add("orchestrator.slurm.login_nodes")

    return slurm

  def _GetNetworkName(self, network) -> str:
    """Returns the network name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/global/networks/{network}"

  def _GetSubNetworkName(self, subnetwork) -> str:
    """Returns the subnetwork name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{subnetwork}"

  def _GetNextStorageId(self, storage_counter: int) -> str:
    """Returns the next storage ID."""
    return f"storage{storage_counter}"

  def _GetFilestoreName(self, filestore) -> str:
    """Returns the filestore name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{filestore}"

  def _GetLustreName(self, lustre) -> str:
    """Returns the Lustre name."""
    project = self.cluster_ref.Parent().projectsId
    return f"projects/{project}/{lustre}"

  def _GetReservationName(self, reservation) -> str:
    """Returns the reservation name."""
    project = self.cluster_ref.Parent().projectsId
    if reservation.startswith("projects/"):
      return reservation
    return f"projects/{project}/{reservation}"

  def _GetReservationZone(self, reservation) -> str:
    """Returns the reservation zone."""
    # projects/{project}/zones/{zone}/reservations/{reservation}/reservationBlocks/{reservationBlock}
    parts = reservation.split("/")
    for current_part, next_part in zip(parts, parts[1:]):
      if current_part == "zones" and next_part:
        return next_part
    raise exceptions.ToolException(
        f"Reservation {reservation} does not contain a zone."
    )

  def _GetComputeMachineTypeFromArgs(self, compute_id):
    """Returns the compute machine type from args."""
    instances = []
    if self.args.IsSpecified("on_demand_instances"):
      instances.extend(self.args.on_demand_instances)
    if self.args.IsSpecified("spot_instances"):
      instances.extend(self.args.spot_instances)
    if self.args.IsSpecified("reserved_instances"):
      instances.extend(self.args.reserved_instances)
    if self.args.IsSpecified("dws_flex_instances"):
      instances.extend(self.args.dws_flex_instances)
    for instance in instances:
      if instance.get("id") == compute_id:
        return instance.get("machineType")
    raise exceptions.ToolException(
        f"Compute instances with id={compute_id} not found."
    )

  def _GetComputeMachineTypeFromCluster(
      self, compute_id: str, cluster, use_existing_cluster=False
  ):
    """Returns the compute machine type from cluster."""
    if cluster:
      compute_resources = self._ConvertMessageToDict(cluster.computeResources)
      if compute_id in compute_resources:
        return self._GetComputeMachineType(compute_id, compute_resources)
    if use_existing_cluster:
      compute_resources = self._ConvertMessageToDict(
          self.existing_cluster.computeResources
      )
      if compute_id in compute_resources:
        return self._GetComputeMachineType(compute_id, compute_resources)
    raise exceptions.ToolException(
        f"Compute instances with id={compute_id} not found."
    )

  def _GetComputeMachineType(
      self, compute_id: str, compute_resources: Dict[str, Any]
  ):
    """Returns the compute machine type from compute resources."""
    compute_resource = compute_resources[compute_id]
    if compute_resource.config.newOnDemandInstances:
      return compute_resource.config.newOnDemandInstances.machineType
    if compute_resource.config.newSpotInstances:
      return compute_resource.config.newSpotInstances.machineType
    if compute_resource.config.newReservedInstances:
      return compute_resource.config.newReservedInstances.machineType
    if compute_resource.config.newDwsFlexInstances:
      return compute_resource.config.newDwsFlexInstances.machineType
    if compute_resource.config.newFlexStartInstances:
      return compute_resource.config.newFlexStartInstances.machineType
    raise exceptions.ToolException("Compute instances type not supported.")

  def _GetStorageConfigs(self, cluster):
    """Returns the storage configs."""
    storage_configs: List[self.message_module.StorageConfig] = []
    sorted_storages = sorted(
        cluster.storageResources.additionalProperties,
        key=lambda storage: storage.key,
    )
    if sorted_storages:
      first_storage = sorted_storages[0]
      storage_configs.append(
          self.message_module.StorageConfig(
              id=first_storage.key,
              localMount="/home",
          )
      )
    counters = collections.defaultdict(int)
    for storage in sorted_storages[1:]:
      local_mount = None
      if storage.value:
        if (
            storage.value.config.newFilestore
            or storage.value.config.existingFilestore
        ):
          local_mount = f"/shared{counters['filestore']}"
          counters["filestore"] += 1
        elif (
            storage.value.config.newLustre
            or storage.value.config.existingLustre
        ):
          local_mount = f"/scratch{counters['lustre']}"
          counters["lustre"] += 1
        elif (
            storage.value.config.newBucket
            or storage.value.config.existingBucket
        ):
          local_mount = f"/data{counters['bucket']}"
          counters["bucket"] += 1
      if not local_mount:
        raise exceptions.ToolException(
            "Storage configuration is not supported."
        )

      storage_configs.append(
          self.message_module.StorageConfig(
              id=storage.key,
              localMount=local_mount,
          )
      )
    return storage_configs

  def _GetBashScript(self, arg_value: str) -> str | exceptions.BadFileException:
    """Returns the bash script if argument is a valid bash file path."""
    if not arg_value or not self._CheckIfBashFileFormat(arg_value):
      return arg_value
    path = arg_value
    if not os.path.isabs(path):
      raise exceptions.BadFileException(
          f"Script file path must be absolute, got {path}"
      )
    if not os.path.exists(path) or not os.path.isfile(path):
      raise exceptions.BadFileException(
          f"Script file not found at absolute path={path}"
      )
    return files.ReadFileContents(path)

  def _CheckIfBashFileFormat(self, arg_value: str) -> bool:
    """Checks if the argument is a bash file format."""
    return re.match(r"^\S*\.(sh|bash)$", arg_value)

  def _ConvertMessageToDict(self, message) -> dict[str, Any]:
    """Convert a message with list of type AdditionalProperty(key=str, value=Any) to a dict."""
    if not message:
      return {}
    return {each.key: each.value for each in message.additionalProperties}

  def _ConvertSlurmMessageToDict(self, message):
    """Convert a list of slurm message (SlurmNodeSet, SlurmPartition) to a dict."""
    if not message:
      return {}
    return {each.id: each for each in message}

  def _AddKeyToDictSpec(
      self,
      key: str,
      dict_spec: dict[str, Any],
      value: Any,
      exception_message: str,
  ) -> None | exceptions.ToolException:
    """Adds a cluster identifier (key) with value, if not present in dict spec."""
    if key in dict_spec:
      raise exceptions.ToolException(exception_message.format(key))
    dict_spec[key] = value

  def _RemoveKeyFromDictSpec(
      self, key: str, dict_spec: dict[str, Any], exception_message: str
  ) -> None | exceptions.ToolException:
    """Removes a cluster identifier (key), if present in dict spec."""
    if key not in dict_spec:
      raise exceptions.ToolException(exception_message.format(key))
    dict_spec.pop(key)

  def _RemoveKeyByAttrFromDictSpec(
      self,
      key: str,
      dict_spec: dict[str, Any],
      attrs: List[str],
      key_exception_message: str,
      attr_exception_message: str,
  ) -> None | exceptions.ToolException:
    """Removes a cluster identifier (key) by attribute, if present in dict spec."""
    if key not in dict_spec:
      raise exceptions.ToolException(key_exception_message.format(key))
    if not getattr(dict_spec[key], "config", None):
      raise exceptions.ToolException(attr_exception_message.format(key))
    if not any(getattr(dict_spec[key].config, attr, None) for attr in attrs):
      raise exceptions.ToolException(attr_exception_message.format(key))
    dict_spec.pop(key)

  def _GetValueFromDictSpec(
      self, key: str, dict_spec: dict[str, Any], exception_message: str
  ) -> Any | exceptions.ToolException:
    """Returns the value message by cluster identifier (key) from a dict spec."""
    if key not in dict_spec:
      raise exceptions.ToolException(exception_message.format(key))
    return dict_spec[key]

  def _MakeOnDemandComputeResource(self, instance):
    """Makes a cluster compute resource message for on demand instances."""
    return self.message_module.ComputeResource(
        config=self.message_module.ComputeResourceConfig(
            newOnDemandInstances=self.message_module.NewOnDemandInstancesConfig(
                zone=instance.get("zone"),
                machineType=instance.get("machineType"),
            ),
        ),
    )

  def _MakeSpotComputeResource(self, instance):
    """Makes a cluster compute resource message for spot instances."""
    return self.message_module.ComputeResource(
        config=self.message_module.ComputeResourceConfig(
            newSpotInstances=self.message_module.NewSpotInstancesConfig(
                zone=instance.get("zone"),
                machineType=instance.get("machineType"),
            ),
        ),
    )

  def _MakeReservedComputeResource(self, instance):
    """Makes a cluster compute resource message for reserved instances."""
    reservation = instance.get("reservation")
    return self.message_module.ComputeResource(
        config=self.message_module.ComputeResourceConfig(
            newReservedInstances=self.message_module.NewReservedInstancesConfig(
                reservation=self._GetReservationName(reservation),
                machineType=instance.get("machineType"),
                zone=self._GetReservationZone(reservation),
                type=self.message_module.NewReservedInstancesConfig.TypeValueValuesEnum.SPECIFIC_RESERVATION,
            ),
        ),
    )

  def _MakeDwsFlexComputeResource(self, instance):
    """Makes a cluster compute resource message for DWS Flex instances."""
    return self.message_module.ComputeResource(
        config=self.message_module.ComputeResourceConfig(
            newDwsFlexInstances=self.message_module.NewDWSFlexInstancesConfig(
                zone=instance.get("zone"),
                machineType=instance.get("machineType"),
                maxDuration=instance.get("maxDuration"),
            ),
        ),
    )

  def _MakeSlurmNodeSet(self, node_set, machine_type, storage_configs):
    """Makes a cluster slurm node set message from node set args."""
    return self.message_module.SlurmNodeSet(
        id=node_set.get("id"),
        resourceRequestId=node_set.get("computeId"),
        staticNodeCount=node_set.get("staticNodeCount", 1),
        maxDynamicNodeCount=node_set.get("maxDynamicNodeCount"),
        storageConfigs=storage_configs,
        startupScript=self._GetBashScript(node_set.get("startupScript")),
        labels=self.MakeLabels(
            label_args=node_set.get("labels"),
            label_cls=self.message_module.SlurmNodeSet.LabelsValue,
        ),
        bootDisk=self.MakeDisk(machine_type=machine_type),
    )

  def _MakeSlurmPartition(self, partition):
    """Makes a cluster slurm partition message from partition args."""
    return self.message_module.SlurmPartition(
        id=partition.get("id"),
        nodeSetIds=partition.get("nodesetIds"),
        exclusive=partition.get("exclusive"),
    )
