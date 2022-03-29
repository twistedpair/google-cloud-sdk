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
"""Constants for gkemulticloud."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

MAX_LRO_POLL_INTERVAL_MS = 10000

LRO_KIND = 'Operation'

AZURE_CLIENT_KIND = 'Azure Client'

AZURE_CLUSTER_KIND = 'Azure Cluster'

AZURE_NODEPOOL_KIND = 'Azure Node Pool'

AWS_CLUSTER_KIND = 'AWS Cluster'

AWS_NODEPOOL_KIND = 'AWS Node Pool'

SYSTEM = 'SYSTEM'

WORKLOAD = 'WORKLOAD'
