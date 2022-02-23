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

"""Helpers to validate config set values."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.cloudresourcemanager import projects_api
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import lister
from googlecloudsdk.api_lib.util import exceptions as api_lib_util_exceptions
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.projects import util as command_lib_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.credentials import store as c_store


def WarnIfSettingNonExistentRegionZone(value, zonal=True):
  """Warn if setting 'compute/region' or 'compute/zone' to wrong value."""
  zonal_msg = ('{} is not a valid zone. Run `gcloud compute zones list` to '
               'get all zones.'.format(value))
  regional_msg = ('{} is not a valid region. Run `gcloud compute regions list`'
                  'to get all regions.'.format(value))
  holder = base_classes.ComputeApiHolder(base.ReleaseTrack.GA)
  client = holder.client
  # pylint: disable=protected-access
  request_data = lister._Frontend(None, None, lister.GlobalScope([
      holder.resources.Parse(
          properties.VALUES.core.project.GetOrFail(),
          collection='compute.projects')
  ]))

  list_implementation = lister.GlobalLister(
      client, client.apitools_client.zones if zonal
      else client.apitools_client.regions)
  try:
    response = lister.Invoke(request_data, list_implementation)
    zones = [i['name'] for i in list(response)]
    if value not in zones:
      log.warning(zonal_msg if zonal else regional_msg)
      return True
  except (lister.ListException,
          apitools_exceptions.HttpError,
          c_store.NoCredentialsForAccountException,
          api_lib_util_exceptions.HttpException):
    log.warning('Property validation for compute/{} was skipped.'.format(
        'zone' if zonal else 'region'))
  return False


def WarnIfSettingProjectWithNoAccess(scope, project):
  """Warn if setting 'core/project' config to inaccessible project."""

  # Only display a warning if the following conditions are true:
  #
  # * The current scope is USER (not occurring in the context of installation).
  # * The 'core/account' value is set (a user has authed).
  #
  # If the above conditions are met, check that the project being set exists
  # and is accessible to the current user, otherwise show a warning.
  if (scope == properties.Scope.USER and
      properties.VALUES.core.account.Get()):
    project_ref = command_lib_util.ParseProject(project)
    try:
      with base.WithLegacyQuota():
        projects_api.Get(project_ref, disable_api_enablement_check=True)
    except (apitools_exceptions.HttpError,
            c_store.NoCredentialsForAccountException,
            api_lib_util_exceptions.HttpException):
      log.warning(
          'You do not appear to have access to project [{}] or'
          ' it does not exist.'.format(project))
      return True
  return False


def WarnIfActivateUseClientCertificate(value):
  """Warns if setting context_aware/use_client_certificate to truthy."""
  if value.lower() in ['1', 'true', 'on', 'yes', 'y']:
    mtls_not_supported_msg = (
        'Some services may not support client certificate authorization in '
        'this version of gcloud. When a command sends requests to such '
        'services, the requests will be executed without using a client '
        'certificate.\n\n'
        'Please run $ gcloud topic client-certificate for more information.')
    log.warning(mtls_not_supported_msg)
