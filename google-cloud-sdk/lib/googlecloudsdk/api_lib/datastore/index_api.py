# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Utilities for Cloud Datastore index management commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from typing import Sequence, Set, Tuple

from googlecloudsdk.api_lib.datastore import util
from googlecloudsdk.api_lib.firestore import api_utils as firestore_utils
from googlecloudsdk.api_lib.firestore import indexes as firestore_indexes
from googlecloudsdk.appengine.datastore import datastore_index
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.console import progress_tracker
from googlecloudsdk.generated_clients.apis.datastore.v1 import datastore_v1_client
from googlecloudsdk.generated_clients.apis.datastore.v1 import datastore_v1_messages
from googlecloudsdk.generated_clients.apis.firestore.v1 import firestore_v1_messages


def GetIndexesService() -> (
    datastore_v1_client.DatastoreV1.ProjectsIndexesService
):
  """Returns the service for interacting with the Datastore Admin Service.

  This is used to manage the datastore indexes (create/delete).
  """
  return util.GetClient().projects_indexes


ASCENDING = (
    util.GetMessages().GoogleDatastoreAdminV1IndexedProperty.DirectionValueValuesEnum.ASCENDING
)

DESCENDING = (
    util.GetMessages().GoogleDatastoreAdminV1IndexedProperty.DirectionValueValuesEnum.DESCENDING
)

NO_ANCESTOR = (
    util.GetMessages().GoogleDatastoreAdminV1Index.AncestorValueValuesEnum.NONE
)

ALL_ANCESTORS = (
    util.GetMessages().GoogleDatastoreAdminV1Index.AncestorValueValuesEnum.ALL_ANCESTORS
)

CREATING = (
    util.GetMessages().GoogleDatastoreAdminV1Index.StateValueValuesEnum.CREATING
)

DATASTORE_API_SCOPE = (
    firestore_utils.GetMessages().GoogleFirestoreAdminV1Index.ApiScopeValueValuesEnum.DATASTORE_MODE_API
)

COLLECTION_GROUP = (
    firestore_utils.GetMessages().GoogleFirestoreAdminV1Index.QueryScopeValueValuesEnum.COLLECTION_GROUP
)

COLLECTION_RECURSIVE = (
    firestore_utils.GetMessages().GoogleFirestoreAdminV1Index.QueryScopeValueValuesEnum.COLLECTION_RECURSIVE
)

FIRESTORE_ASCENDING = (
    firestore_utils.GetMessages().GoogleFirestoreAdminV1IndexField.OrderValueValuesEnum.ASCENDING
)

FIRESTORE_DESCENDING = (
    firestore_utils.GetMessages().GoogleFirestoreAdminV1IndexField.OrderValueValuesEnum.DESCENDING
)


def ApiMessageToIndexDefinition(
    proto: datastore_v1_messages.GoogleDatastoreAdminV1Index,
) -> Tuple[str, datastore_index.Index]:
  """Converts a GoogleDatastoreAdminV1Index to an index definition structure."""
  properties = []
  for prop_proto in proto.properties:
    prop_definition = datastore_index.Property(name=str(prop_proto.name))
    if prop_proto.direction == DESCENDING:
      prop_definition.direction = 'desc'
    else:
      prop_definition.direction = 'asc'
    properties.append(prop_definition)
  index = datastore_index.Index(kind=str(proto.kind), properties=properties)
  if proto.ancestor is not NO_ANCESTOR:
    index.ancestor = True
  return proto.indexId, index


def _Fullmatch(regex, string):
  """Emulate python-3.4 re.fullmatch()."""
  return re.match('(?:' + regex + r')\Z', string, flags=0)


def CollectionIdAndIndexIdFromResourcePath(
    resource_path: str,
) -> Tuple[str, str]:
  """Extracts collectionId and indexId from a collectionGroup resource path.

  Args:
    resource_path: A str to represent firestore resource path contains
      collection group. ex: projects/p/databases/d/collectionGroups/c/indexes/i.

  Returns:
    collection_id: A str to represent the collection id in the resource path.
    index_id: A str to represent the index id in the resource path.

  Raises:
    ValueError: If the resource path is invalid.
  """
  index_name_pattern = '^projects/([^/]*)/databases/([^/]*)/collectionGroups/([^/]*)/indexes/([^/]*)$'
  match = _Fullmatch(regex=index_name_pattern, string=resource_path)
  if not match:
    raise ValueError('Invalid resource path: {}'.format(resource_path))

  return match.group(3), match.group(4)


def FirestoreApiMessageToIndexDefinition(
    proto: firestore_v1_messages.GoogleFirestoreAdminV1Index,
) -> Tuple[str, datastore_index.Index]:
  """Converts a GoogleFirestoreAdminV1Index to an index definition structure.

  Args:
    proto: GoogleFirestoreAdminV1Index

  Returns:
    index_id: A str to represent the index id in the resource path.
    index: A datastore_index.Index that contains index definition.

  Raises:
    ValueError: If GoogleFirestoreAdminV1Index cannot be converted to index
    definition structure.
  """
  properties = []
  for field_proto in proto.fields:
    prop_definition = datastore_index.Property(name=str(field_proto.fieldPath))
    if field_proto.vectorConfig is not None:
      prop_definition.vectorConfig = datastore_index.VectorConfig(
          dimension=field_proto.vectorConfig.dimension,
          flat=datastore_index.VectorFlatIndex(),
      )
    elif field_proto.order == FIRESTORE_DESCENDING:
      prop_definition.direction = 'desc'
    else:
      prop_definition.direction = 'asc'
    properties.append(prop_definition)

  collection_id, index_id = CollectionIdAndIndexIdFromResourcePath(proto.name)
  index = datastore_index.Index(kind=str(collection_id), properties=properties)
  if proto.apiScope != DATASTORE_API_SCOPE:
    raise ValueError('Invalid api scope: {}'.format(proto.apiScope))

  if proto.queryScope == COLLECTION_RECURSIVE:
    index.ancestor = True
  elif proto.queryScope == COLLECTION_GROUP:
    index.ancestor = False
  else:
    raise ValueError('Invalid query scope: {}'.format(proto.queryScope))

  return index_id, index


def BuildIndexProto(
    ancestor: datastore_v1_messages.GoogleDatastoreAdminV1Index.AncestorValueValuesEnum,
    kind: str,
    project_id: str,
    properties: Sequence[datastore_index.Property],
) -> datastore_v1_messages.GoogleDatastoreAdminV1Index:
  """Builds and returns a GoogleDatastoreAdminV1Index."""
  messages = util.GetMessages()
  proto = messages.GoogleDatastoreAdminV1Index()
  proto.projectId = project_id
  proto.kind = kind
  proto.ancestor = ancestor
  proto.state = CREATING
  props = []
  for prop in properties:
    prop_proto = messages.GoogleDatastoreAdminV1IndexedProperty()
    prop_proto.name = prop.name
    if prop.vectorConfig is not None:
      raise ValueError(
          'Vector Indexes cannot be created via the Datastore Admin API'
      )
    if prop.direction == 'asc':
      prop_proto.direction = ASCENDING
    else:
      prop_proto.direction = DESCENDING
    props.append(prop_proto)
  proto.properties = props
  return proto


def BuildIndexFirestoreProto(
    name: str,
    is_ancestor: bool,
    properties: Sequence[datastore_index.Property],
    enable_vector: bool = True,
) -> firestore_v1_messages.GoogleFirestoreAdminV1Index:
  """Builds and returns a GoogleFirestoreAdminV1Index."""
  messages = firestore_utils.GetMessages()
  proto = messages.GoogleFirestoreAdminV1Index()

  proto.name = name
  proto.queryScope = COLLECTION_RECURSIVE if is_ancestor else COLLECTION_GROUP
  proto.apiScope = DATASTORE_API_SCOPE
  fields = []
  for prop in properties:
    field_proto = messages.GoogleFirestoreAdminV1IndexField()
    field_proto.fieldPath = prop.name
    if prop.vectorConfig is not None:
      if not enable_vector:
        raise exceptions.InvalidArgumentException(
            'index.yaml',
            'Vector Indexes are currently only supported in the Alpha Track',
        )
      field_proto.vectorConfig = messages.GoogleFirestoreAdminV1VectorConfig()
      field_proto.vectorConfig.dimension = prop.vectorConfig.dimension
      field_proto.vectorConfig.flat = messages.GoogleFirestoreAdminV1FlatIndex()
    elif prop.direction == 'asc':
      field_proto.order = FIRESTORE_ASCENDING
    else:
      field_proto.order = FIRESTORE_DESCENDING
    fields.append(field_proto)
  proto.fields = fields
  return proto


def BuildIndex(
    is_ancestor: bool,
    kind: str,
    properties: Sequence[Tuple[str, str]],
) -> datastore_index.Index:
  """Builds and returns a datastore_index.Index YAML rep object."""
  index = datastore_index.Index(
      kind=str(kind),
      properties=[
          datastore_index.Property(name=str(prop[0]), direction=prop[1])
          for prop in properties
      ],
  )
  index.ancestor = is_ancestor
  return index


def NormalizeIndexesForDatastoreApi(
    indexes: Sequence[datastore_index.Index],
) -> Set[datastore_index.Index]:
  """Removes the last index property if it is __key__:asc which is redundant."""
  indexes = indexes or []
  for index in indexes or []:
    NormalizeIndexForDatastoreApi(index)
  return set(indexes)


def NormalizeIndexForDatastoreApi(
    index: datastore_index.Index,
) -> datastore_index.Index:
  """Removes the last index property if it is __key__:asc which is redundant."""
  if (
      index.properties
      # The key property path is represented as __key__ in Datastore API
      # and __name__ in Firestore API.
      and index.properties[-1].name in ('__key__', '__name__')
      and index.properties[-1].direction == 'asc'
  ):
    index.properties.pop()
  return index


def NormalizeIndexesForFirestoreApi(
    indexes: Sequence[datastore_index.Index],
) -> Set[datastore_index.Index]:
  """Removes the last index property if it is __name__:asc which is redundant."""
  indexes = indexes or []
  for index in indexes or []:
    NormalizeIndexForFirestoreApi(index)
  return set(indexes)


def NormalizeIndexForFirestoreApi(
    index: datastore_index.Index,
) -> datastore_index.Index:
  """Removes the last index property if it is __name__:asc which is redundant."""
  # Firestore API returns index with '__name__' as opposed to Datastore which
  # returns it as '__key__', normalize that here.
  for prop in index.properties:
    if prop.name == '__key__':
      prop.name = '__name__'

  # If the last property is '__name__ ASC', then we can remove it as the backend
  # assumes that is the case.
  if (
      index.properties
      # The key property path is represented as __key__ in Datastore API
      # and __name__ in Firestore API.
      and index.properties[-1].name in ('__key__', '__name__')
      and index.properties[-1].direction == 'asc'
  ):
    index.properties.pop()
  return index


def ListIndexes(project_id: str) -> Sequence[datastore_index.Index]:
  """Lists all datastore indexes under a database with Datastore Admin API."""
  response = GetIndexesService().List(
      util.GetMessages().DatastoreProjectsIndexesListRequest(
          projectId=project_id
      )
  )
  return {ApiMessageToIndexDefinition(index) for index in response.indexes}


def ListDatastoreIndexesViaFirestoreApi(
    project_id: str,
    database_id: str,
) -> Sequence[datastore_index.Index]:
  """Lists all datastore indexes under a database with Firestore Admin API.

  Args:
    project_id: A str to represent the project id.
    database_id: A str to represent the database id.

  Returns:
    List[index]: A list of datastore_index.Index that contains index definition.
  """
  response = firestore_indexes.ListIndexes(project_id, database_id)
  return {
      FirestoreApiMessageToIndexDefinition(index)
      for index in response.indexes
      if index.apiScope == DATASTORE_API_SCOPE
  }


def CreateIndexesViaDatastoreApi(
    project_id: str,
    indexes_to_create: Sequence[datastore_index.Index],
) -> None:
  """Sends the index creation requests via the Datastore Admin API."""
  cnt = 0
  detail_message = None
  with progress_tracker.ProgressTracker(
      '.', autotick=False, detail_message_callback=lambda: detail_message
  ) as pt:
    for index in indexes_to_create:
      GetIndexesService().Create(
          BuildIndexProto(
              ALL_ANCESTORS if index.ancestor else NO_ANCESTOR,
              kind=index.kind,
              project_id=project_id,
              properties=index.properties,
          )
      )
      cnt = cnt + 1
      detail_message = '{0:.0%}'.format(cnt / len(indexes_to_create))
      pt.Tick()


def CreateIndexesViaFirestoreApi(
    project_id: str,
    database_id: str,
    indexes_to_create: Sequence[datastore_index.Index],
    enable_vector: bool,
) -> None:
  """Sends the index creation requests via the Firestore Admin API."""
  detail_message = None
  with progress_tracker.ProgressTracker(
      '.', autotick=False, detail_message_callback=lambda: detail_message
  ) as pt:
    for i, index in enumerate(indexes_to_create):
      firestore_indexes.CreateIndex(
          project_id,
          database_id,
          index.kind,
          BuildIndexFirestoreProto(
              name=None,
              is_ancestor=index.ancestor,
              properties=index.properties,
              enable_vector=enable_vector,
          ),
      )
      detail_message = '{0:.0%}'.format(i / len(indexes_to_create))
      pt.Tick()


def DeleteIndexes(
    project_id: str,
    indexes_to_delete_ids: Sequence[str],
) -> None:
  """Sends the index deletion requests via the Datastore Admin API."""
  cnt = 0
  detail_message = None
  with progress_tracker.ProgressTracker(
      '.',
      autotick=False,
      detail_message_callback=lambda: detail_message,
  ) as pt:
    for index_id in indexes_to_delete_ids:
      GetIndexesService().Delete(
          util.GetMessages().DatastoreProjectsIndexesDeleteRequest(
              projectId=project_id, indexId=index_id
          )
      )
      cnt = cnt + 1
      detail_message = '{0:.0%}'.format(cnt / len(indexes_to_delete_ids))
      pt.Tick()


def DeleteIndexesViaFirestoreApi(
    project_id: str,
    database_id: str,
    indexes_to_delete_ids: Sequence[str],
) -> None:
  """Sends the index deletion requests via the Firestore Admin API."""
  cnt = 0
  detail_message = None
  delete_cnt = len(indexes_to_delete_ids)
  with progress_tracker.ProgressTracker(
      '.',
      autotick=False,
      detail_message_callback=lambda: detail_message,
  ) as pt:
    for index_id in indexes_to_delete_ids:
      firestore_indexes.DeleteIndex(project_id, database_id, index_id)
      cnt = cnt + 1
      detail_message = '{0:.0%}'.format(cnt / delete_cnt)
      pt.Tick()


def CreateMissingIndexesViaDatastoreApi(
    project_id: str,
    index_definitions: datastore_index.IndexDefinitions,
) -> None:
  """Creates the indexes if the index configuration is not present."""
  indexes = ListIndexes(project_id)
  normalized_indexes = NormalizeIndexesForDatastoreApi(
      index_definitions.indexes
  )
  new_indexes = normalized_indexes - {index for _, index in indexes}
  CreateIndexesViaDatastoreApi(project_id, new_indexes)


def CreateMissingIndexesViaFirestoreApi(
    project_id: str,
    database_id: str,
    index_definitions: datastore_index.IndexDefinitions,
    enable_vector: bool,
) -> None:
  """Creates the indexes via Firestore API if the index configuration is not present."""
  existing_indexes = ListDatastoreIndexesViaFirestoreApi(
      project_id, database_id
  )
  # Firestore API returns index with '__name__' field path. Normalizing the
  # index is required.
  existing_indexes_normalized = NormalizeIndexesForFirestoreApi(
      [index for _, index in existing_indexes]
  )
  normalized_indexes = NormalizeIndexesForFirestoreApi(
      index_definitions.indexes
  )
  new_indexes = normalized_indexes - existing_indexes_normalized

  CreateIndexesViaFirestoreApi(
      project_id=project_id,
      database_id=database_id,
      indexes_to_create=new_indexes,
      enable_vector=enable_vector,
  )
