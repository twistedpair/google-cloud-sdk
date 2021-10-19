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

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.transfer import creds_util
from googlecloudsdk.command_lib.transfer import jobs_flag_util
from googlecloudsdk.command_lib.transfer import name_util
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import times


def _create_or_modify_transfer_options(transfer_spec, args, messages):
  """Creates or modifies TransferOptions object based on args."""
  if not (args.overwrite_when or args.delete_from):
    return
  if not transfer_spec.transferOptions:
    transfer_spec.transferOptions = messages.TransferOptions()

  if args.overwrite_when and jobs_flag_util.OverwriteOption(
      args.overwrite_when) is jobs_flag_util.OverwriteOption.ALWAYS:
    transfer_spec.transferOptions.overwriteObjectsAlreadyExistingInSink = True

  if args.delete_from:
    delete_option = jobs_flag_util.DeleteOption(args.delete_from)
    if delete_option is jobs_flag_util.DeleteOption.SOURCE_AFTER_TRANSFER:
      transfer_spec.transferOptions.deleteObjectsFromSourceAfterTransfer = True
    elif delete_option is jobs_flag_util.DeleteOption.DESTINATION_IF_UNIQUE:
      transfer_spec.transferOptions.deleteObjectsUniqueInSink = True


def _create_or_modify_object_conditions(transfer_spec, args, messages):
  """Creates or modifies ObjectConditions based on args."""
  if not (args.include_prefixes or args.exclude_prefixes or
          args.include_modified_before_absolute or
          args.include_modified_after_absolute or
          args.include_modified_before_relative or
          args.include_modified_after_relative):
    return
  if not transfer_spec.objectConditions:
    transfer_spec.objectConditions = messages.ObjectConditions()

  if args.include_prefixes:
    transfer_spec.objectConditions.includePrefixes = args.include_prefixes
  if args.exclude_prefixes:
    transfer_spec.objectConditions.excludePrefixes = args.exclude_prefixes
  if args.include_modified_before_absolute:
    modified_before_datetime_string = (
        args.include_modified_before_absolute.astimezone(times.UTC).isoformat())
    transfer_spec.objectConditions.lastModifiedBefore = modified_before_datetime_string
  if args.include_modified_after_absolute:
    modified_after_datetime_string = (
        args.include_modified_after_absolute.astimezone(times.UTC).isoformat())
    transfer_spec.objectConditions.lastModifiedSince = modified_after_datetime_string
  if args.include_modified_before_relative:
    transfer_spec.objectConditions.minTimeElapsedSinceLastModification = '{}s'.format(
        args.include_modified_before_relative)
  if args.include_modified_after_relative:
    transfer_spec.objectConditions.maxTimeElapsedSinceLastModification = '{}s'.format(
        args.include_modified_after_relative)


def _create_or_modify_creds(transfer_spec, args, messages):
  """Creates or modifies TransferSpec source creds based on args."""
  if transfer_spec.awsS3DataSource:
    if args.source_creds_file:
      creds_dict = creds_util.get_values_for_keys_from_file(
          args.source_creds_file,
          ['aws_access_key_id', 'aws_secret_access_key'])
    else:
      log.warning('No --source-creds-file flag. Checking system config files'
                  ' for AWS credentials.')
      creds_dict = creds_util.get_aws_creds()

    aws_access_key = creds_dict.get('aws_access_key_id', None)
    secret_access_key = creds_dict.get('aws_secret_access_key', None)
    if not (aws_access_key and secret_access_key):
      log.warning('Missing AWS source creds.')

    creds_dict.get('aws_access_key_id', None)
    transfer_spec.awsS3DataSource.awsAccessKey = messages.AwsAccessKey(
        accessKeyId=aws_access_key, secretAccessKey=secret_access_key)

  elif transfer_spec.azureBlobStorageDataSource:
    if args.source_creds_file:
      sas_token = creds_util.get_values_for_keys_from_file(
          args.source_creds_file, ['sasToken'])['sasToken']
    else:
      log.warning('No Azure source creds set. Consider adding'
                  ' --source-creds-file flag.')
      sas_token = None
    transfer_spec.azureBlobStorageDataSource.azureCredentials = (
        messages.AzureCredentials(sasToken=sas_token))


def _create_or_modify_transfer_spec(job, args, messages):
  """Creates or modifies TransferSpec based on args."""
  if not job.transferSpec:
    job.transferSpec = messages.TransferSpec()

  if args.destination:
    destination_url = storage_url.storage_url_from_string(args.destination)
    job.transferSpec.gcsDataSink = messages.GcsData(
        bucketName=destination_url.bucket_name,
        path=destination_url.object_name,
    )
  if args.source:
    # Clear any existing data source to make space for new one.
    job.transferSpec.httpDataSource = None
    job.transferSpec.posixDataSource = None
    job.transferSpec.gcsDataSource = None
    job.transferSpec.awsS3DataSource = None
    job.transferSpec.azureBlobStorageDataSource = None

    try:
      source_url = storage_url.storage_url_from_string(args.source)
    except errors.InvalidUrlError:
      if args.source.startswith(storage_url.ProviderPrefix.HTTP.value):
        job.transferSpec.httpDataSource = messages.HttpData(listUrl=args.source)
        source_url = None
      else:
        raise

    if source_url:
      if source_url.scheme is storage_url.ProviderPrefix.POSIX:
        job.transferSpec.posixDataSource = messages.PosixFilesystem(
            rootDirectory=source_url.object_name)
      elif source_url.scheme is storage_url.ProviderPrefix.GCS:
        job.transferSpec.gcsDataSource = messages.GcsData(
            bucketName=source_url.bucket_name,
            path=source_url.object_name,
        )
      elif source_url.scheme is storage_url.ProviderPrefix.S3:
        job.transferSpec.awsS3DataSource = messages.AwsS3Data(
            bucketName=source_url.bucket_name,
            path=source_url.object_name,
        )
      elif isinstance(source_url, storage_url.AzureUrl):
        job.transferSpec.azureBlobStorageDataSource = (
            messages.AzureBlobStorageData(
                container=source_url.bucket_name,
                path=source_url.object_name,
                storageAccount=source_url.account,
            ))

  _create_or_modify_creds(job.transferSpec, args, messages)
  _create_or_modify_object_conditions(job.transferSpec, args, messages)
  _create_or_modify_transfer_options(job.transferSpec, args, messages)


def _create_or_modify_schedule(job, args, messages, is_update):
  """Creates or modifies transfer Schedule object based on args."""
  if not is_update and args.do_not_run:
    if (args.schedule_starts or args.schedule_repeats_every or
        args.schedule_repeats_until):
      raise ValueError('Cannot set schedule and do-not-run flag.')
    return
  if is_update and not (args.schedule_starts or args.schedule_repeats_every or
                        args.schedule_repeats_until):
    # Nothing needs modification.
    return
  if not job.schedule:
    job.schedule = messages.Schedule()

  if args.schedule_starts:
    start = args.schedule_starts.astimezone(times.UTC)

    job.schedule.scheduleStartDate = messages.Date(
        day=start.day,
        month=start.month,
        year=start.year,
    )
    job.schedule.startTimeOfDay = messages.TimeOfDay(
        hours=start.hour,
        minutes=start.minute,
        seconds=start.second,
    )
  elif not is_update:
    # By default, run job immediately on create.
    today_date = datetime.date.today()
    job.schedule.scheduleStartDate = messages.Date(
        day=today_date.day, month=today_date.month, year=today_date.year)

  if args.schedule_repeats_every:
    job.schedule.repeatInterval = '{}s'.format(args.schedule_repeats_every)
    # Default behavior of running job every 24 hours if field not set will be
    # blocked by args.schedule_repeats_until handling.

  if args.schedule_repeats_until:
    if not job.schedule.repeatInterval:
      raise ValueError(
          'Scheduling a job end time requires setting a frequency with'
          ' --schedule-repeats-every. If no job end time is set, the job will'
          ' run one time.')
    end = args.schedule_repeats_until.astimezone(times.UTC)
    job.schedule.scheduleEndDate = messages.Date(
        day=end.day,
        month=end.month,
        year=end.year,
    )
    job.schedule.endTimeOfDay = messages.TimeOfDay(
        hours=end.hour,
        minutes=end.minute,
        seconds=end.second,
    )
  elif not is_update and not job.schedule.repeatInterval:
    # By default, run operation once on create.
    # If job frequency set, allow operation to repeat endlessly.
    job.schedule.scheduleEndDate = job.schedule.scheduleStartDate


def _create_or_modify_notification_config(job, args, messages, is_update=False):
  """Creates or modifies transfer NotificationConfig object based on args."""
  if not (args.notification_pubsub_topic or args.notification_event_types or
          args.notification_payload_format):
    # Nothing to modify with.
    return

  if args.notification_pubsub_topic:
    if not job.notificationConfig:
      # Create config with required PubSub topic.
      job.notificationConfig = messages.NotificationConfig(
          pubsubTopic=args.notification_pubsub_topic)
    else:
      job.notificationConfig.pubsubTopic = args.notification_pubsub_topic

  if (args.notification_event_types or
      args.notification_payload_format) and not job.notificationConfig:
    raise ValueError('Cannot set notification config without'
                     ' --notification-pubsub-topic.')

  if args.notification_payload_format:
    payload_format_key = args.notification_payload_format.upper()
    job.notificationConfig.payloadFormat = getattr(
        messages.NotificationConfig.PayloadFormatValueValuesEnum,
        payload_format_key)
  elif not is_update:
    # New job default.
    job.notificationConfig.payloadFormat = (
        messages.NotificationConfig.PayloadFormatValueValuesEnum.JSON)

  if args.notification_event_types:
    event_types = []
    for event_type_arg in args.notification_event_types:
      event_type_key = 'TRANSFER_OPERATION_' + event_type_arg.upper()
      event_type = getattr(
          messages.NotificationConfig.EventTypesValueListEntryValuesEnum,
          event_type_key)
      event_types.append(event_type)
    job.notificationConfig.eventTypes = event_types
  elif not is_update:
    # New job default.
    job.notificationConfig.eventTypes = [
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_SUCCESS),
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_FAILED),
        (messages.NotificationConfig.EventTypesValueListEntryValuesEnum
         .TRANSFER_OPERATION_ABORTED)
    ]


def generate_patch_transfer_job_message(messages, job):
  """Generates Apitools patch message for transfer jobs."""
  project_id = job.projectId
  job.projectId = None

  if job.schedule == messages.Schedule():
    # Jobs returned by API are populated with their user-set schedule or an
    # empty schedule. Empty schedules cannot be re-submitted to the API.
    job.schedule = None

  return messages.StoragetransferTransferJobsPatchRequest(
      jobName=job.name,
      updateTransferJobRequest=messages.UpdateTransferJobRequest(
          projectId=project_id,
          transferJob=job,
          updateTransferJobFieldMask=(
              'description,notification_config,schedule,status,transfer_spec'),
      ))


def generate_transfer_job_message(args, messages, existing_job=None):
  """Generates Apitools transfer message based on command arguments."""
  if existing_job:
    job = existing_job
  else:
    job = messages.TransferJob()

  if not job.projectId:
    job.projectId = properties.VALUES.core.project.Get()

  if args.name:
    job.name = name_util.add_job_prefix(args.name)

  if args.description:
    job.description = args.description

  if existing_job:
    # Is job update instead of create.
    if args.status:
      status_key = args.status.upper()
      job.status = getattr(messages.TransferJob.StatusValueValuesEnum,
                           status_key)
  else:
    job.status = messages.TransferJob.StatusValueValuesEnum.ENABLED

  _create_or_modify_transfer_spec(job, args, messages)
  _create_or_modify_schedule(job, args, messages, is_update=bool(existing_job))
  _create_or_modify_notification_config(
      job, args, messages, is_update=bool(existing_job))

  if existing_job:
    return generate_patch_transfer_job_message(messages, job)
  return job
