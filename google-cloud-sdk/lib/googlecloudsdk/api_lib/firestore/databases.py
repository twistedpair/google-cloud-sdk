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
"""Useful commands for interacting with the Cloud Firestore Databases API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from typing import Optional
from googlecloudsdk.api_lib.firestore import api_utils
from googlecloudsdk.calliope import exceptions as ex


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
    delete_protection_state,
    pitr_state,
    cmek_config,
):
  """Performs a Firestore Admin v1 Database Creation.

  Args:
    project: the project id to create, a string.
    location: the database location to create, a string.
    database: the database id to create, a string.
    database_type: the database type, an Enum.
    delete_protection_state: the value for deleteProtectionState, an Enum.
    pitr_state: the value for PitrState, an Enum.
    cmek_config: the CMEK config used to encrypt the database, an object

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  return _GetDatabaseService().Create(
      messages.FirestoreProjectsDatabasesCreateRequest(
          parent='projects/{}'.format(project),
          databaseId=database,
          googleFirestoreAdminV1Database=messages.GoogleFirestoreAdminV1Database(
              type=database_type,
              locationId=location,
              deleteProtectionState=delete_protection_state,
              pointInTimeRecoveryEnablement=pitr_state,
              cmekConfig=cmek_config,
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
    encryption_type: Optional[str],
    kms_key_name: Optional[str],
):
  """Restores a Firestore database from a backup.

  Args:
    project: the project ID to list databases, a string.
    source_backup: the backup to restore from, a string.
    destination_database: the database to restore to, a string.
    encryption_type: the encryption type of the destination database, a string.
    kms_key_name: the kms key name of the destination database, a string.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  restore_request = messages.GoogleFirestoreAdminV1RestoreDatabaseRequest(
      backup=source_backup, databaseId=destination_database
  )

  encryption_type = _NormalizeString(encryption_type)
  if encryption_type == 'google-default-encryption':
    _ThrowIfKmsKeyNameSet(kms_key_name)
    restore_request.useGoogleDefaultEncryption = {}
  elif encryption_type == 'backup-encryption':
    _ThrowIfKmsKeyNameSet(kms_key_name)
    restore_request.useBackupEncryption = {}
  elif encryption_type == 'customer-managed-encryption':
    _ThrowIfKmsKeyNameNotSet(kms_key_name)
    restore_request.kmsKeyName = kms_key_name
  elif encryption_type is not None:
    raise ex.InvalidArgumentException(
        'Invalid encryption type: {}'.format(encryption_type),
        'encryption-type',
    )

  return _GetDatabaseService().Restore(
      messages.FirestoreProjectsDatabasesRestoreRequest(
          parent='projects/{}'.format(project),
          googleFirestoreAdminV1RestoreDatabaseRequest=restore_request,
      )
  )


def _NormalizeString(value: Optional[str]):
  if not value:
    return None
  return value.casefold()


def _ThrowIfKmsKeyNameSet(kms_key_name: Optional[str]):
  if kms_key_name is not None:
    raise ex.ConflictingArgumentsException(
        '--kms-key-name',
        'A KMS Key cannot be set when using an --encryption-type of'
        ' google-default-encryption or backup-encryption.',
    )


def _ThrowIfKmsKeyNameNotSet(kms_key_name: Optional[str]):
  if kms_key_name is None:
    raise ex.RequiredArgumentException(
        '--kms-key-name',
        'The KMS Key Name is required'
        ' when using customer-managed encryption (CMEK), please use'
        ' --kms-key-name to specify this value',
    )
