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
"""Utils for GKE Hub Anthos Config Management commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.command_lib.container.hub.features import base
from googlecloudsdk.command_lib.container.hub.features import info
from googlecloudsdk.core import exceptions


LATEST_VERSION = '1.7.2'

APPLY_SPEC_VERSION_1 = """
applySpecVersion: 1
spec:
  configSync:
    enabled: false
    sourceFormat: hierarchy
    policyDir:
    httpsProxy:
    secretType: none|ssh|cookiefile|token|gcenode
    syncBranch: master
    syncRepo: URL
    syncWait: 15
    syncRev: HEAD
  policyController:
    enabled: false
    referentialRulesEnabled: false
    templateLibraryInstalled: true
    logDeniesEnabled: false
    auditIntervalSeconds: 60
    exemptableNamespaces: []
  hierarchyController:
     enabled: false
     enablePodTreeLabels: false
     enableHierarchicalResourceQuota: false
"""

CONFIG_SYNC = 'configSync'
POLICY_CONTROLLER = 'policyController'
HNC = 'hierarchyController'


def try_get_configmanagement(project):
  """Get the configmanagement Feature resource in Hub.

  Args:
    project: the project id to query the Feature

  Returns:
    the response of configmanagement Feature resource.

  Raises:
    - exceptions if the feature is not enabled or user is not authorized.
  """
  feature = 'configmanagement'
  try:
    name = 'projects/{0}/locations/global/features/{1}'.format(
        project, feature)
    response = base.GetFeature(name)
  except apitools_exceptions.HttpUnauthorizedError as e:
    raise exceptions.Error(
        'You are not authorized to see the status of {} '
        'Feature from project [{}]. Underlying error: {}'.format(
            info.Get(feature).display_name, project, e))
  except apitools_exceptions.HttpNotFoundError as e:
    raise exceptions.Error(
        '{} Feature for project [{}] is not enabled'.format(
            info.Get(feature).display_name, project))
  return response
