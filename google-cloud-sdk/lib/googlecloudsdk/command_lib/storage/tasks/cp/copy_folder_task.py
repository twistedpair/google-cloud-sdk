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

"""Task for copying a folder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import threading

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks import task_status
from googlecloudsdk.command_lib.storage.tasks.cp import copy_util


class RenameFolderTask(copy_util.CopyTaskWithExitHandler):
  """Represents a command operation renaming a folder around the cloud."""

  def __init__(
      self,
      source_resource,
      destination_resource,
      print_created_message=False,
      user_request_args=None,
      verbose=False,
  ):
    """Initializes RenameFolderTask. Parent class documents arguments."""
    super(RenameFolderTask, self).__init__(
        source_resource=source_resource,
        destination_resource=destination_resource,
        print_created_message=print_created_message,
        user_request_args=user_request_args,
        verbose=verbose,
    )
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string
    )

  def execute(self, task_status_queue=None):
    source_url = self._source_resource.storage_url
    destination_url = self._destination_resource.storage_url
    api_client = api_factory.get_api(source_url.scheme)

    if task_status_queue is not None:
      progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
          status_queue=task_status_queue,
          offset=0,
          length=0,
          source_url=self._source_resource.storage_url,
          destination_url=self._destination_resource.storage_url,
          operation_name=task_status.OperationName.INTRA_CLOUD_COPYING,
          process_id=os.getpid(),
          thread_id=threading.get_ident(),
      )
    else:
      progress_callback = None

    operation = api_client.rename_folder(
        destination_url.bucket_name,
        source_url.object_name,
        destination_url.object_name,
    )
    if not operation.done:
      api_client.wait_for_operation(operation)

    self._print_created_message_if_requested(self._destination_resource)

    if progress_callback:
      progress_callback(0)

  def __eq__(self, other):
    if not isinstance(other, RenameFolderTask):
      return NotImplemented
    return (
        self._source_resource == other._source_resource
        and self._destination_resource == other._destination_resource
        and self._print_created_message == other._print_created_message
        and self._user_request_args == other._user_request_args
        and self._verbose == other._verbose
    )


class CopyFolderTask(copy_util.CopyTaskWithExitHandler):
  """Represents a command operation copying a folder around the cloud."""

  def __init__(
      self,
      source_resource,
      destination_resource,
      print_created_message=False,
      user_request_args=None,
      verbose=False,
  ):
    """Initializes RenameFolderTask. Parent class documents arguments."""
    super(CopyFolderTask, self).__init__(
        source_resource=source_resource,
        destination_resource=destination_resource,
        print_created_message=print_created_message,
        user_request_args=user_request_args,
        verbose=verbose,
    )
    self.parallel_processing_key = (
        self._destination_resource.storage_url.url_string
    )

  def execute(self, task_status_queue=None):
    source_url = self._source_resource.storage_url
    destination_url = self._destination_resource.storage_url
    api_client = api_factory.get_api(source_url.scheme)

    if task_status_queue is not None:
      progress_callback = progress_callbacks.FilesAndBytesProgressCallback(
          status_queue=task_status_queue,
          offset=0,
          length=0,
          source_url=self._source_resource.storage_url,
          destination_url=self._destination_resource.storage_url,
          operation_name=task_status.OperationName.INTRA_CLOUD_COPYING,
          process_id=os.getpid(),
          thread_id=threading.get_ident(),
      )
    else:
      progress_callback = None

    bucket_layout = api_client.get_storage_layout(destination_url.bucket_name)
    # GetStorageLayout requires ListObjects permission to work.
    # While for most cases, (especially in this code path) the user would
    # have the permission, we do not want to absorb the error as this is an
    # entirely new workflow (HNS buckets) and absorbing this would end up
    # invoking upload_objects which would create objects instead of folders
    # in an HNS bucket.

    if (
        bucket_layout
        and getattr(bucket_layout, 'hierarchicalNamespace', None)
        and bucket_layout.hierarchicalNamespace.enabled
    ):
      # We are copying to an HNS bucket. This means we can and should use
      # create_folders API.
      try:
        api_client.create_folder(
            destination_url.bucket_name,
            destination_url.object_name,
            is_recursive=True,
        )
      except api_errors.ConflictError:
        # If the folder already exists, we can just skip this step.
        pass
    else:
      # We are copying to a flat namespace bucket. This means we need to
      # upload an empty object to create the folder.
      request_config = request_config_factory.get_request_config(
          destination_url,
          content_type=request_config_factory.DEFAULT_CONTENT_TYPE,
          size=None,
      )
      api_client.upload_object(
          io.StringIO(''),
          self._destination_resource,
          request_config=request_config,
      )

    self._print_created_message_if_requested(self._destination_resource)

    if progress_callback:
      progress_callback(0)

  def __eq__(self, other):
    if not isinstance(other, CopyFolderTask):
      return NotImplemented
    return (
        self._source_resource == other._source_resource
        and self._destination_resource == other._destination_resource
        and self._print_created_message == other._print_created_message
        and self._user_request_args == other._user_request_args
        and self._verbose == other._verbose
    )
