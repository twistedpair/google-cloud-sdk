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

Tested through surface/transfer/jobs/create_test.py.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import enum

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.transfer import creds_util
from googlecloudsdk.command_lib.transfer import name_util
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times

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
    'Publicly-accessible objects:\n'
    '- URL list of objects - http://example.com/tsvfile')
_DESTINATION_HELP_TEXT = (
    'The destination for your data in Google Cloud Storage, specified'
    ' by bucket name and, if transferring to a folder, any subsequent'
    ' path to the folder. E.g., gs://example-bucket/example-folder')


class OverwriteOption(enum.Enum):
  DIFFERENT = 'different'
  ALWAYS = 'always'


class DeleteOption(enum.Enum):
  DESTINATION_IF_UNIQUE = 'destination-if-unique'
  SOURCE_AFTER_TRANSFER = 'source-after-transfer'


def _get_transfer_options(args, messages):
  """Returns TransferOptions object from args."""
  if not (args.overwrite_when or args.delete_from):
    return None

  return messages.TransferOptions(
      overwriteObjectsAlreadyExistingInSink=(OverwriteOption(
          args.overwrite_when) is OverwriteOption.ALWAYS),
      deleteObjectsFromSourceAfterTransfer=(DeleteOption(args.delete_from) is
                                            DeleteOption.SOURCE_AFTER_TRANSFER),
      deleteObjectsUniqueInSink=(DeleteOption(args.delete_from) is
                                 DeleteOption.DESTINATION_IF_UNIQUE),
  )


def _get_object_conditions(args, messages):
  """Returns ObjectConditins from args."""
  if not (args.include_prefixes or args.exclude_prefixes or
          args.include_modified_before_absolute or
          args.include_modified_after_absolute or
          args.include_modified_before_relative or
          args.include_modified_after_relative):
    return None
  object_conditions = messages.ObjectConditions()
  if args.include_prefixes:
    object_conditions.includePrefixes = args.include_prefixes
  if args.exclude_prefixes:
    object_conditions.excludePrefixes = args.exclude_prefixes
  if args.include_modified_before_absolute:
    modified_before_datetime_string = (
        args.include_modified_before_absolute.astimezone(times.UTC).isoformat())
    object_conditions.lastModifiedBefore = modified_before_datetime_string
  if args.include_modified_after_absolute:
    modified_after_datetime_string = (
        args.include_modified_after_absolute.astimezone(times.UTC).isoformat())
    object_conditions.lastModifiedSince = modified_after_datetime_string
  if args.include_modified_before_relative:
    object_conditions.minTimeElapsedSinceLastModification = '{}s'.format(
        args.include_modified_before_relative)
  if args.include_modified_after_relative:
    object_conditions.maxTimeElapsedSinceLastModification = '{}s'.format(
        args.include_modified_after_relative)
  return object_conditions


def _get_transfer_spec(args, messages):
  """Returns TransferSpec object from args."""
  destination_url = storage_url.storage_url_from_string(args.destination)
  transfer_spec = messages.TransferSpec(
      gcsDataSink=messages.GcsData(
          bucketName=destination_url.bucket_name,
          path=destination_url.object_name,
      ),
      objectConditions=_get_object_conditions(args, messages),
      transferOptions=_get_transfer_options(args, messages))

  try:
    source_url = storage_url.storage_url_from_string(args.source)
  except errors.InvalidUrlError:
    if args.source.startswith(storage_url.ProviderPrefix.HTTP.value):
      transfer_spec.httpDataSource = messages.HttpData(listUrl=args.source)
      source_url = None
    else:
      raise

  if source_url:
    if source_url.scheme is storage_url.ProviderPrefix.GCS:
      transfer_spec.gcsDataSource = messages.GcsData(
          bucketName=source_url.bucket_name,
          path=source_url.object_name,
      )
    elif source_url.scheme is storage_url.ProviderPrefix.S3:
      if args.source_creds_file:
        creds_dict = creds_util.get_values_for_keys_from_file(
            args.source_creds_file,
            ['aws_access_key_id', 'aws_secret_access_key'])
      else:
        creds_dict = creds_util.get_aws_creds()
      transfer_spec.awsS3DataSource = messages.AwsS3Data(
          awsAccessKey=messages.AwsAccessKey(
              accessKeyId=creds_dict.get('aws_access_key_id', None),
              secretAccessKey=creds_dict.get('aws_secret_access_key', None)),
          bucketName=source_url.bucket_name,
          path=source_url.object_name,
      )
    elif isinstance(source_url, storage_url.AzureUrl):
      if args.source_creds_file:
        sas_token = creds_util.get_values_for_keys_from_file(
            args.source_creds_file, ['sasToken'])['sasToken']
      else:
        sas_token = None
      transfer_spec.azureBlobStorageDataSource = (
          messages.AzureBlobStorageData(
              azureCredentials=messages.AzureCredentials(sasToken=sas_token),
              container=source_url.bucket_name,
              path=source_url.object_name,
              storageAccount=source_url.account,
          ))
  return transfer_spec


def _get_schedule(args, messages):
  """Returns transfer Schedule object from args."""
  if args.do_not_run:
    if (args.schedule_starts or args.schedule_repeats_every or
        args.schedule_repeats_until):
      raise ValueError('Cannot set schedule and do-not-run flag.')
    return None

  schedule = messages.Schedule()

  if args.schedule_starts:
    start = args.schedule_starts.astimezone(times.UTC)

    schedule.scheduleStartDate = messages.Date(
        day=start.day,
        month=start.month,
        year=start.year,
    )
    schedule.startTimeOfDay = messages.TimeOfDay(
        hours=start.hour,
        minutes=start.minute,
        seconds=start.second,
    )
  else:
    # By default, run job immediately.
    today_date = datetime.date.today()
    schedule.scheduleStartDate = messages.Date(
        day=today_date.day, month=today_date.month, year=today_date.year)

  if args.schedule_repeats_every:
    schedule.repeatInterval = '{}s'.format(args.schedule_repeats_every)
    # Default behavior of running job every 24 hours if field not set will be
    # blocked by args.schedule_repeats_until handling.

  if args.schedule_repeats_until:
    if not args.schedule_repeats_every:
      raise ValueError(
          'Scheduling a job end time requires setting a frequency with'
          ' --schedule-repeats-every. If no job end time is set, the job will'
          ' run one time.')
    end = args.schedule_repeats_until.astimezone(times.UTC)
    schedule.scheduleEndDate = messages.Date(
        day=end.day,
        month=end.month,
        year=end.year,
    )
    schedule.endTimeOfDay = messages.TimeOfDay(
        hours=end.hour,
        minutes=end.minute,
        seconds=end.second,
    )
  elif not args.schedule_repeats_every:
    # By default, run operation once.
    # If job frequency set, allow operation to repeat endlessly.
    schedule.scheduleEndDate = schedule.scheduleStartDate

  return schedule


def _get_notification_config(args, messages):
  """Returns transfer NotificationConfig object from args."""
  if not args.notification_pubsub_topic:
    if args.notification_event_types or args.notification_payload_format:
      raise ValueError('Cannot set notification config without'
                       ' --notification-pubsub-topic.')
    return None

  if args.notification_payload_format:
    payload_format_key = args.notification_payload_format.upper()
    payload_format = getattr(
        messages.NotificationConfig.PayloadFormatValueValuesEnum,
        payload_format_key)
  else:
    payload_format = (
        messages.NotificationConfig.PayloadFormatValueValuesEnum.JSON)

  if args.notification_event_types:
    event_types = []
    for event_type_arg in args.notification_event_types:
      event_type_key = 'TRANSFER_OPERATION_' + event_type_arg.upper()
      event_type = getattr(
          messages.NotificationConfig.EventTypesValueListEntryValuesEnum,
          event_type_key)
      event_types.append(event_type)
  else:
    event_types = [
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_SUCCESS),
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_FAILED),
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_ABORTED)
    ]

  return messages.NotificationConfig(
      eventTypes=event_types,
      pubsubTopic=args.notification_pubsub_topic,
      payloadFormat=payload_format)


def get_transfer_job_from_args(args):
  """Generates apitools TransferJob from command arguments."""
  messages = apis.GetMessagesModule('storagetransfer', 'v1')

  if args.name:
    formatted_job_name = name_util.add_job_prefix(args.name)
  else:
    formatted_job_name = None

  transfer_spec = _get_transfer_spec(args, messages)
  schedule = _get_schedule(args, messages)
  notification_config = _get_notification_config(args, messages)

  return messages.TransferJob(
      description=args.description,
      name=formatted_job_name,
      notificationConfig=notification_config,
      projectId=properties.VALUES.core.project.Get(),
      schedule=schedule,
      status=messages.TransferJob.StatusValueValuesEnum.ENABLED,
      transferSpec=transfer_spec)


def add_flags(parser, is_update=False):
  """Adds flags to job create and job update commands."""
  if is_update:
    parser.add_argument(
        'job_name', help="Name of the transfer job you'd like to update.")
  else:
    parser.add_argument('source', help=_SOURCE_HELP_TEXT)
    parser.add_argument('destination', help=_DESTINATION_HELP_TEXT)

  job_information = parser.add_group(help='JOB INFORMATION')
  if is_update:
    job_information.add_argument('source', help=_SOURCE_HELP_TEXT)
    job_information.add_argument('destination', help=_DESTINATION_HELP_TEXT)
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
      help='Path to local file that'
      ' includes relevant AWS or Azure credentials. Required only for jobs'
      ' with Amazon S3 buckets and Azure Storage containers as sources.'
      ' If not specified for an AWS transfer, will check default config '
      ' paths. For credential file formatting information, see:'
      ' http://cloud/storage-transfer/docs/reference/rest/v1/TransferSpec')

  schedule = parser.add_group(help='SCHEDULE')
  if is_update:
    schedule.add_argument(
        '--clear-schedule',
        action='store_true',
        help=(
            "Remove the job's entire schedule by clearing all scheduling flags."
            ' The job will no longer run unless an operation is manually'
            ' started or a new schedule is specified.'))
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
  schedule.add_argument(
      '--do-not-run',
      action='store_true',
      help='Disable default Transfer Service behavior of running job upon'
      ' creation if no schedule is set. If this flag is specified, the job'
      " won't run until an operation is manually started or a schedule is"
      ' added.')

  object_conditions = parser.add_group(help='OBJECT CONDITIONS')
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
        '--clear-modified-before-absolute',
        action='store_true',
        help='Remove the maximum modification datetime from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-modified-after-absolute',
        action='store_true',
        help='Remove the minimum modification datetime from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-modified-before-relative',
        action='store_true',
        help='Remove the maximum duration since modification from the'
        ' object conditions.')
    object_conditions.add_argument(
        '--clear-modified-after-relative',
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

  transfer_options = parser.add_group(help='TRANSFER OPTIONS')
  if is_update:
    transfer_options.add_argument(
        '--clear-delete-from',
        action='store_true',
        help='Remove a specified deletion option from the transfer job. If this'
        " flag is specified, the transfer job won't delete any data from"
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

  notification_config = parser.add_group(help='NOTIFICATION CONFIG')
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
    execution_options = parser.add_group(help='EXECUTION OPTIONS')
    execution_options.add_argument(
        '--no-async',
        action='store_true',
        help='For jobs set to run upon creation, this flag blocks other tasks'
        " in your terminal until the job's initial, immediate transfer"
        ' operation has completed. If not included, tasks will run'
        ' asynchronously.')
