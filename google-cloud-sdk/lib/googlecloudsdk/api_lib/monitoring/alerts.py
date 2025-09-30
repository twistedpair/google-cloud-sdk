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
"""Utilities for Cloud Monitoring Alerts API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.monitoring import util


class AlertsClient(object):
  """Client for the Alert service in the Stackdriver Monitoring API."""

  def __init__(self, client=None, messages=None):
    self.client = client or util.GetClientInstance()
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_alerts

  def Get(self, alert_ref):
    """Gets a Monitoring Alert."""
    request = self.messages.MonitoringProjectsAlertsGetRequest(
        name=alert_ref.RelativeName()
    )
    return self._service.Get(request)

  def List(self, project_ref, a_filter=None, order_by=None, page_size=None):
    """Lists Monitoring Alerts."""
    request = self.messages.MonitoringProjectsAlertsListRequest(
        parent=project_ref.RelativeName(),
        filter=a_filter,
        orderBy=order_by,
        pageSize=page_size,
    )
    return self._service.List(request)
