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
"""Useful commands for interacting with the Cloud Firestore Indexes API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.firestore import api_utils
from googlecloudsdk.generated_clients.apis.firestore.v1 import firestore_v1_client
from googlecloudsdk.generated_clients.apis.firestore.v1 import firestore_v1_messages


def _GetIndexService() -> (
    firestore_v1_client.FirestoreV1.ProjectsDatabasesCollectionGroupsIndexesService
):
  """Returns the Firestore Index service for interacting with the Firestore Admin service."""
  return api_utils.GetClient().projects_databases_collectionGroups_indexes


def CreateIndex(
    project: str,
    database: str,
    collection_id: str,
    index: firestore_v1_messages.GoogleFirestoreAdminV1Index,
) -> firestore_v1_messages.GoogleLongrunningOperation:
  """Performs a Firestore Admin v1 Index Creation.

  Args:
    project: the project of the database of the index, a string.
    database: the database id of the index, a string.
    collection_id: the current group of the index, a string.
    index: the index to create, a GoogleFirestoreAdminV1Index message.

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  return _GetIndexService().Create(
      messages.FirestoreProjectsDatabasesCollectionGroupsIndexesCreateRequest(
          parent='projects/{}/databases/{}/collectionGroups/{}'.format(
              project, database, collection_id
          ),
          googleFirestoreAdminV1Index=index,
      )
  )


def ListIndexes(
    project: str, database: str
) -> firestore_v1_messages.GoogleFirestoreAdminV1ListIndexesResponse:
  """Performs a Firestore Admin v1 Index list.

  Args:
    project: the project of the database of the index, a string.
    database: the database id of the index, a string.

  Returns:
    a list of Indexes.
  """
  messages = api_utils.GetMessages()
  return _GetIndexService().List(
      messages.FirestoreProjectsDatabasesCollectionGroupsIndexesListRequest(
          parent='projects/{}/databases/{}/collectionGroups/-'.format(
              project, database
          ),
      )
  )


def DeleteIndex(
    project: str, database: str, index_id: str
) -> firestore_v1_messages.GoogleLongrunningOperation:
  """Performs a Firestore Admin v1 Index Deletion.

  Args:
    project: the project of the database of the index, a string.
    database: the database id of the index, a string.
    index_id: the index id of the index, a string

  Returns:
    an Operation.
  """
  messages = api_utils.GetMessages()
  return _GetIndexService().Delete(
      messages.FirestoreProjectsDatabasesCollectionGroupsIndexesDeleteRequest(
          name=(
              'projects/{}/databases/{}/collectionGroups/-/indexes/{}'.format(
                  project,
                  database,
                  index_id,
              )
          ),
      )
  )
