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
"""Flattens wildcard expansion iterators and returns delete bucket tasks."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.storage import progress_callbacks
from googlecloudsdk.command_lib.storage.tasks.rb import delete_bucket_task


class DeleteBucketTaskIterator:
  """Flattens wildcard expansion iterators and returns tasks."""

  def __init__(self,
               bucket_wildcard_iterators,
               task_status_queue=None):
    """Initializes iterator.

    Args:
      bucket_wildcard_iterators (Iter[CloudWildcardIterator]): Iterable of
        wildcard iterators to flatten.
      task_status_queue (multiprocessing.Queue|None): Used for estimating total
        workload from this iterator.
    """
    self._bucket_wildcard_iterators = bucket_wildcard_iterators
    self._task_status_queue = task_status_queue

  def __iter__(self):
    buckets_count = 0
    for bucket_wildcard_iterator in self._bucket_wildcard_iterators:
      for resource in bucket_wildcard_iterator:
        yield delete_bucket_task.DeleteBucketTask(resource.storage_url)
        buckets_count += 1

    progress_callbacks.workload_estimator_callback(self._task_status_queue,
                                                   buckets_count)
