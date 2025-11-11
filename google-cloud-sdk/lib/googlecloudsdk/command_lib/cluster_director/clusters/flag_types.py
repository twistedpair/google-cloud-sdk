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

from googlecloudsdk.calliope import arg_parsers

DISK = arg_parsers.ArgObject(
    spec={
        "type": str,
        "sizeGb": int,
        "boot": bool,
        "sourceImage": str,
    },
    required_keys=["type", "boot"],
    enable_shorthand=True,
    repeated=True,
)

BOOT_DISK = arg_parsers.ArgObject(
    spec={
        "type": str,
        "sizeGb": int,
        "boot": bool,
        "sourceImage": str,
    },
    required_keys=["type", "boot"],
    enable_shorthand=True,
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
    }
)

_CLUSTER = {
    "compute": arg_parsers.ArgObject(  # v1alpha only field
        spec={
            "resourceRequests": arg_parsers.ArgObject(
                spec={
                    "disks": DISK,
                    "id": str,
                    "machineType": str,
                    "maxRunDuration": int,
                    "provisioningModel": str,
                    "reservationAffinity": arg_parsers.ArgObject(
                        spec={
                            "key": str,
                            "type": str,
                            "values": arg_parsers.ArgList(),
                        }
                    ),
                    "terminationAction": str,
                    "zone": str,
                },
                repeated=True,
            ),
        }
    ),
    "computeResources": arg_parsers.ArgObject(
        key_type=str,
        value_type=arg_parsers.ArgObject(
            spec={
                "config": arg_parsers.ArgObject(
                    spec={
                        "newFlexStartInstances": arg_parsers.ArgObject(
                            spec={
                                "machineType": str,
                                "maxDuration": str,
                                "zone": str,
                                "atmTags": LABEL,
                                "bootDisk": BOOT_DISK,
                                "terminationAction": str,
                            }
                        ),
                        "newDwsFlexInstances": arg_parsers.ArgObject(
                            spec={
                                "machineType": str,
                                "maxDuration": str,
                                "zone": str,
                                "atmTags": LABEL,
                                "bootDisk": BOOT_DISK,
                                "terminationAction": str,
                            }
                        ),
                        "newOnDemandInstances": arg_parsers.ArgObject(
                            spec={
                                "machineType": str,
                                "zone": str,
                                "atmTags": LABEL,
                                "bootDisk": BOOT_DISK,
                            }
                        ),
                        "newReservedInstances": arg_parsers.ArgObject(
                            spec={
                                "machineType": str,
                                "reservation": str,
                                "type": str,
                                "zone": str,
                                "atmTags": LABEL,
                                "bootDisk": BOOT_DISK,
                                "reservationBlock": str,
                                "reservationSubBlock": str,
                            }
                        ),
                        "newSpotInstances": arg_parsers.ArgObject(
                            spec={
                                "machineType": str,
                                "zone": str,
                                "atmTags": LABEL,
                                "bootDisk": BOOT_DISK,
                                "terminationAction": str,
                            }
                        ),
                    }
                ),
            }
        ),
    ),
    "description": str,
    "labels": LABEL,
    "name": str,
    "networks": arg_parsers.ArgObject(  # v1alpha only field
        spec={
            "initializeParams": arg_parsers.ArgObject(
                spec={
                    "description": str,
                    "network": str,
                }
            ),
            "networkSource": arg_parsers.ArgObject(
                spec={
                    "network": str,
                    "subnetwork": str,
                }
            ),
        },
        repeated=True,
    ),
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
                            "disks": DISK,
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
                            "bootDisk": BOOT_DISK,
                            "id": str,
                            "labels": LABEL,
                            "maxDynamicNodeCount": int,
                            "resourceRequestId": str,
                            "startupScript": arg_parsers.ArgObject(),
                            "staticNodeCount": int,
                            "storageConfigs": STORAGE_CONFIG,
                            "computeId": str,
                            "serviceAccount": SERVICE_ACCOUNT_TYPE,
                            "enableOsLogin": bool,
                            "canIpForward": bool,
                            "enablePublicIps": bool,
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
                }
            ),
        }
    ),
    "storages": arg_parsers.ArgObject(  # v1alpha only field
        spec={
            "id": str,
            "initializeParams": arg_parsers.ArgObject(
                spec={
                    "filestore": arg_parsers.ArgObject(
                        spec={
                            "description": str,
                            "fileShares": arg_parsers.ArgObject(
                                spec={"capacityGb": int, "fileShare": str},
                                repeated=True,
                            ),
                            "filestore": str,
                            "protocol": str,
                            "tier": str,
                        }
                    ),
                    "gcs": arg_parsers.ArgObject(
                        spec={
                            "autoclass": arg_parsers.ArgObject(
                                spec={
                                    "enabled": bool,
                                    "terminalStorageClass": str,
                                }
                            ),
                            "bucket": str,
                            "hierarchicalNamespace": arg_parsers.ArgObject(
                                spec={"enabled": bool}
                            ),
                            "storageClass": str,
                        }
                    ),
                    "lustre": arg_parsers.ArgObject(
                        spec={
                            "capacityGb": int,
                            "description": str,
                            "filesystem": str,
                            "lustre": str,
                        }
                    ),
                }
            ),
            "storageSource": arg_parsers.ArgObject(
                spec={
                    "bucket": str,
                    "filestore": str,
                    "lustre": str,
                }
            ),
        },
        repeated=True,
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
                            spec={
                                "autoclass": arg_parsers.ArgObject(
                                    spec={
                                        "enabled": bool,
                                        "terminalStorageClass": str,
                                    }
                                ),
                                "bucket": str,
                                "hierarchicalNamespace": arg_parsers.ArgObject(
                                    spec={"enabled": bool}
                                ),
                                "storageClass": str,
                            }
                        ),
                        "newFilestore": arg_parsers.ArgObject(
                            spec={
                                "description": str,
                                "fileShares": arg_parsers.ArgObject(
                                    spec={"capacityGb": int, "fileShare": str},
                                    repeated=True,
                                ),
                                "filestore": str,
                                "protocol": str,
                                "tier": str,
                            }
                        ),
                        "newLustre": arg_parsers.ArgObject(
                            spec={
                                "capacityGb": int,
                                "description": str,
                                "filesystem": str,
                                "lustre": str,
                                "perUnitStorageThroughput": int,
                            }
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
