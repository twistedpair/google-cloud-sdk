# -*- coding: utf-8 -*- #
# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Common utility functions for sql instances."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.sql import api_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


_POSTGRES_DATABASE_VERSION_PREFIX = 'POSTGRES'


def GetRegionFromZone(gce_zone):
  """Parses and returns the region string from the gce_zone string."""
  zone_components = gce_zone.split('-')
  # The region is the first two components of the zone.
  return '-'.join(zone_components[:2])


# TODO(b/73648377): Factor out static methods into module-level functions.
class _BaseInstances(object):
  """Common utility functions for sql instances."""

  @staticmethod
  def GetDatabaseInstances(limit=None, batch_size=None):
    """Gets SQL instances in a given project.

    Modifies current state of an individual instance to 'STOPPED' if
    activationPolicy is 'NEVER'.

    Args:
      limit: int, The maximum number of records to yield. None if all available
          records should be yielded.
      batch_size: int, The number of items to retrieve per request.

    Returns:
      List of yielded sql_messages.DatabaseInstance instances.
    """

    client = api_util.SqlClient(api_util.API_VERSION_DEFAULT)
    sql_client = client.sql_client
    sql_messages = client.sql_messages
    project_id = properties.VALUES.core.project.Get(required=True)

    params = {}
    if limit is not None:
      params['limit'] = limit
    if batch_size is not None:
      params['batch_size'] = batch_size

    yielded = list_pager.YieldFromList(
        sql_client.instances,
        sql_messages.SqlInstancesListRequest(project=project_id), **params)

    def YieldInstancesWithAModifiedState():
      for result in yielded:
        # TODO(b/63139112): Investigate impact of instances without settings.
        if result.settings and result.settings.activationPolicy == 'NEVER':
          result.state = 'STOPPED'
        yield result

    return YieldInstancesWithAModifiedState()

  @staticmethod
  def PrintAndConfirmAuthorizedNetworksOverwrite():
    console_io.PromptContinue(
        message='When adding a new IP address to authorized networks, '
        'make sure to also include any IP addresses that have already been '
        'authorized. Otherwise, they will be overwritten and de-authorized.',
        default=True,
        cancel_on_no=True)

  @staticmethod
  def IsPostgresDatabaseVersion(database_version):
    """Returns a boolean indicating if the database version is Postgres."""
    return _POSTGRES_DATABASE_VERSION_PREFIX in database_version


class InstancesV1Beta3(_BaseInstances):
  """Common utility functions for sql instances V1Beta3."""

  @staticmethod
  def SetProjectAndInstanceFromRef(instance_resource, instance_ref):
    instance_resource.project = instance_ref.project
    instance_resource.instance = instance_ref.instance

  @staticmethod
  def AddBackupConfigToSettings(settings, backup_config):
    settings.backupConfiguration = [backup_config]


class InstancesV1Beta4(_BaseInstances):
  """Common utility functions for sql instances V1Beta4."""

  @staticmethod
  def SetProjectAndInstanceFromRef(instance_resource, instance_ref):
    instance_resource.project = instance_ref.project
    instance_resource.name = instance_ref.instance

  @staticmethod
  def AddBackupConfigToSettings(settings, backup_config):
    settings.backupConfiguration = backup_config
