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
"""Spanner database API helper."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


# The list of pre-defined IAM roles in Spanner.
KNOWN_ROLES = [
    'roles/spanner.admin', 'roles/spanner.databaseAdmin',
    'roles/spanner.databaseReader', 'roles/spanner.databaseUser',
    'roles/spanner.viewer'
]


def Create(instance, database, ddl):
  """Create a new database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  instance_ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesDatabasesCreateRequest(
      parent=instance_ref.RelativeName(),
      createDatabaseRequest=msgs.CreateDatabaseRequest(
          createStatement='CREATE DATABASE `'+database+'`',
          extraStatements=ddl))
  return client.projects_instances_databases.Create(req)


def SetPolicy(database_ref, policy):
  """Saves the given policy on the database, overwriting whatever exists."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesSetIamPolicyRequest(
      resource=database_ref.RelativeName(),
      setIamPolicyRequest=msgs.SetIamPolicyRequest(policy=policy))
  return client.projects_instances_databases.SetIamPolicy(req)


def Delete(instance, database):
  """Delete a database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      database,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancesId': instance
      },
      collection='spanner.projects.instances.databases')
  req = msgs.SpannerProjectsInstancesDatabasesDropDatabaseRequest(
      database=ref.RelativeName())
  return client.projects_instances_databases.DropDatabase(req)


def GetIamPolicy(database_ref):
  """Gets the IAM policy on a database."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  req = msgs.SpannerProjectsInstancesDatabasesGetIamPolicyRequest(
      resource=database_ref.RelativeName())
  return client.projects_instances_databases.GetIamPolicy(req)


def Get(instance, database):
  """Get a database by name."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      database,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancesId': instance
      },
      collection='spanner.projects.instances.databases')
  req = msgs.SpannerProjectsInstancesDatabasesGetRequest(
      name=ref.RelativeName())
  return client.projects_instances_databases.Get(req)


def GetDdl(instance, database):
  """Get a database's DDL description."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      database,
      params={
          'instancesId': instance,
          'projectsId': properties.VALUES.core.project.GetOrFail,
      },
      collection='spanner.projects.instances.databases')
  req = msgs.SpannerProjectsInstancesDatabasesGetDdlRequest(
      database=ref.RelativeName())
  return client.projects_instances_databases.GetDdl(req).statements


def List(instance):
  """List databases in the instance."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  ref = resources.REGISTRY.Parse(
      instance,
      params={'projectsId': properties.VALUES.core.project.GetOrFail},
      collection='spanner.projects.instances')
  req = msgs.SpannerProjectsInstancesDatabasesListRequest(
      parent=ref.RelativeName())
  return list_pager.YieldFromList(
      client.projects_instances_databases,
      req,
      field='databases',
      batch_size_attribute='pageSize')


def UpdateDdl(instance, database, ddl):
  """Update a database via DDL commands."""
  client = apis.GetClientInstance('spanner', 'v1')
  msgs = apis.GetMessagesModule('spanner', 'v1')
  instance_ref = resources.REGISTRY.Parse(
      database,
      params={
          'projectsId': properties.VALUES.core.project.GetOrFail,
          'instancesId': instance
      },
      collection='spanner.projects.instances.databases')
  req = msgs.SpannerProjectsInstancesDatabasesUpdateDdlRequest(
      database=instance_ref.RelativeName(),
      updateDatabaseDdlRequest=msgs.UpdateDatabaseDdlRequest(
          statements=ddl))
  return client.projects_instances_databases.UpdateDdl(req)
