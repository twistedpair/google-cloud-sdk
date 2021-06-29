# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Command utilities for `gcloud container azure` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


CLUSTERS_FORMAT = """
  table(
    name.segment(-1):label=NAME,
    azureRegion,
    controlPlane.version:label=CONTROL_PLANE_VERSION,
    endpoint:label=CONTROL_PLANE_IP,
    controlPlane.vmSize,
    state)
"""


CLIENT_FORMAT = """
  table(
    name.segment(-1),
    tenantId,
    applicationId)
"""


NODE_POOL_FORMAT = """
  table(name.segment(-1),
    version:label=NODE_VERSION,
    config.vmSize,
    autoscaling.minNodeCount:label=MIN_NODES,
    autoscaling.maxNodeCount:label=MAX_NODES,
    state)
"""
