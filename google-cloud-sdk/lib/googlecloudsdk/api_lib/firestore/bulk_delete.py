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
"""Useful commands for interacting with the Cloud Firestore Bulk Delete API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.firestore import api_utils


def _GetDatabaseService():
  """Returns the service for interacting with the Datastore Admin service."""
  return api_utils.GetClient().projects_databases


def GetBulkDeleteDocumentsRequest(
    database, namespace_ids=None, collection_ids=None
):
  """Returns a request for a Firestore Admin Bulk Delete.

  Args:
    database: the database id to bulk delete, a string.
    namespace_ids: a string list of namespace ids to delete.
    collection_ids: a string list of collection ids to delete.

  Returns:
    a BulkDeleteDocumentsRequest message.
  """
  messages = api_utils.GetMessages()
  request_class = messages.GoogleFirestoreAdminV1BulkDeleteDocumentsRequest

  kwargs = {}
  if collection_ids:
    kwargs['collectionIds'] = collection_ids

  if namespace_ids:
    kwargs['namespaceIds'] = namespace_ids

  bulk_delete_request = request_class(**kwargs)

  return messages.FirestoreProjectsDatabasesBulkDeleteDocumentsRequest(
      name=database,
      googleFirestoreAdminV1BulkDeleteDocumentsRequest=bulk_delete_request,
  )


def BulkDelete(project, database, namespace_ids, collection_ids):
  """Performs a Firestore Admin v1 Bulk Delete.

  Args:
    project: the project id, a string.
    database: the databae id, a string.
    namespace_ids: a string list of namespace ids to bulk delete.
    collection_ids: a string list of collections to bulk delete.

  Returns:
    an Operation.
  """
  dbname = 'projects/{}/databases/{}'.format(project, database)
  return _GetDatabaseService().BulkDeleteDocuments(
      GetBulkDeleteDocumentsRequest(
          database=dbname,
          namespace_ids=namespace_ids,
          collection_ids=collection_ids,
      )
  )
