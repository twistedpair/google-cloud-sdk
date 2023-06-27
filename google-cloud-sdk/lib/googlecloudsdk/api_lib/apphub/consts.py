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
"""Consts for Apphub Cloud SDK."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class Resource:
  TOPOLOGY = 'topology'
  TELEMETRY = 'telemetry'


class UpdateTopology:

  EMPTY_UPDATE_HELP_TEXT = 'Please specify fields to update.'

  STATE_ENABLED = 'enabled'
  STATE_DISABLED = 'disabled'

  UPDATE_MASK_ENABLED_FIELD_NAME = 'enabled'

  WAIT_FOR_UPDATE_MESSAGE = 'Updating topology'
  UPDATE_TIMELIMIT_SEC = 60


class UpdateTelemetry:

  EMPTY_UPDATE_HELP_TEXT = 'Please specify fields to update.'

  MONITORING_STATE_ENABLED = 'enabled'
  MONITORING_STATE_DISABLED = 'disabled'

  UPDATE_MASK_MONITORING_ENABLED_FIELD_NAME = 'monitoringEnabled'

  WAIT_FOR_UPDATE_MESSAGE = 'Updating telemetry'
  UPDATE_TIMELIMIT_SEC = 60
