# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Useful commands for interacting with the Cloud Firestore Admin API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis

DEFAULT_DATABASE = '(default)'

_FIRESTORE_API_VERSION = 'v1'


def GetMessages():
  """Import and return the appropriate admin messages module."""
  return apis.GetMessagesModule('firestore', _FIRESTORE_API_VERSION)


def GetClient():
  """Returns the Cloud Firestore client for the appropriate release track."""
  return apis.GetClientInstance('firestore', _FIRESTORE_API_VERSION)


def GetService():
  """Returns the service for interacting with the Datastore Admin service."""
  return GetClient().projects_databases


def GetLocationService():
  """Returns the Firestore Location service for interacting with the Firestore Admin service."""
  return GetClient().projects_locations


def GetIndexService():
  """Returns the Firestore Index service for interacting with the Firestore Admin service."""
  return GetClient().projects_databases_collectionGroups_indexes


def CreateDatabase(project, location, database, database_type):
  """Performs a Firestore Admin v1 Database Creation.

  Args:
    project: the project id to create, a string.
    location: the database location to create, a string.
    database: the database id to create, a string.
    database_type: the database type, an Enum.

  Returns:
    an Operation.
  """
  messages = GetMessages()
  return GetService().Create(
      messages.FirestoreProjectsDatabasesCreateRequest(
          parent='projects/{}'.format(project),
          databaseId=database,
          googleFirestoreAdminV1Database=messages.GoogleFirestoreAdminV1Database(
              type=database_type, locationId=location
          ),
      )
  )


def ListDatabases(project):
  """Lists all Firestore databases under the project.

  Args:
    project: the project ID to list databases, a string.

  Returns:
    a List of Databases.
  """
  messages = GetMessages()
  return GetService().List(
      messages.FirestoreProjectsDatabasesListRequest(
          parent='projects/{}'.format(project)
      )
  )


def GetExportDocumentsRequest(
    database, output_uri_prefix, namespace_ids=None, collection_ids=None
):
  """Returns a request for a Firestore Admin Export.

  Args:
    database: the database id to export, a string.
    output_uri_prefix: the output GCS path prefix, a string.
    namespace_ids: a string list of namespace ids to export.
    collection_ids: a string list of collection ids to export.

  Returns:
    an ExportDocumentsRequest message.
  """
  messages = GetMessages()
  request_class = messages.GoogleFirestoreAdminV1ExportDocumentsRequest
  kwargs = {'outputUriPrefix': output_uri_prefix}
  if collection_ids:
    kwargs['collectionIds'] = collection_ids

  if namespace_ids is not None:
    kwargs['namespaceIds'] = namespace_ids

  export_request = request_class(**kwargs)

  request = messages.FirestoreProjectsDatabasesExportDocumentsRequest(
      name=database, googleFirestoreAdminV1ExportDocumentsRequest=export_request
  )
  return request


def GetImportDocumentsRequest(
    database, input_uri_prefix, namespace_ids=None, collection_ids=None
):
  """Returns a request for a Firestore Admin Import.

  Args:
    database: the database id to import, a string.
    input_uri_prefix: the location of the GCS export files, a string.
    namespace_ids: a string list of namespace ids to import.
    collection_ids: a string list of collection ids to import.

  Returns:
    an ImportDocumentsRequest message.
  """
  messages = GetMessages()
  request_class = messages.GoogleFirestoreAdminV1ImportDocumentsRequest

  kwargs = {'inputUriPrefix': input_uri_prefix}
  if collection_ids:
    kwargs['collectionIds'] = collection_ids

  if namespace_ids:
    kwargs['namespaceIds'] = namespace_ids

  import_request = request_class(**kwargs)

  return messages.FirestoreProjectsDatabasesImportDocumentsRequest(
      name=database, googleFirestoreAdminV1ImportDocumentsRequest=import_request
  )


def Export(project, database, output_uri_prefix, namespace_ids, collection_ids):
  """Performs a Firestore Admin Export.

  Args:
    project: the project id to export, a string.
    database: the databae id to import, a string.
    output_uri_prefix: the output GCS path prefix, a string.
    namespace_ids: a string list of namespace ids to import.
    collection_ids: a string list of collections to export.

  Returns:
    an Operation.
  """
  dbname = 'projects/{}/databases/{}'.format(project, database)
  return GetService().ExportDocuments(
      GetExportDocumentsRequest(
          database=dbname,
          output_uri_prefix=output_uri_prefix,
          namespace_ids=namespace_ids,
          collection_ids=collection_ids,
      )
  )


def Import(project, database, input_uri_prefix, namespace_ids, collection_ids):
  """Performs a Firestore Admin v1 Import.

  Args:
    project: the project id to import, a string.
    database: the databae id to import, a string.
    input_uri_prefix: the input uri prefix of the exported files, a string.
    namespace_ids: a string list of namespace ids to import.
    collection_ids: a string list of collections to import.

  Returns:
    an Operation.
  """
  dbname = 'projects/{}/databases/{}'.format(project, database)
  return GetService().ImportDocuments(
      GetImportDocumentsRequest(
          database=dbname,
          input_uri_prefix=input_uri_prefix,
          namespace_ids=namespace_ids,
          collection_ids=collection_ids,
      )
  )


def ListLocations(project):
  """Lists locations available to Google Cloud Firestore.

  Args:
    project: the project id to list locations, a string.

  Returns:
    a List of Locations.
  """
  return list_pager.YieldFromList(
      GetLocationService(),
      GetMessages().FirestoreProjectsLocationsListRequest(
          name='projects/{}'.format(project)
      ),
      field='locations',
      batch_size_attribute='pageSize',
  )


def DeleteDatabase(project, database, etag, allow_missing):
  """Performs a Firestore Admin v1 Database Deletion.

  Args:
    project: the project of the database to delete, a string.
    database: the database id to delete, a string.
    etag: the current etag of the Database, a string.
    allow_missing: delete will success on non-existing database if true, a bool.

  Returns:
    an Operation.
  """
  messages = GetMessages()
  return GetService().Delete(
      messages.FirestoreProjectsDatabasesDeleteRequest(
          name='projects/{}/databases/{}'.format(project, database),
          etag=etag,
          allowMissing=allow_missing,
      )
  )


def CreateIndex(project, database, collection_id, index):
  """Performs a Firestore Admin v1 Index Creation.

  Args:
    project: the project of the database of the index, a string.
    database: the database id of the index, a string.
    collection_id: the current group of the index, a string.
    index: the index to create, a googleFirestoreAdminV1Index message.

  Returns:
    an Operation.
  """
  messages = GetMessages()
  return GetIndexService().Create(
      messages.FirestoreProjectsDatabasesCollectionGroupsIndexesCreateRequest(
          parent='projects/{}/databases/{}/collectionGroups/{}'.format(
              project, database, collection_id
          ),
          googleFirestoreAdminV1Index=index
      )
  )


def ListIndexes(project, database):
  """Performs a Firestore Admin v1 Index list.

  Args:
    project: the project of the database of the index, a string.
    database: the database id of the index, a string.

  Returns:
    a list of Indexes.
  """
  messages = GetMessages()
  return GetIndexService().List(
      messages.FirestoreProjectsDatabasesCollectionGroupsIndexesListRequest(
          parent='projects/{}/databases/{}'.format(project, database),
      )
  )
