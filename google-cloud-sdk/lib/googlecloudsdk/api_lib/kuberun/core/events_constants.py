# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Shared constants for kuberun/cloudrun eventing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import enum

EVENTS_CONTROL_PLANE_SERVICE_ACCOUNT = 'cloud-run-events'
EVENTS_BROKER_SERVICE_ACCOUNT = 'cloud-run-events-broker'
EVENTS_SOURCES_SERVICE_ACCOUNT = 'cloud-run-events-sources'

KUBERUN_EVENTS_CONTROL_PLANE_SERVICE_ACCOUNT = 'events-controller-gsa'
KUBERUN_EVENTS_BROKER_SERVICE_ACCOUNT = 'events-broker-gsa'
KUBERUN_EVENTS_SOURCES_SERVICE_ACCOUNT = 'events-sources-gsa'

CLOUDRUN_EVENTS_NAMESPACE = 'cloud-run-events'
KUBERUN_EVENTS_NAMESPACE = 'events-system'


@enum.unique
class Operator(enum.Enum):
  NONE = 'none'
  CLOUDRUN = 'cloudrun'
  KUBERUN = 'kuberun'


@enum.unique
class ClusterEventingType(enum.Enum):
  CLOUDRUN_SECRETS = 'cloudrun-secrets'
  KUBERUN_SECRETS = 'kuberun-secrets'


def ControlPlaneNamespaceFromEventingType(cluster_eventing_type):
  if cluster_eventing_type == ClusterEventingType.CLOUDRUN_SECRETS:
    return CLOUDRUN_EVENTS_NAMESPACE
  elif cluster_eventing_type == ClusterEventingType.KUBERUN_SECRETS:
    return KUBERUN_EVENTS_NAMESPACE
  return None
