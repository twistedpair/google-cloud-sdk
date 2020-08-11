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

"""Task for file uploads.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import task
from googlecloudsdk.core.util import files


class FileUploadTask(task.Task):
  """Represents a command operation triggering a file upload.

  Attributes:
    source_local_path (str): The local filesystem path of the source file to
        upload.
    destination_object_reference (resource_reference.ObjectReference): Must
        contain the full object path. Directories will not be accepted. Existing
        objects at the this location will be overwritten.
  """

  def __init__(self, source_local_path, destination_object_reference):
    super(FileUploadTask, self).__init__()
    self.upload_stream = files.FileReader(source_local_path)

    cloud_url = storage_url.CloudUrl.from_url_string(
        destination_object_reference.storage_url.url_string)
    self.provider = cloud_url.scheme
    self.object_metadata = destination_object_reference.metadata_object

  def execute(self, callback=None):
    # TODO(b/162069479): Support all of UploadObject's parameters.
    api_factory.get_api(self.provider).UploadObject(self.upload_stream,
                                                    self.object_metadata)
