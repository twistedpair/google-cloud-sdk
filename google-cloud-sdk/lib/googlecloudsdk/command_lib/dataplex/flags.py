# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Shared resource args for the Dataplex surface."""

from __future__ import absolute_import
from __future__ import annotations
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import parser_arguments
from googlecloudsdk.command_lib.dataplex import parsers as dataplex_parsers
from googlecloudsdk.command_lib.util.args import labels_util


def AddDiscoveryArgs(parser):
  """Adds Discovery Args to parser."""
  discovery_spec = parser.add_group(
      help='Settings to manage the metadata discovery and publishing.'
  )
  discovery_spec.add_argument(
      '--discovery-enabled',
      action=arg_parsers.StoreTrueFalseAction,
      help='Whether discovery is enabled.',
  )
  discovery_spec.add_argument(
      '--discovery-include-patterns',
      default=[],
      type=arg_parsers.ArgList(),
      metavar='INCLUDE_PATTERNS',
      help="""The list of patterns to apply for selecting data to include
        during discovery if only a subset of the data should considered. For
        Cloud Storage bucket assets, these are interpreted as glob patterns
        used to match object names. For BigQuery dataset assets, these are
        interpreted as patterns to match table names.""",
  )
  discovery_spec.add_argument(
      '--discovery-exclude-patterns',
      default=[],
      type=arg_parsers.ArgList(),
      metavar='EXCLUDE_PATTERNS',
      help="""The list of patterns to apply for selecting data to exclude
        during discovery. For Cloud Storage bucket assets, these are interpreted
        as glob patterns used to match object names. For BigQuery dataset
        assets, these are interpreted as patterns to match table names.""",
  )
  trigger = discovery_spec.add_group(
      help='Determines when discovery jobs are triggered.'
  )
  trigger.add_argument(
      '--discovery-schedule',
      help="""[Cron schedule](https://en.wikipedia.org/wiki/Cron) for running
                discovery jobs periodically. Discovery jobs must be scheduled at
                least 30 minutes apart.""",
  )
  discovery_prefix = discovery_spec.add_group(help='Describe data formats.')
  csv_option = discovery_prefix.add_group(
      help='Describe CSV and similar semi-structured data formats.'
  )
  csv_option.add_argument(
      '--csv-header-rows',
      type=int,
      help=(
          'The number of rows to interpret as header rows that should be'
          ' skipped when reading data rows.'
      ),
  )
  csv_option.add_argument(
      '--csv-delimiter',
      help="The delimiter being used to separate values. This defaults to ','.",
  )
  csv_option.add_argument(
      '--csv-encoding',
      help='The character encoding of the data. The default is UTF-8.',
  )
  csv_option.add_argument(
      '--csv-disable-type-inference',
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          'Whether to disable the inference of data type for CSV data. If true,'
          ' all columns will be registered as strings.'
      ),
  )
  json_option = discovery_prefix.add_group(help='Describe JSON data format.')
  json_option.add_argument(
      '--json-encoding',
      help='The character encoding of the data. The default is UTF-8.',
  )
  json_option.add_argument(
      '--json-disable-type-inference',
      action=arg_parsers.StoreTrueFalseAction,
      help=(
          ' Whether to disable the inference of data type for Json data. If'
          ' true, all columns will be registered as their primitive types'
          ' (strings, number or boolean).'
      ),
  )
  return discovery_spec


# Dataplex Entries
def AddEntrySourceArgs(
    parser: parser_arguments.ArgumentInterceptor, for_update: bool
):
  """Add entry source update args.

  Args:
    parser: The arg parser to add flags to.
    for_update: If True, then indicates that arguments are intended for Update
      command. In such case for each clearable argument there will be also
      `--clear-...` flag added in a mutually exclusive group to support clearing
      the field.
  """
  entry_source = parser.add_group(
      help=(
          'Source system related information for an entry. If any of the entry'
          ' source fields are specified, then ``--entry-source-update-time`'
          ' must be specified as well.'
      )
  )

  def AddArgument(name: str, **kwargs):
    parser_to_add = entry_source

    # Update command includes `--clear-...` flag, that should be in mutually
    # exclusive group, so either value is updated or cleared.
    if for_update:
      parser_to_add = entry_source.add_mutually_exclusive_group()
      parser_to_add.add_argument(
          '--clear-entry-source-' + name,
          action='store_true',
          help=(
              f"Clear the value for the {name.replace('-', '_')} field in the"
              ' Entry Source.'
          ),
      )

    parser_to_add.add_argument('--entry-source-' + name, **kwargs)

  AddArgument(
      'resource',
      help='The name of the resource in the source system.',
      metavar='RESOURCE',
  )
  AddArgument(
      'system',
      help='The name of the source system.',
      metavar='SYSTEM_NAME',
  )
  AddArgument(
      'platform',
      help='The platform containing the source system.',
      metavar='PLATFORM_NAME',
  )
  AddArgument(
      'display-name',
      help='User friendly display name.',
      metavar='DISPLAY_NAME',
  )
  AddArgument(
      'description',
      help='Description of the Entry.',
      metavar='DESCRIPTION',
  )
  AddArgument(
      'create-time',
      help='The creation date and time of the resource in the source system.',
      type=dataplex_parsers.IsoDateTime,
      metavar='DATE_TIME',
  )

  # Handle labels using built-in utils.
  entry_source_labels_container = entry_source
  if for_update:
    entry_source_labels_container = entry_source.add_mutually_exclusive_group()
    clear_flag = labels_util.GetClearLabelsFlag(
        labels_name='entry-source-labels'
    ).AddToParser(entry_source_labels_container)
    clear_flag.help = 'Clear the labels for the Entry Source.'

  labels_util.GetCreateLabelsFlag(
      labels_name='entry-source-labels'
  ).AddToParser(entry_source_labels_container)

  if not for_update:
    entry_source.add_argument(
        '--entry-source-ancestors',
        help='Information about individual items in the hierarchy of an Entry.',
        type=arg_parsers.ArgList(includes_json=True),
        metavar='ANCESTORS',
    )

  # Update time is marked as required and is on a level above from other flags.
  # If any other flag (e.g. `--entry-source-system`) will be specified, then
  # the user will have to provide update time as well.
  entry_source.add_argument(
      '--entry-source-update-time',
      help='The update date and time of the resource in the source system.',
      type=dataplex_parsers.IsoDateTime,
      required=for_update,
      metavar='DATE_TIME',
  )


def AddAspectFlags(
    parser: parser_arguments.ArgumentInterceptor,
    *,
    update_aspects_name: str | None = 'update-aspects',
    remove_aspects_name: str | None = 'remove-aspects',
    required: bool = False,
):
  """Adds flags for updating and removing Aspects.

  Args:
    parser: The arg parser to add flags to.
    update_aspects_name: Name of the flag to add for updating Aspects or None if
      no flag should be added.
    remove_aspects_name: Name of the flag to add for removing Aspects or None if
      no flag should be added.
    required: If True, then flags will be marked as required.
  """
  combination_help_text = ''
  if update_aspects_name is not None and remove_aspects_name is not None:
    combination_help_text = f"""

        If both `--{update_aspects_name}` and `--{remove_aspects_name}` flags
        are specified, and the same aspect key is used in both flags, then
        `--{update_aspects_name}` takes precedence, and such an aspect will be
        updated and not removed.
    """

  if update_aspects_name is not None:
    parser.add_argument(
        f'--{update_aspects_name}',
        help="""
        Path to a YAML or JSON file containing Aspects to add or update.

        When this flag is specified, only Aspects referenced in the file are
        going to be added or updated. Specifying this flag does not remove any
        Aspects from the entry. In other words, specifying this flag will not
        lead to a full replacement of Aspects with a contents of the provided
        file.

        Content of the file contains a map, where keys are in the format
        ``ASPECT_TYPE@PATH'', or just ``ASPECT_TYPE'', if the Aspect is attached
        to an entry itself rather than to a specific column defined in the
        schema.

        Values in the map represent Aspect's content, which must conform to a
        template defined for a given ``ASPECT_TYPE''. Each Aspect will be replaced
        fully by the provided content. That means data in the Aspect will be
        replaced and not merged with existing contents of that Aspect in the Entry.

        ``ASPECT_TYPE'' is expected to be in a format
        ``PROJECT_ID.LOCATION.ASPECT_TYPE_ID''.

        ``PATH'' can be either empty (which means a 'root' path, such that Aspect
        is attached to the entry itself) or point to a specific column defined
        in the schema. For example: `Schema.some_column`.

        Example YAML format:

        ```
          project-id1.us-central1.my-aspect-type1:
            data:
              aspectField1: someValue
              aspectField2: someOtherValue
          project-id2.us-central1.my-aspect-type2@Schema.column1:
            data:
              aspectField3: someValue3
        ```

        Example JSON format:

        ```
          {
            "project-id1.us-central1.my-aspect-type1": {
              "data": {
                "aspectField1": "someValue",
                "aspectField2": "someOtherValue"
              }
            },
            "project-id2.us-central1.my-aspect-type2@Schema.column1": {
              "data": {
                "aspectField3": "someValue3"
              }
            }
          }
        ```
        """ + combination_help_text,
        type=dataplex_parsers.ParseAspects,
        metavar='YAML_OR_JSON_FILE',
        required=required,
    )

  if remove_aspects_name is not None:
    parser.add_argument(
        f'--{remove_aspects_name}',
        help="""
        List of Aspect keys, identifying Aspects to remove from the entry.

        Keys are in the format ``ASPECT_TYPE@PATH'', or just ``ASPECT_TYPE'', if
        the Aspect is attached to an entry itself rather than to a specific
        column defined in the schema.

        ``ASPECT_TYPE'' is expected to be in a format
        ``PROJECT_ID.LOCATION.ASPECT_TYPE_ID'' or a wildcard `*`, which targets
        all aspect types.

        ``PATH'' can be either empty (which means a 'root' path, such that
        Aspect is attached to the entry itself), point to a specific column
        defined in the schema (for example: `Schema.some_column`) or a wildcard
        `*` (target all paths).

        ``ASPECT_TYPE'' and ``PATH'' cannot be both specified as wildcards `*`."""
        + combination_help_text,
        type=arg_parsers.ArgList(),
        metavar='ASPECT_TYPE@PATH',
        required=required,
    )


def AddEntryLinkAspectFlags(
    parser: parser_arguments.ArgumentInterceptor,
    *,
    update_aspects_name: str | None = 'update-aspects',
    required: bool = False,
):
  """Adds flags for updating Aspects for EntryLinks.

  Args:
    parser: The arg parser to add flags to.
    update_aspects_name: Name of the flag to add for updating Aspects or None if
      no flag should be added.
    required: If True, then flags will be marked as required.
  """
  if update_aspects_name is not None:
    parser.add_argument(
        f'--{update_aspects_name}',
        help="""
        Path to a YAML or JSON file containing Aspects to add or update for the EntryLink.

        When this flag is specified, only Aspects referenced in the file are
        going to be added or updated. This does not remove other Aspects from the EntryLink.

        The file content must be a map where keys are in the format ``ASPECT_TYPE''.
        Paths are not allowed in the keys for EntryLink aspects.

        Values in the map represent the Aspect's content, which must conform to the
        template defined for the given ``ASPECT_TYPE''. Each Aspect is fully replaced.

        ``ASPECT_TYPE'' must be in the format ``PROJECT_ID.LOCATION.ASPECT_TYPE_ID''.

        Example YAML format:

        ```
          project-id1.us-central1.my-aspect-type1:
            data:
              aspectField1: someValue
              aspectField2: someOtherValue
        ```
        """,
        type=dataplex_parsers.ParseEntryLinkAspects,  # Use the EntryLink parser
        metavar='YAML_OR_JSON_FILE',
        required=required,
    )
