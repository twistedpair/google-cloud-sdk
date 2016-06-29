# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Manage and stream build logs.

"""

import time

from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.core import log


def Stream(build_ref, client, messages):
  """Stream the logs for a build.

  Args:
    build_ref: Build resource, The build whose logs shall be streamed.
    client: apitools cloudbuild client.
    messages: apitools cloudbuild messages module.

  Returns:
    Build message, The completed or terminated build as read for the final
    poll.
  """
  build = client.projects_builds.Get(build_ref.Request())

  log_stripped = build.logsBucket.lstrip('gs://')
  if '/' not in log_stripped:
    log_bucket = log_stripped
    log_object_dir = ''
  else:
    [log_bucket, log_object_dir] = log_stripped.split('/', 1)
    log_object_dir += '/'

  log_object = '{object}log-{id}.txt'.format(
      object=log_object_dir,
      id=build.id,
  )

  log_tailer = cloud_storage.LogTailer(
      bucket=log_bucket,
      obj=log_object,
      out=log.out,
      url_pattern='https://storage.googleapis.com/{bucket}/{obj}')

  statuses = messages.Build.StatusValueValuesEnum
  working_statuses = [
      statuses.QUEUED,
      statuses.WORKING,
  ]

  while build.status in working_statuses:
    log_tailer.Poll()
    time.sleep(1)
    build = client.projects_builds.Get(build_ref.Request())

  # Poll the logs one final time to ensure we have everything. We know this
  # final poll will get the full log contents because GCS is strongly
  # consistent and Container Builder waits for logs to finish pushing before
  # marking the build complete.
  log_tailer.Poll(is_last=True)

  return build
