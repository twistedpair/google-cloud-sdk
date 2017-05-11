# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Shared constants used by container commands."""

EXPIRE_WARNING_DAYS = 14

EXPIRE_WARNING = """
! One or more clusters are approaching expiration and will be deleted.
"""

KUBERNETES_ALPHA_PROMPT = (
    "This will create a cluster with all Kubernetes Alpha features enabled.\n"
    "- This cluster will not be covered by the Container Engine SLA and should"
    " not be used for production workloads.\n"
    "- You will not be able to upgrade the master or nodes.\n"
    "- The cluster will be deleted after 30 days.\n"
)
