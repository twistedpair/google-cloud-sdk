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
"""Clients for interacting with Storage Batch Operations."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.storage import storage_batch_operations_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import properties


# Backend has a limit of 500.
PAGE_SIZE = 500


def _get_parent_string(project, location):
  return "projects/{}/locations/{}".format(project, location)


class StorageBatchOperationsApi:
  """Client for Storage Batch Operations API."""

  def __init__(self):
    self.client = core_apis.GetClientInstance("storagebatchoperations", "v1")
    self.messages = core_apis.GetMessagesModule("storagebatchoperations", "v1")

  def _instantiate_job_with_source(
      self,
      bucket_name,
      manifest_location=None,
      included_object_prefixes=None,
      description=None,
      dry_run=False,
  ):
    """Instatiates a Job object using the source and description provided.

    Args:
      bucket_name (str): Bucket name that contains the source objects described
        by the manifest or prefix list.
      manifest_location (str): Absolute path to the manifest source file in a
        Google Cloud Storage bucket.
      included_object_prefixes (list[str]): list of object prefixes to describe
        the objects being transformed.
      description (str): Description of the job.
      dry_run (bool): If true, job will be created in dry run mode.

    Returns:
      A Job object.
    """
    # empty prefix list is still allowed and considered set.
    prefix_list_set = included_object_prefixes is not None
    if bool(manifest_location) == prefix_list_set:
      raise errors.StorageBatchOperationsApiError(
          "Exactly one of manifest-location or included-object-prefixes must be"
          " specified."
      )
    job = self.messages.Job(
        description=description,
    )
    if dry_run:
      job.dryRun = True
    if manifest_location:
      manifest_payload = self.messages.Manifest(
          manifestLocation=manifest_location,
      )
      job.bucketList = self.messages.BucketList(
          buckets=[
              self.messages.Bucket(
                  bucket=bucket_name,
                  manifest=manifest_payload,
              )
          ]
      )
    else:
      prefix_list = (
          storage_batch_operations_util.process_included_object_prefixes(
              included_object_prefixes
          )
      )
      job.bucketList = self.messages.BucketList(
          buckets=[
              self.messages.Bucket(
                  bucket=bucket_name,
                  prefixList=prefix_list,
              )
          ]
      )
    return job

  def _create_job(self, batch_job_name, job):
    """Creates a job by building a CreateJobRequest and calling Create.

    Args:
      batch_job_name (str): Resource name of the batch job.
      job: A Job object to create.

    Returns:
      A longrunning operation representing the batch job.
    """
    parent, job_id = (
        storage_batch_operations_util.get_job_id_and_parent_string_from_resource_name(
            batch_job_name
        )
    )
    create_job_request = (
        self.messages.StoragebatchoperationsProjectsLocationsJobsCreateRequest(
            job=job, jobId=job_id, parent=parent
        )
    )
    return self.client.projects_locations_jobs.Create(create_job_request)

  def _modify_job_put_object_hold(
      self,
      job,
      put_object_temporary_hold,
      put_object_event_based_hold,
  ):
    """Modifies a job to put object on hold."""
    job.putObjectHold = self.messages.PutObjectHold()
    if put_object_temporary_hold is not None:
      job.putObjectHold.temporaryHold = (
          self.messages.PutObjectHold.TemporaryHoldValueValuesEnum.SET
          if put_object_temporary_hold
          else self.messages.PutObjectHold.TemporaryHoldValueValuesEnum.UNSET
      )
    if put_object_event_based_hold is not None:
      job.putObjectHold.eventBasedHold = (
          self.messages.PutObjectHold.EventBasedHoldValueValuesEnum.SET
          if put_object_event_based_hold
          else self.messages.PutObjectHold.EventBasedHoldValueValuesEnum.UNSET
      )

  def _modify_job_rewrite_object(self, job, rewrite_object_dict):
    """Modifies a job to rewrite object and the specified metadata."""
    rewrite_object = self.messages.RewriteObject()
    if rewrite_object_dict.get("kms-key"):
      rewrite_object.kmsKey = rewrite_object_dict["kms-key"]
    job.rewriteObject = rewrite_object

  def _modify_job_put_metadata(self, job, put_metadata_dict):
    """Modifies a job to put metadata.

    Args:
      job: A Job object to modify.
      put_metadata_dict (dict): A dictionary of metadata fields and values to
        apply.

    Raises:
      errors.StorageBatchOperationsApiError: If an invalid value is provided
        for "retention-mode".
    """
    put_metadata = self.messages.PutMetadata()
    custom_metadata_value = self.messages.PutMetadata.CustomMetadataValue()
    object_retention = self.messages.ObjectRetention()
    is_object_retention_set = False
    # put_metadata_dict is garanteed to have at least one key-value pair.
    for key, value in put_metadata_dict.items():
      lower_key = key.casefold()
      if lower_key == "content-disposition":
        put_metadata.contentDisposition = value
      elif lower_key == "content-encoding":
        put_metadata.contentEncoding = value
      elif lower_key == "content-language":
        put_metadata.contentLanguage = value
      elif lower_key == "content-type":
        put_metadata.contentType = value
      elif lower_key == "cache-control":
        put_metadata.cacheControl = value
      elif lower_key == "custom-time":
        put_metadata.customTime = value
      elif lower_key == "retain-until":
        is_object_retention_set = True
        if value:
          object_retention.retainUntilTime = value
      elif lower_key == "retention-mode":
        is_object_retention_set = True
        if value:
          try:
            retention_mode_enum = (
                self.messages.ObjectRetention.RetentionModeValueValuesEnum(
                    value.upper()
                )
            )
            object_retention.retentionMode = retention_mode_enum
          except TypeError:
            valid_modes = (
                self.messages.ObjectRetention.RetentionModeValueValuesEnum.to_dict().keys()
            )
            raise errors.StorageBatchOperationsApiError(
                f"Invalid value for retention-mode: {value}. Must be one of"
                f" {valid_modes}."
            )
      else:
        custom_metadata_value.additionalProperties.append(
            self.messages.PutMetadata.CustomMetadataValue.AdditionalProperty(
                key=key, value=value
            )
        )
    if custom_metadata_value.additionalProperties:
      put_metadata.customMetadata = custom_metadata_value
    if is_object_retention_set:
      put_metadata.objectRetention = object_retention
    job.putMetadata = put_metadata

  def _modify_job_logging_config(self, job, log_actions, log_action_states):
    """Modifies a job to create logging config."""
    logging_config = self.messages.LoggingConfig()
    actions = []
    for action in log_actions:
      actions.append(
          getattr(
              logging_config.LogActionsValueListEntryValuesEnum, action.upper()
          )
      )
    logging_config.logActions = actions

    action_states = []
    for action_state in log_action_states:
      action_states.append(
          getattr(
              logging_config.LogActionStatesValueListEntryValuesEnum,
              action_state.upper(),
          )
      )
    logging_config.logActionStates = action_states
    job.loggingConfig = logging_config

  def create_batch_job(self, args, batch_job_name):
    """Creates a batch job based on command arguments."""
    job = self._instantiate_job_with_source(
        args.bucket,
        manifest_location=args.manifest_location,
        included_object_prefixes=args.included_object_prefixes,
        description=args.description,
        dry_run=getattr(args, "dry_run", False),
    )
    if (
        args.put_object_temporary_hold is not None
        or args.put_object_event_based_hold is not None
    ):
      self._modify_job_put_object_hold(
          job, args.put_object_temporary_hold, args.put_object_event_based_hold
      )
    elif args.delete_object:
      job.deleteObject = self.messages.DeleteObject(
          permanentObjectDeletionEnabled=args.enable_permanent_object_deletion,
      )
    elif args.rewrite_object:
      self._modify_job_rewrite_object(job, args.rewrite_object)
    elif args.put_metadata:
      self._modify_job_put_metadata(job, args.put_metadata)
    else:
      raise errors.StorageBatchOperationsApiError(
          "Exactly one transformaiton must be specified."
      )

    if args.log_actions and args.log_action_states:
      self._modify_job_logging_config(
          job, args.log_actions, args.log_action_states
      )
    elif args.log_actions or args.log_action_states:
      raise errors.StorageBatchOperationsApiError(
          "Both --log-actions and --log-action-states are required for a"
          " complete log config."
      )
    return self._create_job(batch_job_name, job)

  def get_batch_job(self, batch_job_name):
    """Gets a batch job by resource name."""
    return self.client.projects_locations_jobs.Get(
        self.messages.StoragebatchoperationsProjectsLocationsJobsGetRequest(
            name=batch_job_name
        )
    )

  def delete_batch_job(self, batch_job_name):
    """Deletes a batch job by resource name."""
    return self.client.projects_locations_jobs.Delete(
        self.messages.StoragebatchoperationsProjectsLocationsJobsDeleteRequest(
            name=batch_job_name
        )
    )

  def list_batch_jobs(self, location=None, limit=None, page_size=None):
    if location:
      parent_string = _get_parent_string(
          properties.VALUES.core.project.Get(), location
      )
    else:
      parent_string = _get_parent_string(
          properties.VALUES.core.project.Get(), "-"
      )
    return list_pager.YieldFromList(
        self.client.projects_locations_jobs,
        self.messages.StoragebatchoperationsProjectsLocationsJobsListRequest(
            parent=parent_string,
        ),
        batch_size=page_size if page_size else PAGE_SIZE,
        batch_size_attribute="pageSize",
        limit=limit,
        field="jobs",
    )

  def cancel_batch_job(self, batch_job_name):
    """Cancels a batch job by resource name."""
    return self.client.projects_locations_jobs.Cancel(
        self.messages.StoragebatchoperationsProjectsLocationsJobsCancelRequest(
            name=batch_job_name
        )
    )
