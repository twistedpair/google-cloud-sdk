# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Utilities for dealing with AI Platform indexes API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import extra_types
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import exceptions as gcloud_exceptions
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.ai import errors
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import yaml


class IndexesClient(object):
  """High-level client for the AI Platform indexes surface."""

  def __init__(self, client=None, messages=None, version=None):
    self.client = client or apis.GetClientInstance(
        constants.AI_PLATFORM_API_NAME,
        constants.AI_PLATFORM_API_VERSION[version])
    self.messages = messages or self.client.MESSAGES_MODULE
    self._service = self.client.projects_locations_indexes

  def _ReadIndexMetadata(self, metadata_file):
    """Parse json metadata file."""
    if not metadata_file:
      raise gcloud_exceptions.BadArgumentException(
          '--metadata-file', 'Index metadata file must be specified.')
    index_metadata = None
    # Yaml is a superset of json, so parse json file as yaml.
    data = yaml.load_path(metadata_file)
    if data:
      index_metadata = messages_util.DictToMessageWithErrorCheck(
          data, extra_types.JsonValue)
    return index_metadata

  def Get(self, index_ref):
    request = self.messages.AiplatformProjectsLocationsIndexesGetRequest(
        name=index_ref.RelativeName())
    return self._service.Get(request)

  def List(self, limit=None, region_ref=None):
    return list_pager.YieldFromList(
        self._service,
        self.messages.AiplatformProjectsLocationsIndexesListRequest(
            parent=region_ref.RelativeName()),
        field='indexes',
        batch_size_attribute='pageSize',
        limit=limit)

  def CreateBeta(self, location_ref, args):
    """Create a new index."""
    labels = labels_util.ParseCreateArgs(
        args, self.messages.GoogleCloudAiplatformV1beta1Index.LabelsValue)
    req = self.messages.AiplatformProjectsLocationsIndexesCreateRequest(
        parent=location_ref.RelativeName(),
        googleCloudAiplatformV1beta1Index=self.messages
        .GoogleCloudAiplatformV1beta1Index(
            displayName=args.display_name,
            description=args.description,
            metadata=self._ReadIndexMetadata(args.metadata_file),
            labels=labels))
    return self._service.Create(req)

  def Create(self, location_ref, args):
    """Create a new v1 index."""
    labels = labels_util.ParseCreateArgs(
        args, self.messages.GoogleCloudAiplatformV1Index.LabelsValue)
    req = self.messages.AiplatformProjectsLocationsIndexesCreateRequest(
        parent=location_ref.RelativeName(),
        googleCloudAiplatformV1Index=self.messages.GoogleCloudAiplatformV1Index(
            displayName=args.display_name,
            description=args.description,
            metadata=self._ReadIndexMetadata(args.metadata_file),
            labels=labels))
    return self._service.Create(req)

  def PatchBeta(self, index_ref, args):
    """Update an index."""
    index = self.messages.GoogleCloudAiplatformV1beta1Index()
    update_mask = []

    if args.metadata_file is not None:
      index.metadata = self._ReadIndexMetadata(args.metadata_file)
      update_mask.append('metadata')
    else:
      if args.display_name is not None:
        index.displayName = args.display_name
        update_mask.append('display_name')

      if args.description is not None:
        index.description = args.description
        update_mask.append('description')

      def GetLabels():
        return self.Get(index_ref).labels

      labels_update = labels_util.ProcessUpdateArgsLazy(
          args, self.messages.GoogleCloudAiplatformV1beta1Index.LabelsValue,
          GetLabels)
      if labels_update.needs_update:
        index.labels = labels_update.labels
        update_mask.append('labels')

    if not update_mask:
      raise errors.NoFieldsSpecifiedError('No updates requested.')

    request = self.messages.AiplatformProjectsLocationsIndexesPatchRequest(
        name=index_ref.RelativeName(),
        googleCloudAiplatformV1beta1Index=index,
        updateMask=','.join(update_mask))
    return self._service.Patch(request)

  def Patch(self, index_ref, args):
    """Update an v1 index."""
    index = self.messages.GoogleCloudAiplatformV1Index()
    update_mask = []

    if args.metadata_file is not None:
      index.metadata = self._ReadIndexMetadata(args.metadata_file)
      update_mask.append('metadata')
    else:
      if args.display_name is not None:
        index.displayName = args.display_name
        update_mask.append('display_name')

      if args.description is not None:
        index.description = args.description
        update_mask.append('description')

      def GetLabels():
        return self.Get(index_ref).labels

      labels_update = labels_util.ProcessUpdateArgsLazy(
          args, self.messages.GoogleCloudAiplatformV1Index.LabelsValue,
          GetLabels)
      if labels_update.needs_update:
        index.labels = labels_update.labels
        update_mask.append('labels')

    if not update_mask:
      raise errors.NoFieldsSpecifiedError('No updates requested.')

    request = self.messages.AiplatformProjectsLocationsIndexesPatchRequest(
        name=index_ref.RelativeName(),
        googleCloudAiplatformV1Index=index,
        updateMask=','.join(update_mask))
    return self._service.Patch(request)

  def Delete(self, index_ref):
    request = self.messages.AiplatformProjectsLocationsIndexesDeleteRequest(
        name=index_ref.RelativeName())
    return self._service.Delete(request)
