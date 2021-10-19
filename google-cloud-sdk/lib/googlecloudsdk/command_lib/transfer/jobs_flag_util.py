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
"""Utils for managng the many transfer job flags.

Tested more through command surface tests.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

from googlecloudsdk.calliope import arg_parsers

_SOURCE_HELP_TEXT = (
    'The source of your data, typically specified by a scheme to show source'
    ' (e.g., gs:// for a Google Cloud Storage bucket);'
    ' name of the resource (e.g., bucket or container name);'
    ' and, if transferring from a folder, the path to the folder.'
    ' Example formatting:\n\n'
    'Public clouds:\n'
    '- Google Cloud Storage - gs://example-bucket/example-folder\n'
    '- Amazon S3 - s3://examplebucket/example-folder\n'
    '- Azure Storage - http://examplestorageaccount.blob.core.windows.net/'
    'examplecontainer/examplefolder\n\n'
    'POSIX filesystem - Specify the `posix://` scheme followed by the full path'
    " to the desired directory. Format the path relative to the agents' mount"
    ' point in the filesystem, not based on where the desired directory is in'
    ' the machine running gcloud. For example:\n\n'
    '- posix://example/path/to/directory/\n\n'
    'Publicly-accessible objects:\n'
    '- URL list of objects - http://example.com/tsvfile')
_DESTINATION_HELP_TEXT = (
    'The destination for your data in Google Cloud Storage, specified'
    ' by bucket name and, if transferring to a folder, any subsequent'
    ' path to the folder. E.g., gs://example-bucket/example-folder')


class DeleteOption(enum.Enum):
  DESTINATION_IF_UNIQUE = 'destination-if-unique'
  SOURCE_AFTER_TRANSFER = 'source-after-transfer'


class JobStatus(enum.Enum):
  ENABLED = 'enabled'
  DISABLED = 'disabled'
  DELETED = 'deleted'


class OverwriteOption(enum.Enum):
  DIFFERENT = 'different'
  ALWAYS = 'always'


def setup_parser(parser, is_update=False):
  """Adds flags to job create and job update commands."""
  # Flags and arg groups appear in help text in the order they are added here.
  # The order was designed by UX, so please do not modify.
  parser.SetSortArgs(False)
  if is_update:
    parser.add_argument(
        'name', help="Name of the transfer job you'd like to update.")
  else:
    parser.add_argument('source', help=_SOURCE_HELP_TEXT)
    parser.add_argument('destination', help=_DESTINATION_HELP_TEXT)

  job_information = parser.add_group(help='JOB INFORMATION', sort_args=False)
  if is_update:
    job_information.add_argument(
        '--status',
        choices=[status.value for status in JobStatus],
        help='Specify this flag to change the status of the job. Options'
        " include 'enabled', 'disabled', 'deleted'.")
    job_information.add_argument('--source', help=_SOURCE_HELP_TEXT)
    job_information.add_argument('--destination', help=_DESTINATION_HELP_TEXT)
    job_information.add_argument(
        '--clear-description',
        action='store_true',
        help='Remove the description from the transfer job.')
    job_information.add_argument(
        '--clear-source-creds-file',
        action='store_true',
        help='Remove the source creds file from the transfer job.')
  else:
    job_information.add_argument(
        '--name',
        help='A unique identifier for the job. Referring to your source and'
        ' destination is recommended. If left blank, the name is'
        ' auto-generated upon submission of the job.')
  job_information.add_argument(
      '--description',
      help='An optional description to help identify the job using details'
      " that don't fit in its name.")
  job_information.add_argument(
      '--source-creds-file',
      help='Path to a local file on your machine that includes credentials'
      ' for an Amazon S3 or Azure Blob Storage source (not required for'
      ' Google Cloud Storage sources). If not specified for an S3 source,'
      ' gcloud will check your system for an AWS config file. For'
      ' formatting, see:\n\n'
      'S3: https://cloud.google.com/storage-transfer/docs/reference/'
      'rest/v1/TransferSpec#AwsAccessKey\n'
      'Azure: http://cloud/storage-transfer/docs/reference/rest/'
      'v1/TransferSpec#AzureCredentials')

  schedule = parser.add_group(
      help=("SCHEDULE\n\nA job's schedule determines when and how often the job"
            ' will run. For formatting information, see'
            ' https://cloud.google.com/sdk/gcloud/reference/topic/datetimes.'),
      sort_args=False)
  if is_update:
    schedule.add_argument(
        '--clear-schedule',
        action='store_true',
        help=("Remove the job's entire schedule by clearing all scheduling"
              ' flags. The job will no longer run unless an operation is'
              ' manually started or a new schedule is specified.'))
  else:
    schedule.add_argument(
        '--do-not-run',
        action='store_true',
        help='Disable default Transfer Service behavior of running job upon'
        ' creation if no schedule is set. If this flag is specified, the job'
        " won't run until an operation is manually started or a schedule is"
        ' added.')
  schedule.add_argument(
      '--schedule-starts',
      type=arg_parsers.Datetime.Parse,
      help='Set when the job will start using the %Y-%m-%dT%H:%M:%S%z'
      ' datetime format (e.g., 2020-04-12T06:42:12+04:00). If not set,'
      ' the job will run upon the successful submission of the create'
      ' job command unless the --do-not-run flag is included.')
  schedule.add_argument(
      '--schedule-repeats-every',
      type=arg_parsers.Duration(),
      help='Set the frequency of the job using the absolute duration'
      ' format (e.g., 1 month is p1m; 1 hour 30 minutes is 1h30m). If'
      ' not set, the job will run once.')
  schedule.add_argument(
      '--schedule-repeats-until',
      type=arg_parsers.Datetime.Parse,
      help='Set when the job will stop recurring using the'
      ' %Y-%m-%dT%H:%M:%S%z datetime format (e.g.,'
      ' 2020-04-12T06:42:12+04:00). If specified, you must also include a'
      ' value for the --schedule-repeats-every flag. If not specified, the'
      ' job will continue to repeat as specified in its repeat-every field'
      ' unless the job is manually disabled or you add this field later.')

  object_conditions = parser.add_group(
      help=(
          'OBJECT CONDITIONS\n\nA set of conditions to determine which objects'
          ' are transferred. For time-based object condition formatting tips,'
          ' see https://cloud.google.com/sdk/gcloud/reference/topic/datetimes.'
          ' Note: If you specify multiple conditions, objects must have at'
          " least one of the specified 'include' prefixes and all of the"
          " specified time conditions. If an object has an 'exclude' prefix, it"
          ' will be excluded even if it matches other conditions.'),
      sort_args=False)
  if is_update:
    object_conditions.add_argument(
        '--clear-include-prefixes',
        action='store_true',
        help='Remove the list of object prefixes to include from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-exclude-prefixes',
        action='store_true',
        help='Remove the list of object prefixes to exclude from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-include-modified-before-absolute',
        action='store_true',
        help='Remove the maximum modification datetime from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-include-modified-after-absolute',
        action='store_true',
        help='Remove the minimum modification datetime from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-include-modified-before-relative',
        action='store_true',
        help='Remove the maximum duration since modification from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-include-modified-after-relative',
        action='store_true',
        help='Remove the minimum duration since modification from the'
        ' object conditions.')
  object_conditions.add_argument(
      '--include-prefixes',
      type=arg_parsers.ArgList(),
      metavar='INCLUDED_PREFIXES',
      help='Include only objects that start with the specified prefix(es).'
      ' Separate multiple prefixes with commas, omitting spaces after'
      ' the commas (e.g., --include-prefixes=foo,bar).')
  object_conditions.add_argument(
      '--exclude-prefixes',
      type=arg_parsers.ArgList(),
      metavar='EXCLUDED_PREFIXES',
      help='Exclude any objects that start with the prefix(es) entered.'
      ' Separate multiple prefixes with commas, omitting spaces after'
      ' the commas (e.g., --exclude-prefixes=foo,bar).')
  object_conditions.add_argument(
      '--include-modified-before-absolute',
      type=arg_parsers.Datetime.Parse,
      help='Include objects last modified before an absolute date/time. Ex.'
      " by specifying '2020-01-01', the transfer would include objects"
      ' last modified before January 1, 2020. Use the'
      ' %Y-%m-%dT%H:%M:%S%z datetime format.')
  object_conditions.add_argument(
      '--include-modified-after-absolute',
      type=arg_parsers.Datetime.Parse,
      help='Include objects last modified after an absolute date/time. Ex.'
      " by specifying '2020-01-01', the transfer would include objects"
      ' last modified after January 1, 2020. Use the'
      ' %Y-%m-%dT%H:%M:%S%z datetime format.')
  object_conditions.add_argument(
      '--include-modified-before-relative',
      type=arg_parsers.Duration(),
      help='Include objects that were modified before a relative date/time in'
      " the past. Ex. by specifying a duration of '10d', the transfer"
      ' would include objects last modified *more than* 10 days before'
      ' its start time. Use the absolute duration format (ex. 1m for 1'
      ' month; 1h30m for 1 hour 30 minutes).')
  object_conditions.add_argument(
      '--include-modified-after-relative',
      type=arg_parsers.Duration(),
      help='Include objects that were modified after a relative date/time in'
      " the past. Ex. by specifying a duration of '10d', the transfer"
      ' would include objects last modified *less than* 10 days before'
      ' its start time. Use the absolute duration format (ex. 1m for 1'
      ' month; 1h30m for 1 hour 30 minutes).')

  transfer_options = parser.add_group(help='TRANSFER OPTIONS', sort_args=False)
  if is_update:
    transfer_options.add_argument(
        '--clear-delete-from',
        action='store_true',
        help='Remove a specified deletion option from the transfer job. If '
        " this flag is specified, the transfer job won't delete any data from"
        ' your source or destination.')
  transfer_options.add_argument(
      '--overwrite-when',
      choices=[option.value for option in OverwriteOption],
      help='Determine when destination objects are overwritten by source'
      ' objects. Options include:\n'
      " - 'different' - Overwrites files with the same name if the contents"
      " are different (e.g., if etags or checksums don't match)\n"
      " - 'always' - Overwrite destination file whenever source file has the"
      " same name -- even if they're identical")
  transfer_options.add_argument(
      '--delete-from',
      choices=[option.value for option in DeleteOption],
      help="By default, transfer jobs won't delete any data from your source"
      ' or destination. These options enable you to delete data if'
      ' needed for your use case. Options include:\n'
      " - 'destination-if-unique' - Delete files from destination if they're"
      ' not also at source. Use to sync destination to source (i.e., make'
      ' destination match source exactly)\n'
      " - 'source-after-transfer' - Delete files from source after they're"
      ' transferred')

  notification_config = parser.add_group(
      help=(
          'NOTIFICATION CONFIG\n\nA configuration for receiving notifications of'
          'transfer operation status changes via Cloud Pub/Sub.'),
      sort_args=False)
  if is_update:
    notification_config.add_argument(
        '--clear-notification-config',
        action='store_true',
        help="Remove the job's full notification configuration to no"
        ' longer receive notifications via Cloud Pub/Sub.')
    notification_config.add_argument(
        '--clear-notification-event-types',
        action='store_true',
        help='Remove the event types from the notification config.')
  notification_config.add_argument(
      '--notification-pubsub-topic',
      help='Pub/Sub topic used for notifications.')
  notification_config.add_argument(
      '--notification-event-types',
      type=arg_parsers.ArgList(choices=['success', 'failed', 'aborted']),
      metavar='EVENT_TYPES',
      help='Define which change of transfer operation status will trigger'
      " Pub/Sub notifications. Choices include 'success', 'failed',"
      " 'aborted'. To trigger notifications for all three status changes,"
      " you can leave this flag unspecified as long as you've specified"
      ' a topic for the --notification-pubsub-topic flag.')
  notification_config.add_argument(
      '--notification-payload-format',
      choices=['json', 'none'],
      help="If 'none', no transfer operation details are included with"
      " notifications. If 'json', a json representation of the relevant"
      ' transfer operation is included in notification messages (e.g., to'
      ' see errors after an operation fails).')

  if not is_update:
    execution_options = parser.add_group(
        help='EXECUTION OPTIONS', sort_args=False)
    execution_options.add_argument(
        '--no-async',
        action='store_true',
        help='For jobs set to run upon creation, this flag blocks other tasks'
        " in your terminal until the job's initial, immediate transfer"
        ' operation has completed. If not included, tasks will run'
        ' asynchronously.')
