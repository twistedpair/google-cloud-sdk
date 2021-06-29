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

"""Factory class for PySparkBatch message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.dataproc import flags
from googlecloudsdk.command_lib.dataproc import local_file_uploader


class PySparkBatchFactory(object):
  """Factory class for PySparkBatch message."""

  def __init__(self, dataproc):
    """Factory class for SparkBatch message.

    Args:
      dataproc: A Dataproc instance.
    """
    self.dataproc = dataproc

  def UploadLocalFilesAndGetMessage(self, args):
    """upload user local files and creates a PySparkBatch message.

    Upload user local files and point URIs to the local files to the uploaded
    URIs.
    Creates a PySparkBatch message from parsed arguments.

    Args:
      args: Parsed arguments.

    Returns:
      PySparkBatch: A PySparkBatch message.
    """
    kwargs = {}

    dependencies = {}

    # Upload requires a list.
    dependencies['mainPythonFileUri'] = [args.MAIN_PYTHON_FILE]

    if args.python_files:
      dependencies['pythonFileUris'] = args.python_files

    if args.jar_files:
      dependencies['jarFileUris'] = args.jar_files

    if args.files:
      dependencies['fileUris'] = args.files

    if args.archives:
      dependencies['archiveUris'] = args.archives

    if args.args:
      kwargs['args'] = args.args

    dependencies = local_file_uploader.Upload(args.bucket, dependencies)

    # Move mainPythonFileUri out of the list.
    dependencies['mainPythonFileUri'] = dependencies['mainPythonFileUri'][0]

    # Merge the dict first for compatibility.
    # Old python versions don't support multi unpacking of dictionaries.
    kwargs.update(dependencies)

    return self.dataproc.messages.PySparkBatch(**kwargs)


def AddArguments(parser):
  """Adds arguments related to PySparkBatch message."""
  flags.AddMainPythonFile(parser)
  flags.AddPythonFiles(parser)
  flags.AddJarFiles(parser)
  flags.AddOtherFiles(parser)
  flags.AddArchives(parser)
  flags.AddArgs(parser)
  # Cloud Storage bucket to upload workload dependencies.
  # It is required until we figure out a place to upload user files.
  flags.AddBucket(parser)
