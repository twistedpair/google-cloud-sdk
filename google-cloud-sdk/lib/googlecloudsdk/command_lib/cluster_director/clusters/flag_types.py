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
    required_keys=["type", "sizeGb"],
    enable_shorthand=True,
    repeated=True,
)

LABEL = arg_parsers.ArgObject(
    key_type=str,
    value_type=str,
    enable_shorthand=True,
)

SERVICE_ACCOUNT = arg_parsers.ArgObject(
    spec={
        "email": str,
        "scopes": arg_parsers.ArgList(element_type=str),
    },
)

V1ALPHA_STORAGE_CONFIG = arg_parsers.ArgObject(
    spec={
        "id": str,
        "localMount": str,
    },
    repeated=True,
)

_V1ALPHA_CLUSTER = {
    "compute": arg_parsers.ArgObject(
        spec={
            "resourceRequests": arg_parsers.ArgObject(
                spec={
                    "disks": DISK,
                    "guestAccelerators": arg_parsers.ArgObject(
                        spec={"acceleratorType": str, "count": int},
                        repeated=True,
                    ),
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
    "description": str,
    "labels": LABEL,
    "name": str,
    "networks": arg_parsers.ArgObject(
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
    "orchestrator": arg_parsers.ArgObject(
        spec={
            "slurm": arg_parsers.ArgObject(
                spec={
                    "config": arg_parsers.ArgObject(
                        spec={
                            "prologEpilogTimeout": str,
                            "prologFlags": arg_parsers.ArgList(
                                element_type=str
                            ),
                            "requeueExitCodes": arg_parsers.ArgList(),
                            "requeueHoldExitCodes": arg_parsers.ArgList(),
                        }
                    ),
                    "defaultPartition": str,
                    "loginNodes": arg_parsers.ArgObject(
                        spec={
                            "count": int,
                            "disks": DISK,
                            "enableOsLogin": bool,
                            "enablePublicIps": bool,
                            "labels": LABEL,
                            "machineType": str,
                            "serviceAccount": SERVICE_ACCOUNT,
                            "startupScript": arg_parsers.ArgObject(),
                            "storageConfigs": V1ALPHA_STORAGE_CONFIG,
                            "zone": str,
                        }
                    ),
                    "nodeSets": arg_parsers.ArgObject(
                        spec={
                            "canIpForward": bool,
                            "enableOsLogin": bool,
                            "enablePublicIps": bool,
                            "id": str,
                            "labels": LABEL,
                            "maxDynamicNodeCount": int,
                            "resourceRequestId": str,
                            "serviceAccount": SERVICE_ACCOUNT,
                            "startupScript": arg_parsers.ArgObject(),
                            "staticNodeCount": int,
                            "storageConfigs": V1ALPHA_STORAGE_CONFIG,
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
                    "epilogBashScripts": arg_parsers.ArgList(),
                    "prologBashScripts": arg_parsers.ArgList(),
                    "taskEpilogBashScripts": arg_parsers.ArgList(),
                    "taskPrologBashScripts": arg_parsers.ArgList(),
                }
            ),
        }
    ),
    "storages": arg_parsers.ArgObject(
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
}

API_VERSION_TO_CLUSTER_FLAG_TYPE = {
    "v1alpha": _V1ALPHA_CLUSTER,
}
