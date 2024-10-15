# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Utilities for Cloud Monitoring Metric service API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


def GetClientInstance(no_http=False):
  return apis.GetClientInstance('monitoring', 'v3', no_http=no_http)


def GetMessagesModule():
  return GetClientInstance().MESSAGES_MODULE


class MetricClient(object):
  """Client for the Metric service in the Cloud Monitoring API."""

  def __init__(self):
    self.client = GetClientInstance()
    self.messages = GetMessagesModule()

  def ListTimeSeriesByProject(
      self,
      project,
      aggregation_alignment_period,
      aggregation_per_series_aligner,
      interval_start_time,
      interval_end_time,
      filter_str,
  ):
    """List the Metrics Scopes monitoring the specified project."""
    request = self.messages.MonitoringProjectsTimeSeriesListRequest(
        name=f'projects/{project}',
        aggregation_alignmentPeriod=aggregation_alignment_period,
        aggregation_perSeriesAligner=aggregation_per_series_aligner,
        interval_startTime=interval_start_time,
        interval_endTime=interval_end_time,
        filter=filter_str,
        view=self.messages.MonitoringProjectsTimeSeriesListRequest.ViewValueValuesEnum.FULL,
    )
    return self.client.projects_timeSeries.List(request)
