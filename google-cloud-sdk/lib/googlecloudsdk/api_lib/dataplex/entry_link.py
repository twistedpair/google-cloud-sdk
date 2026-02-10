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
"""Client and utilities for the Dataplex Entry Links API."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from typing import Any, List

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import log
from googlecloudsdk.core import yaml

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


def Create(args: parser_extensions.Namespace):
  """Create an EntryLink."""
  entry_link_ref = args.CONCEPTS.entry_link.Parse()
  # Read and parse the entry_references.yaml file
  try:
    entry_references_content = yaml.load_path(args.entry_references)
  except (IOError, yaml.Error) as e:
    raise exceptions.BadFileException(
        'entry-references', f'Error reading or parsing YAML file: {e}'
    )
  if not entry_references_content:
    raise exceptions.BadFileException(
        'entry-references', 'The entry references file is empty.'
    )

  # Create the list of entry references objects
  entry_references_message = CreateEntryReferences(
      entry_references_content=entry_references_content
  )

  dataplex_client = dataplex_api.GetClientInstance()
  entry_link_response = dataplex_client.projects_locations_entryGroups_entryLinks.Create(
      dataplex_api.GetMessageModule().DataplexProjectsLocationsEntryGroupsEntryLinksCreateRequest(
          entryLinkId=entry_link_ref.Name(),
          parent=entry_link_ref.Parent().RelativeName(),
          googleCloudDataplexV1EntryLink=dataplex_api.GetMessageModule().GoogleCloudDataplexV1EntryLink(
              entryLinkType=args.entry_link_type,
              entryReferences=entry_references_message,
              name=entry_link_ref.RelativeName(),
              aspects=_GetArgValueOrNone(args, 'aspects'),
          ),
      )
  )
  log.CreatedResource(
      entry_link_response.name,
      details=(
          'Content entry link in project [{0}] with location [{1}] in entry'
          ' group [{2}]'.format(
              entry_link_ref.projectsId,
              entry_link_ref.locationsId,
              entry_link_ref.entryGroupsId,
          )
      ),
  )


def _GenerateAspectKeys(
    args: parser_extensions.Namespace,
    *,
    remove_aspects_arg_name: str,
    update_aspects_arg_name: str,
) -> List[str]:
  """Generate a list of unique aspect keys to be updated or removed."""
  keys = set()
  if args.IsKnownAndSpecified(update_aspects_arg_name):
    keys.update(
        map(
            lambda aspect: aspect.key,
            args.GetValue(update_aspects_arg_name).additionalProperties,
        )
    )
  if args.IsKnownAndSpecified(remove_aspects_arg_name):
    keys.update(args.GetValue(remove_aspects_arg_name))
  return sorted(keys)


def _GetArgValueOrNone(
    args: parser_extensions.Namespace, arg_name: str
) -> Any | None:
  return args.GetValue(arg_name) if args.IsKnownAndSpecified(arg_name) else None


def Update(
    args: parser_extensions.Namespace,
    remove_aspects_arg_name: str = 'remove_aspects',
    update_aspects_arg_name: str = 'update_aspects',
):
  """Create an UpdateEntryLink request based on arguments provided."""
  if not (
      args.IsKnownAndSpecified(remove_aspects_arg_name)
      or args.IsKnownAndSpecified(update_aspects_arg_name)
  ):
    raise exceptions.HttpException(
        'Update commands must specify at least one additional parameter to'
        ' change.'
    )
  entry_link_ref = args.CONCEPTS.entry_link.Parse()
  dataplex_client = dataplex_api.GetClientInstance()
  resource = dataplex_client.projects_locations_entryGroups_entryLinks.Patch(
      module.DataplexProjectsLocationsEntryGroupsEntryLinksPatchRequest(
          name=entry_link_ref.RelativeName(),
          googleCloudDataplexV1EntryLink=module.GoogleCloudDataplexV1EntryLink(
              name=entry_link_ref.RelativeName(),
              aspects=_GetArgValueOrNone(args, update_aspects_arg_name),
          ),
          aspectKeys=_GenerateAspectKeys(
              args,
              remove_aspects_arg_name=remove_aspects_arg_name,
              update_aspects_arg_name=update_aspects_arg_name,
          ),
      )
  )
  log.UpdatedResource(entry_link_ref.RelativeName(), kind='EntryLink')
  return resource
