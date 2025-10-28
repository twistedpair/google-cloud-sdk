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
"""Useful commands for interacting with the Cloud Firestore Databases API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.firestore import api_utils


def _GetDatabaseService():
  """Returns the service for interacting with the Firestore admin service."""
  return api_utils.GetClient().projects_databases


def GetDatabase(project, database):
  """Performs a Firestore Admin v1 Database Get.

  Args:
    project: the project id to get, a string.
    database: the database id to get, a string.

  Returns:
    a database.
  """
  messages = api_utils.GetMessages()
  return _GetDatabaseService().Get(
      messages.FirestoreProjectsDatabasesGetRequest(
          name='projects/{}/databases/{}'.format(project, database),
      )
  )


def CreateDatabase(
    project,
    location,
    database,
    database_type,
    database_edition,
    delete_protection_state,
    pitr_state,
    cmek_config,
    mongodb_compatible_data_access_mode,
    firestore_data_access_mode,
    realtime_updates_mode,
    tags=None,
):
  """Performs a Firestore Admin v1 Database Creation.

  Args:
    project: the project id to create, a string.
    location: the database location to create, a string.
    database: the database id to create, a string.
    database_type: the database type, an Enum.
    database_edition: the database edition, an Enum.
    delete_protection_state: the value for deleteProtectionState, an Enum.
    pitr_state: the value for PitrState, an Enum.
    cmek_config: the CMEK config used to encrypt the database, an object.
    mongodb_compatible_data_access_mode: The MongoDB compatible API data access
      mode to use for this database, an Enum.
    firestore_data_access_mode: The Firestore API data access mode to use for
      this database, an Enum.
    realtime_updates_mode: The Realtime Updates mode to use for this database,
      an Enum.
    tags: the tags to attach to the database, a key-value dictionary, or None.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  tags_value = api_utils.ParseTagsForTagsValue(
      tags, messages.GoogleFirestoreAdminV1Database.TagsValue
  )
  return _GetDatabaseService().Create(
      messages.FirestoreProjectsDatabasesCreateRequest(
          parent='projects/{}'.format(project),
          databaseId=database,
          googleFirestoreAdminV1Database=messages.GoogleFirestoreAdminV1Database(
              type=database_type,
              databaseEdition=database_edition,
              locationId=location,
              deleteProtectionState=delete_protection_state,
              pointInTimeRecoveryEnablement=pitr_state,
              cmekConfig=cmek_config,
              mongodbCompatibleDataAccessMode=mongodb_compatible_data_access_mode,
              firestoreDataAccessMode=firestore_data_access_mode,
              realtimeUpdatesMode=realtime_updates_mode,
              tags=tags_value,
          ),
      )
  )


def DeleteDatabase(project, database, etag):
  """Performs a Firestore Admin v1 Database Deletion.

  Args:
    project: the project of the database to delete, a string.
    database: the database id to delete, a string.
    etag: the current etag of the Database, a string.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  return _GetDatabaseService().Delete(
      messages.FirestoreProjectsDatabasesDeleteRequest(
          name='projects/{}/databases/{}'.format(project, database),
          etag=etag,
      )
  )


def ListDatabases(project, show_deleted):
  """Lists all Firestore databases under the project.

  Args:
    project: the project ID to list databases, a string.
    show_deleted: if true, also returns deleted resources, a boolean.

  Returns:
    a List of Databases.
  """
  messages = api_utils.GetMessages()
  return list(
      _GetDatabaseService()
      .List(
          messages.FirestoreProjectsDatabasesListRequest(
              parent='projects/{}'.format(project),
              showDeleted=True if show_deleted else None,
          )
      )
      .databases
  )


def RestoreDatabase(
    project,
    source_backup,
    destination_database,
    encryption_config,
    tags=None,
):
  """Restores a Firestore database from a backup.

  Args:
    project: the project ID to list databases, a string.
    source_backup: the backup to restore from, a string.
    destination_database: the database to restore to, a string.
    encryption_config: the encryption config to use for the restored database,
      an optional object.
    tags: the tags to attach to the database, a key-value dictionary.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  tags_value = api_utils.ParseTagsForTagsValue(
      tags, messages.GoogleFirestoreAdminV1RestoreDatabaseRequest.TagsValue
  )
  restore_request = messages.GoogleFirestoreAdminV1RestoreDatabaseRequest(
      backup=source_backup,
      databaseId=destination_database,
      encryptionConfig=encryption_config,
      tags=tags_value,
  )

  return _GetDatabaseService().Restore(
      messages.FirestoreProjectsDatabasesRestoreRequest(
          parent='projects/{}'.format(project),
          googleFirestoreAdminV1RestoreDatabaseRequest=restore_request,
      )
  )


def CloneDatabase(
    project,
    source_database,
    snapshot_time,
    destination_database,
    encryption_config,
    tags=None,
):
  """Clones one Firestore database from another.

  Args:
    project: the project ID containing the source database, a string.
    source_database: the resource name of the database to clone, a string.
    snapshot_time: the timestamp at which to clone, a DateTime.
    destination_database: the database to clone to, a string.
    encryption_config: the encryption config to use for the cloned database, an
      optional object.
    tags: the tags to attach to the database, a key-value dictionary, or None.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  tags_value = api_utils.ParseTagsForTagsValue(
      tags, messages.GoogleFirestoreAdminV1CloneDatabaseRequest.TagsValue
  )
  clone_request = messages.GoogleFirestoreAdminV1CloneDatabaseRequest(
      pitrSnapshot=messages.GoogleFirestoreAdminV1PitrSnapshot(
          database=source_database,
          snapshotTime=snapshot_time,
      ),
      databaseId=destination_database,
      encryptionConfig=encryption_config,
      tags=tags_value,
  )

  return _GetDatabaseService().Clone(
      messages.FirestoreProjectsDatabasesCloneRequest(
          parent='projects/{}'.format(project),
          googleFirestoreAdminV1CloneDatabaseRequest=clone_request,
      )
  )
