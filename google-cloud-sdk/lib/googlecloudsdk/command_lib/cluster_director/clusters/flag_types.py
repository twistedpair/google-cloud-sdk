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

"""Flag type definitions for clusters command group."""

from googlecloudsdk.api_lib.hypercomputecluster import utils as api_utils
from googlecloudsdk.calliope import arg_parsers


MESSAGES = api_utils.GetMessagesModule(api_utils.GetReleaseTrack("v1alpha"))


UPDATE_MASK_OBJECT = arg_parsers.ArgObject(
    value_type=str, enable_shorthand=True
)

NETWORK_OBJECT = arg_parsers.ArgObject(
    spec={
        "name": str,
        "description": str,
    },
    required_keys=["name"],
    enable_shorthand=True,
)

FILESTORES_OBJECT = arg_parsers.ArgObject(
    spec={
        "name": str,
        "tier": MESSAGES.NewFilestoreConfig.TierValueValuesEnum,
        "capacityGb": int,
        "fileshare": str,
        "protocol": MESSAGES.NewFilestoreConfig.ProtocolValueValuesEnum,
        "description": str,
    },
    required_keys=["name", "tier", "capacityGb", "fileshare"],
    enable_shorthand=True,
    repeated=True,
)

LABEL = arg_parsers.ArgObject(
    key_type=str,
    value_type=str,
    enable_shorthand=True,
)

STORAGE_CONFIG = arg_parsers.ArgObject(
    spec={
        "id": str,
        "localMount": str,
    },
    repeated=True,
)

PROTO_BOOT_DISK_TYPE = arg_parsers.ArgObject(
    spec={
        "type": str,
        "sizeGb": int,
        "image": str,
    },
    required_keys=["type", "sizeGb"],
    enable_shorthand=True,
)

PROTO_BOOT_DISK_TYPE_BETA = arg_parsers.ArgObject(
    spec={
        "type": str,
        "sizeGb": int,
    },
    required_keys=["type", "sizeGb"],
    enable_shorthand=True,
)

GCS_BUCKETS_OBJECT = arg_parsers.ArgObject(
    spec={
        "name": str,
        "storageClass": MESSAGES.NewBucketConfig.StorageClassValueValuesEnum,
        "enableAutoclass": bool,
        "enableHNS": bool,
        "autoclassTerminalStorageClass": (
            MESSAGES.GcsAutoclassConfig.TerminalStorageClassValueValuesEnum
        ),
    },
    required_keys=["name"],
    enable_shorthand=True,
    repeated=True,
)

LUSTRES_OBJECT = arg_parsers.ArgObject(
    spec={
        "name": str,
        "filesystem": str,
        "capacityGb": int,
        "description": str,
        "perUnitStorageThroughput": int,
    },
    required_keys=["name", "capacityGb", "filesystem"],
    enable_shorthand=True,
    repeated=True,
)

ON_DEMAND_INSTANCES_OBJECT = arg_parsers.ArgObject(
    spec={
        "id": str,
        "zone": str,
        "machineType": str,
        "atmTags": LABEL,
    },
    required_keys=["id", "zone", "machineType"],
    enable_shorthand=True,
    repeated=True,
)

SPOT_INSTANCES_OBJECT = arg_parsers.ArgObject(
    spec={
        "id": str,
        "zone": str,
        "machineType": str,
        "terminationAction": (
            MESSAGES.NewSpotInstancesConfig.TerminationActionValueValuesEnum
        ),
        "atmTags": LABEL,
    },
    required_keys=["id", "zone", "machineType"],
    enable_shorthand=True,
    repeated=True,
)

RESERVED_INSTANCES_OBJECT = arg_parsers.ArgObject(
    spec={
        "id": str,
        "reservation": str,
        "atmTags": LABEL,
        "reservationBlock": str,
        "reservationSubBlock": str,
    },
    required_keys=["id", "reservation"],
    enable_shorthand=True,
    repeated=True,
)

FLEX_START_INSTANCES_OBJECT = arg_parsers.ArgObject(
    spec={
        "id": str,
        "zone": str,
        "machineType": str,
        "maxDuration": str,
        "atmTags": LABEL,
    },
    required_keys=["id", "zone", "machineType", "maxDuration"],
    enable_shorthand=True,
    repeated=True,
)

SERVICE_ACCOUNT_TYPE = arg_parsers.ArgObject(
    spec={
        "email": str,
        "scopes": arg_parsers.ArgList(),
    }
)

SLURM_CONFIG_TYPE = arg_parsers.ArgObject(
    spec={
        "requeueExitCodes": arg_parsers.ArgList(element_type=int),
        "requeueHoldExitCodes": arg_parsers.ArgList(element_type=int),
        "prologFlags": arg_parsers.ArgList(element_type=str),
        "prologEpilogTimeout": str,
        "accountingStorageEnforceFlags": arg_parsers.ArgList(element_type=str),
        "priorityType": str,
        "priorityWeightAge": int,
        "priorityWeightAssoc": int,
        "priorityWeightFairshare": int,
        "priorityWeightJobSize": int,
        "priorityWeightPartition": int,
        "priorityWeightQos": int,
        "priorityWeightTres": str,
        "preemptMode": arg_parsers.ArgList(element_type=str),
        "preemptType": str,
        "preemptExemptTime": str,
        "healthCheckInterval": int,
        "healthCheckNodeState": str,
        "healthCheckProgram": str,
    }
)
SLURM_NODE_SETS_OBJECT = arg_parsers.ArgObject(
    spec={
        "id": str,
        "computeId": str,
        "staticNodeCount": int,
        "maxDynamicNodeCount": int,
        "startupScript": arg_parsers.ArgObject(),
        "labels": LABEL,
        "bootDisk": PROTO_BOOT_DISK_TYPE,
        "serviceAccount": SERVICE_ACCOUNT_TYPE,
        "startupScriptTimeout": str,
        "container-resource-labels": LABEL,
        "container-startup-script": arg_parsers.ArgObject(),
    },
    required_keys=["id"],
    enable_shorthand=True,
    repeated=True,
)
SLURM_PARTITION_SPEC = {
    "id": str,
    "nodesetIds": arg_parsers.ArgObject(value_type=str, repeated=True),
    "exclusive": bool,
}
SLURM_PARTITIONS_OBJECT = arg_parsers.ArgObject(
    spec=SLURM_PARTITION_SPEC,
    required_keys=["id", "nodesetIds"],
    enable_shorthand=True,
    repeated=True,
)
SLURM_PARTITIONS_UPDATE_OBJECT = arg_parsers.ArgObject(
    spec=SLURM_PARTITION_SPEC,
    required_keys=["id"],
    enable_shorthand=True,
    repeated=True,
)
SLURM_LOGIN_NODE_OBJECT = arg_parsers.ArgObject(
    spec={
        "machineType": str,
        "zone": str,
        "count": int,
        "enableOSLogin": bool,
        "enablePublicIPs": bool,
        "startupScript": arg_parsers.ArgObject(),
        "labels": LABEL,
        "bootDisk": PROTO_BOOT_DISK_TYPE,
        "serviceAccount": SERVICE_ACCOUNT_TYPE,
    },
    required_keys=["machineType", "zone"],
    enable_shorthand=True,
)
SLURM_LOGIN_NODE_UPDATE_OBJECT = arg_parsers.ArgObject(
    spec={
        "count": int,
        "startupScript": arg_parsers.ArgObject(),
        "bootDisk": PROTO_BOOT_DISK_TYPE,
        "serviceAccount": SERVICE_ACCOUNT_TYPE,
    },
    required_keys=[],
    enable_shorthand=True,
)

NEW_ON_DEMAND_INSTANCES_SPEC = {
    "machineType": str,
    "zone": str,
    "atmTags": LABEL,
}
NEW_SPOT_INSTANCES_SPEC = NEW_ON_DEMAND_INSTANCES_SPEC | {
    "terminationAction": str
}
NEW_FLEX_START_INSTANCES_SPEC = NEW_SPOT_INSTANCES_SPEC | {"maxDuration": str}
NEW_RESERVED_INSTANCES_SPEC = NEW_ON_DEMAND_INSTANCES_SPEC | {
    "reservation": str,
    "type": str,
    "reservationBlock": str,
    "reservationSubBlock": str,
}
FILESTORE_CONFIG_SPEC = {
    "description": str,
    "fileShares": arg_parsers.ArgObject(
        spec={"capacityGb": int, "fileShare": str},
        repeated=True,
    ),
    "filestore": str,
    "protocol": str,
    "tier": str,
}
BUCKET_CONFIG_SPEC = {
    "autoclass": arg_parsers.ArgObject(
        spec={
            "enabled": bool,
            "terminalStorageClass": str,
        }
    ),
    "bucket": str,
    "hierarchicalNamespace": arg_parsers.ArgObject(spec={"enabled": bool}),
    "storageClass": str,
}
LUSTRE_CONFIG_SPEC = {
    "capacityGb": int,
    "description": str,
    "filesystem": str,
    "lustre": str,
}
_CLUSTER = {
    "computeResources": arg_parsers.ArgObject(
        key_type=str,
        value_type=arg_parsers.ArgObject(
            spec={
                "config": arg_parsers.ArgObject(
                    spec={
                        "newFlexStartInstances": arg_parsers.ArgObject(
                            spec=NEW_FLEX_START_INSTANCES_SPEC
                        ),
                        "newDwsFlexInstances": arg_parsers.ArgObject(
                            spec=NEW_FLEX_START_INSTANCES_SPEC
                        ),
                        "newOnDemandInstances": arg_parsers.ArgObject(
                            spec=NEW_ON_DEMAND_INSTANCES_SPEC
                        ),
                        "newReservedInstances": arg_parsers.ArgObject(
                            spec=NEW_RESERVED_INSTANCES_SPEC
                        ),
                        "newSpotInstances": arg_parsers.ArgObject(
                            spec=NEW_SPOT_INSTANCES_SPEC
                        ),
                    }
                ),
            }
        ),
    ),
    "description": str,
    "labels": LABEL,
    "name": str,
    "networkResources": arg_parsers.ArgObject(
        key_type=str,
        value_type=arg_parsers.ArgObject(
            spec={
                "config": arg_parsers.ArgObject(
                    spec={
                        "existingNetwork": arg_parsers.ArgObject(
                            spec={
                                "network": str,
                                "subnetwork": str,
                            }
                        ),
                        "newNetwork": arg_parsers.ArgObject(
                            spec={
                                "description": str,
                                "network": str,
                            }
                        ),
                        "newComputeNetwork": arg_parsers.ArgObject(
                            spec={
                                "description": str,
                                "network": str,
                            }
                        ),
                        "existingComputeNetwork": arg_parsers.ArgObject(
                            spec={
                                "network": str,
                                "subnetwork": str,
                            }
                        ),
                    }
                ),
            }
        ),
    ),
    "orchestrator": arg_parsers.ArgObject(
        spec={
            "slurm": arg_parsers.ArgObject(
                spec={
                    "defaultPartition": str,
                    "loginNodes": arg_parsers.ArgObject(
                        spec={
                            "count": int,
                            "enableOsLogin": bool,
                            "enablePublicIps": bool,
                            "labels": LABEL,
                            "machineType": str,
                            "startupScript": arg_parsers.ArgObject(),
                            "storageConfigs": STORAGE_CONFIG,
                            "zone": str,
                            "bootDisk": PROTO_BOOT_DISK_TYPE,
                            "serviceAccount": SERVICE_ACCOUNT_TYPE,
                        }
                    ),
                    "nodeSets": arg_parsers.ArgObject(
                        spec={
                            "id": str,
                            "maxDynamicNodeCount": int,
                            "staticNodeCount": int,
                            "storageConfigs": STORAGE_CONFIG,
                            "computeId": str,
                            "serviceAccount": SERVICE_ACCOUNT_TYPE,
                            "computeInstance": arg_parsers.ArgObject(
                                spec={
                                    "startupScript": arg_parsers.ArgObject(),
                                    "labels": LABEL,
                                    "bootDisk": PROTO_BOOT_DISK_TYPE,
                                }
                            ),
                            "containerNodePool": arg_parsers.ArgObject(spec={}),
                        },
                        repeated=True,
                    ),
                    "partitions": arg_parsers.ArgObject(
                        spec={
                            "exclusive": bool,
                            "id": str,
                            "nodeSetIds": arg_parsers.ArgObject(
                                repeated=True,
                            ),
                        },
                        repeated=True,
                    ),
                    "prologBashScripts": arg_parsers.ArgList(),
                    "epilogBashScripts": arg_parsers.ArgList(),
                    "taskPrologBashScripts": arg_parsers.ArgList(),
                    "taskEpilogBashScripts": arg_parsers.ArgList(),
                    "config": SLURM_CONFIG_TYPE,
                    "disableHealthCheckProgram": bool,
                }
            ),
        }
    ),
    "storageResources": arg_parsers.ArgObject(
        key_type=str,
        value_type=arg_parsers.ArgObject(
            spec={
                "config": arg_parsers.ArgObject(
                    spec={
                        "existingBucket": arg_parsers.ArgObject(
                            spec={"bucket": str}
                        ),
                        "existingFilestore": arg_parsers.ArgObject(
                            spec={"filestore": str}
                        ),
                        "existingLustre": arg_parsers.ArgObject(
                            spec={"lustre": str}
                        ),
                        "newBucket": arg_parsers.ArgObject(
                            spec=BUCKET_CONFIG_SPEC
                        ),
                        "newFilestore": arg_parsers.ArgObject(
                            spec=FILESTORE_CONFIG_SPEC
                        ),
                        "newLustre": arg_parsers.ArgObject(
                            spec=LUSTRE_CONFIG_SPEC
                            | {"perUnitStorageThroughput": int}
                        ),
                    },
                )
            }
        ),
    ),
}

API_VERSION_TO_CLUSTER_FLAG_TYPE = {
    "v1alpha": _CLUSTER,
}
