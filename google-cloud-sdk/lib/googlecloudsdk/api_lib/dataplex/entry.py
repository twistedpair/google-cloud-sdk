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
"""Client for interaction with Entries API CRUD DATAPLEX."""

from __future__ import annotations

from typing import Any, Dict, List

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.dataplex import parsers as dataplex_parsers
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.core import log


dataplex_message = dataplex_api.GetMessageModule()


def _GetFieldsForUpdateMask(args: parser_extensions.Namespace) -> List[str]:
  """Create a sorted list of fields to be used in update_mask for Entry based on arguments provided to the command."""

  # Map command arguments to the API proto fields.
  arg_name_to_field = {
      '--fully-qualified-name': 'fully_qualified_name',
      '--update-aspects': 'aspects',  # For update command
      '--remove-aspects': 'aspects',  # For update command
      '--aspects': 'aspects',  # For update-aspects command
      '--keys': 'aspects',  # For remove-aspects command
      '--entry-source-resource': 'entry_source.resource',
      '--entry-source-system': 'entry_source.system',
      '--entry-source-platform': 'entry_source.platform',
      '--entry-source-display-name': 'entry_source.display_name',
      '--entry-source-description': 'entry_source.description',
      '--entry-source-labels': 'entry_source.labels',
      '--entry-source-create-time': 'entry_source.create_time',
      '--entry-source-update-time': 'entry_source.update_time',
  }

  # Remove `--clear-` part from command argument names, as those args are meant
  # to clear the respective API proto fields. Select only those that were
  # supplied to the command by performing a set intersection.
  args_cleaned = set(
      map(
          lambda arg: arg.replace('--clear-', '--'), args.GetSpecifiedArgNames()
      )
  )
  updatable_args = args_cleaned.intersection(arg_name_to_field)
  return sorted(
      set(map(lambda arg_name: arg_name_to_field[arg_name], updatable_args))
  )


def _GenerateAspectKeys(
    args: parser_extensions.Namespace,
    *,
    remove_aspects_arg_name: str,
    update_aspects_arg_name: str,
) -> List[str]:
  """Generate a list of unique aspect keys to be updated or removed.

  This will be used along with the update_mask for updating an Entry. This list
  is populated based on `--update-aspects` and `--remove-aspects` arguments
  (or `--aspects` in case of specialized command like `update-aspects`).

  Args:
    args: The arguments provided to the command.
    remove_aspects_arg_name: The name of the argument that contains the aspect
      keys to be removed.
    update_aspects_arg_name: The name of the argument that contains aspect
      contents to be added or updated.

  Returns:
    A sorted list of unique aspect keys to be updated or removed. Or empty list
    if neither `--update-aspects`, `--remove-aspects` or `--aspects` are
    provided to the command.
  """
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


def _GetEntrySourceLabels(
    args: parser_extensions.Namespace,
) -> Dict[str, str] | None:
  """Parse EntrySource labels from the command arguments if defined."""

  if not args.IsKnownAndSpecified('entry_source_labels'):
    return None
  return labels_util.ParseCreateArgs(
      args,
      labels_cls=dataplex_message.GoogleCloudDataplexV1EntrySource.LabelsValue,
      labels_dest='entry_source_labels',
  )


def _GetEntrySourceAncestors(
    args: parser_extensions.Namespace,
) -> List[Any]:
  """Parse EntrySource ancestors from the command arguments if defined."""
  if not args.IsKnownAndSpecified('entry_source_ancestors'):
    return []
  return dataplex_parsers.ParseEntrySourceAncestors(args.entry_source_ancestors)


def _GetEntrySourceOrNone(
    args: parser_extensions.Namespace,
) -> dataplex_message.GoogleCloudDataplexV1EntrySource | None:
  """Parse EntrySource from the command arguments if defined."""
  entry_source = dataplex_message.GoogleCloudDataplexV1EntrySource(
      resource=_GetArgValueOrNone(args, 'entry_source_resource'),
      system=_GetArgValueOrNone(args, 'entry_source_system'),
      platform=_GetArgValueOrNone(args, 'entry_source_platform'),
      displayName=_GetArgValueOrNone(args, 'entry_source_display_name'),
      description=_GetArgValueOrNone(args, 'entry_source_description'),
      labels=_GetEntrySourceLabels(args),
      ancestors=_GetEntrySourceAncestors(args),
      createTime=_GetArgValueOrNone(args, 'entry_source_create_time'),
      updateTime=_GetArgValueOrNone(args, 'entry_source_update_time'),
  )
  return None if not entry_source else entry_source


def Create(args: parser_extensions.Namespace):
  """Create a CreateEntry request based on arguments provided."""
  entry_ref = args.CONCEPTS.entry.Parse()
  entry_type_ref = args.CONCEPTS.entry_type.Parse()
  parent_entry_ref = args.CONCEPTS.parent_entry.Parse()

  dataplex_client = dataplex_api.GetClientInstance()

  parent_entry_name = ''
  if parent_entry_ref is not None:
    parent_entry_name = parent_entry_ref.RelativeName()

  resource = dataplex_client.projects_locations_entryGroups_entries.Create(
      dataplex_message.DataplexProjectsLocationsEntryGroupsEntriesCreateRequest(
          entryId=entry_ref.Name(),
          googleCloudDataplexV1Entry=dataplex_message.GoogleCloudDataplexV1Entry(
              name=entry_ref.RelativeName(),
              entryType=entry_type_ref.RelativeName(),
              parentEntry=parent_entry_name,
              fullyQualifiedName=_GetArgValueOrNone(
                  args, 'fully_qualified_name'
              ),
              aspects=_GetArgValueOrNone(args, 'aspects'),
              entrySource=_GetEntrySourceOrNone(args),
          ),
          parent=entry_ref.Parent().RelativeName(),
      )
  )

  log.CreatedResource(
      entry_ref.Name(),
      details='in [{0}]'.format(entry_ref.Parent().RelativeName()),
  )
  return resource


def Update(
    args: parser_extensions.Namespace,
    remove_aspects_arg_name: str = 'remove_aspects',
    update_aspects_arg_name: str = 'update_aspects',
):
  """Create an UpdateEntry request based on arguments provided."""

  update_mask = _GetFieldsForUpdateMask(args)
  if len(update_mask) < 1:
    raise exceptions.HttpException(
        'Update commands must specify at least one additional parameter to'
        ' change.'
    )

  entry_ref = args.CONCEPTS.entry.Parse()
  dataplex_client = dataplex_api.GetClientInstance()

  resource = dataplex_client.projects_locations_entryGroups_entries.Patch(
      dataplex_message.DataplexProjectsLocationsEntryGroupsEntriesPatchRequest(
          name=entry_ref.RelativeName(),
          googleCloudDataplexV1Entry=dataplex_message.GoogleCloudDataplexV1Entry(
              name=entry_ref.RelativeName(),
              fullyQualifiedName=_GetArgValueOrNone(
                  args, 'fully_qualified_name'
              ),
              aspects=_GetArgValueOrNone(args, update_aspects_arg_name),
              entrySource=_GetEntrySourceOrNone(args),
          ),
          deleteMissingAspects=args.IsKnownAndSpecified(
              remove_aspects_arg_name
          ),
          updateMask=','.join(update_mask),
          aspectKeys=_GenerateAspectKeys(
              args,
              remove_aspects_arg_name=remove_aspects_arg_name,
              update_aspects_arg_name=update_aspects_arg_name,
          ),
      )
  )

  log.UpdatedResource(entry_ref.RelativeName(), kind='entry')
  return resource
