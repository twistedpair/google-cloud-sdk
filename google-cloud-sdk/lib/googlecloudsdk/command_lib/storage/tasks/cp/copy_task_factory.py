# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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

"""Preferred method of generating a copy task."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import posix_util
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.tasks.cp import daisy_chain_copy_task
from googlecloudsdk.command_lib.storage.tasks.cp import file_download_task
from googlecloudsdk.command_lib.storage.tasks.cp import file_upload_task
from googlecloudsdk.command_lib.storage.tasks.cp import intra_cloud_copy_task
from googlecloudsdk.command_lib.storage.tasks.cp import parallel_composite_upload_util
from googlecloudsdk.command_lib.storage.tasks.cp import streaming_download_task
from googlecloudsdk.command_lib.storage.tasks.cp import streaming_upload_task


def get_copy_task(source_resource,
                  destination_resource,
                  delete_source=False,
                  do_not_decompress=False,
                  force_daisy_chain=False,
                  print_created_message=False,
                  shared_stream=None,
                  user_request_args=None):
  """Factory method that returns the correct copy task for the arguments.

  Args:
    source_resource (resource_reference.Resource): Reference to file to copy.
    destination_resource (resource_reference.Resource): Reference to destination
      to copy file to.
    delete_source (bool): If copy completes successfully, delete the source
        object afterwards.
    do_not_decompress (bool): Prevents automatically decompressing downloaded
      gzips.
    force_daisy_chain (bool): If True, yields daisy chain copy tasks in place
      of intra-cloud copy tasks.
    print_created_message (bool): Print the versioned URL of each successfully
      copied object.
    shared_stream (stream): Multiple tasks may reuse this read or write stream.
    user_request_args (UserRequestArgs|None): Values for RequestConfig.

  Returns:
    Task object that can be executed to perform a copy.

  Raises:
    NotImplementedError: Cross-cloud copy.
    ValueError: Local filesystem copy.
  """
  source_url = source_resource.storage_url
  destination_url = destination_resource.storage_url

  if (isinstance(source_url, storage_url.FileUrl)
      and isinstance(destination_url, storage_url.FileUrl)):
    raise ValueError('Local copies not supported. Gcloud command-line tool is'
                     ' meant for cloud operations.')

  if (isinstance(source_url, storage_url.CloudUrl)
      and isinstance(destination_url, storage_url.FileUrl)):
    if destination_url.is_stream:
      return streaming_download_task.StreamingDownloadTask(
          source_resource,
          shared_stream,
          print_created_message=print_created_message,
          user_request_args=user_request_args)

    return file_download_task.FileDownloadTask(
        source_resource,
        destination_resource,
        delete_source=delete_source,
        do_not_decompress=do_not_decompress,
        print_created_message=print_created_message,
        system_posix_data=posix_util.run_if_preserving_posix(
            user_request_args, posix_util.get_system_posix_data
        ),
        user_request_args=user_request_args,
    )

  if (isinstance(source_url, storage_url.FileUrl)
      and isinstance(destination_url, storage_url.CloudUrl)):
    if source_url.is_stream:
      return streaming_upload_task.StreamingUploadTask(
          source_resource,
          destination_resource,
          print_created_message=print_created_message,
          user_request_args=user_request_args)
    else:
      is_composite_upload_eligible = (
          parallel_composite_upload_util.is_composite_upload_eligible(
              source_resource, destination_resource, user_request_args))
      return file_upload_task.FileUploadTask(
          source_resource,
          destination_resource,
          delete_source=delete_source,
          print_created_message=print_created_message,
          user_request_args=user_request_args,
          is_composite_upload_eligible=is_composite_upload_eligible)

  if (isinstance(source_url, storage_url.CloudUrl)
      and isinstance(destination_url, storage_url.CloudUrl)):
    if source_url.scheme != destination_url.scheme or force_daisy_chain:
      if (user_request_args and user_request_args.resource_args and
          user_request_args.resource_args.preserve_acl):
        raise ValueError(
            'Cannot preserve ACLs while copying between cloud providers.')
      return daisy_chain_copy_task.DaisyChainCopyTask(
          source_resource,
          destination_resource,
          delete_source=delete_source,
          print_created_message=print_created_message,
          user_request_args=user_request_args)
    return intra_cloud_copy_task.IntraCloudCopyTask(
        source_resource,
        destination_resource,
        delete_source=delete_source,
        print_created_message=print_created_message,
        user_request_args=user_request_args)
