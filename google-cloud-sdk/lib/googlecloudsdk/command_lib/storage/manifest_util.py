# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""For managing the copy manifest feature (manifest = a file with copy info)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import csv
import datetime
import enum
import os

from googlecloudsdk.command_lib.storage import thread_messages
from googlecloudsdk.core.util import files


class ResultStatus(enum.Enum):
  ERROR = 'error'
  OK = 'OK'
  SKIP = 'skip'


def parse_for_completed_sources(manifest_path):
  """Extracts set of completed or skipped copies from manifest CSV."""
  if not (manifest_path and os.path.exists(manifest_path)):
    return set()
  res = set()
  with files.FileReader(manifest_path) as file_reader:
    csv_reader = csv.DictReader(file_reader)
    for row in csv_reader:
      if row['Result'] in (ResultStatus.OK.value, ResultStatus.SKIP.value):
        res.add(row['Source'])
  return res


def send_error_message(source_resource, destination_resource, error,
                       task_status_queue):
  """Send ManifestMessage to task_status_queue for processing."""
  task_status_queue.put(
      thread_messages.ManifestMessage(
          source_url=source_resource.storage_url,
          destination_url=destination_resource.storage_url,
          end_time=datetime.datetime.utcnow().isoformat(),
          size=source_resource.size,
          result_status=ResultStatus.ERROR,
          md5_hash=source_resource.md5_hash,
          description=str(error),
      ))
