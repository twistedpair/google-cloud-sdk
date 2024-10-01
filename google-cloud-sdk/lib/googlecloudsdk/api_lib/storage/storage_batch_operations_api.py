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
      manifest_location=None,
      prefix_list_file=None,
      description=None,
  ):
    """Instatiates a Job object using the source and description provided.

    Args:
      manifest_location (str): Absolute path to the manifest source file in a
        Google Cloud Storage bucket.
      prefix_list_file (str): Path to a local JSON or YAML file containing a
        list of prefixes.
      description (str): Description of the job.

    Returns:
      A Job object.
    """
    if bool(manifest_location) == bool(prefix_list_file):
      raise errors.StorageBatchOperationsApiError(
          "Exactly one of manifest-location or prefix-list-file must be"
          " specified."
      )
    job = self.messages.Job(
        description=description,
    )
    if manifest_location:
      job.manifest = self.messages.Manifest(
          manifestLocation=manifest_location,
      )
    else:
      job.prefixList = storage_batch_operations_util.process_prefix_list_file(
          prefix_list_file
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

  def _modify_job_put_metadata(self, job, put_metadata_dict):
    """Modifies a job to put metadata."""
    put_metadata = self.messages.PutMetadata()
    custom_metadata_value = self.messages.PutMetadata.CustomMetadataValue()
    # put_metadata_dict is garanteed to have at least one key-value pair.
    for key, value in put_metadata_dict.items():
      if key.casefold() == "content-disposition":
        put_metadata.contentDisposition = value
      elif key.casefold() == "content-encoding":
        put_metadata.contentEncoding = value
      elif key.casefold() == "content-language":
        put_metadata.contentLanguage = value
      elif key.casefold() == "content-type":
        put_metadata.contentType = value
      elif key.casefold() == "cache-control":
        put_metadata.cacheControl = value
      elif key.casefold() == "custom-time":
        put_metadata.customTime = value
      else:
        custom_metadata_value.additionalProperties.append(
            self.messages.PutMetadata.CustomMetadataValue.AdditionalProperty(
                key=key, value=value
            )
        )
    if custom_metadata_value.additionalProperties:
      put_metadata.customMetadata = custom_metadata_value
    job.putMetadata = put_metadata

  def create_batch_job(self, args, batch_job_name):
    """Creates a batch job based on command arguments."""
    job = self._instantiate_job_with_source(
        manifest_location=args.manifest_location,
        prefix_list_file=args.prefix_list_file,
        description=args.description,
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
    elif args.put_kms_key:
      job.putKmsKey = self.messages.PutKmsKey(kmsKey=args.put_kms_key)
    elif args.put_metadata:
      self._modify_job_put_metadata(job, args.put_metadata)
    else:
      raise errors.StorageBatchOperationsApiError(
          "Exactly one transformaiton must be specified."
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
