# -*- coding: utf-8 -*- #
# Copyright 2025 Google Inc. All Rights Reserved.
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
"""Utilities for Dataplex Entry Link."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.calliope import exceptions

module = dataplex_api.GetMessageModule()

# Define a mapping between user-friendly strings and API enum values
ENTRY_REFERENCE_TYPE_MAPPING = {
    'UNSPECIFIED': (
        module.GoogleCloudDataplexV1EntryLinkEntryReference.TypeValueValuesEnum.UNSPECIFIED
    ),
    'SOURCE': (
        module.GoogleCloudDataplexV1EntryLinkEntryReference.TypeValueValuesEnum.SOURCE
    ),
    'TARGET': (
        module.GoogleCloudDataplexV1EntryLinkEntryReference.TypeValueValuesEnum.TARGET
    ),
}


def CreateEntryReferences(entry_references_content):
  """Create Entry References."""
  entry_references_message = []
  if not entry_references_content:
    raise exceptions.BadFileException(
        'The entry references file is empty.'
    )

  for entry_reference in entry_references_content:
    reference_type_input = entry_reference['type'].upper()
    reference_type_enum = ENTRY_REFERENCE_TYPE_MAPPING.get(reference_type_input)
    if not reference_type_enum:
      raise exceptions.BadFileException(
          f'Invalid entry reference type: {reference_type_input}.'
          ' Valid types are: UNSPECIFIED, SOURCE, TARGET.'
      )
    entry_reference_message = (
        module.GoogleCloudDataplexV1EntryLinkEntryReference(
            name=entry_reference['name'],
            type=reference_type_enum,
        )
    )
    if 'path' in entry_reference:
      entry_reference_message.path = entry_reference['path']
    entry_references_message.append(entry_reference_message)
  if len(entry_references_message) != 2:
    raise exceptions.BadFileException(
        'The entry references file must contain exactly two entries.'
    )
  return entry_references_message
