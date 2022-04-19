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
"""Utility functions for task execution."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from googlecloudsdk.core import properties


def get_first_matching_message_payload(messages, topic):
  """Gets first item with matching topic from list of task output messages."""
  for message in messages:
    if topic is message.topic:
      return message.payload
  return None


def should_use_parallelism():
  """Checks execution settings to determine if parallelism should be used.

  This function is called in some tasks to determine how they are being
  executed, and should include as many of the relevant conditions as possible.

  Returns:
    True if parallel execution should be used, False otherwise.
  """
  process_count = properties.VALUES.storage.process_count.GetInt()
  thread_count = properties.VALUES.storage.thread_count.GetInt()
  return process_count > 1 or thread_count > 1
