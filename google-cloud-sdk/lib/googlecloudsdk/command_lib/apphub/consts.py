# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Apphub Command Lib Consts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class Resource:
  PROJECTS_ID = 'projectsId'
  GLOBAL_LOCATION = 'global'


class Collections:
  PROJECTS_LOCATIONS = 'apphub.projects.locations'


class Topology:
  """Consts for Topology."""
  TOPOLOGY_SUFFIX = '/topology'

  STATE_ENABLED = 'enabled'
  STATE_DISABLED = 'disabled'
  VALID_STATES = [STATE_ENABLED, STATE_DISABLED]

  NAME = 'name'
  ENABLED = 'enabled'
  PROJECT = 'project'


class Telemetry:
  """Consts for Telemetry."""
  TELEMETRY_SUFFIX = '/telemetry'

  MONITORING_STATE_ENABLED = 'enabled'
  MONITORING_STATE_DISABLED = 'disabled'
  VALID_MONITORING_STATES = [
      MONITORING_STATE_ENABLED,
      MONITORING_STATE_DISABLED,
  ]

  NAME = 'name'
  MONITORING_ENABLED = 'monitoring_enabled'
  PROJECT = 'project'
