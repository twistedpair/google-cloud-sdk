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
"""Utility for making containeranalysis API calls."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import resources


def GetClient():
  return apis.GetClientInstance('containeranalysis', 'v1')


def GetMessages():
  return apis.GetMessagesModule('containeranalysis', 'v1')


def ListOccurrences(project,
                    resource_filter,
                    occurrence_filter=None):
  """List occurrences for resources in a project."""
  client = GetClient()
  messages = GetMessages()
  base_filter = resource_filter
  if occurrence_filter:
    base_filter = ('({occurrence_filter}) AND ({base_filter})'.format(
        occurrence_filter=occurrence_filter, base_filter=base_filter))

  project_ref = resources.REGISTRY.Parse(
      project, collection='cloudresourcemanager.projects')
  return list_pager.YieldFromList(
      client.projects_occurrences,
      request=messages.ContaineranalysisProjectsOccurrencesListRequest(
          parent=project_ref.RelativeName(), filter=base_filter),
      field='occurrences',
      batch_size=1000,
      batch_size_attribute='pageSize')


def GetVulnerabilitySummary(project, resource_filter):
  """Get vulnerability summary for resources in a project."""
  client = GetClient()
  messages = GetMessages()
  req = (
      messages
      .ContaineranalysisProjectsOccurrencesGetVulnerabilitySummaryRequest(
          parent=project, filter=resource_filter))
  return client.projects_occurrences.GetVulnerabilitySummary(req)

