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
"""Helper for processing API responses."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import log


def GetFieldAndLogUnreachable(message, attribute):
  """Response callback to log unreachable while generating fields of the message."""
  if message.unreachable:
    log.warning(
        'The following instances were unreachable: {}.'
        .format(', '.join(message.unreachable)))
  return getattr(message, attribute)


def GetFieldAndLogUnreachableInstancePartitions(message, attribute):
  """Response callback to log unreachable while generating fields of the message."""
  warning_text = 'The following instance partitions were unreachable: {}.'
  if hasattr(message, 'unreachable') and message.unreachable:
    # if the `message` is `ListInstancePartitionsResponse`.
    log.warning(warning_text.format(', '.join(message.unreachable)))
  elif (
      hasattr(message, 'unreachableInstancePartitions')
      and message.unreachableInstancePartitions
  ):
    # If the `message` is `ListInstancePartitionOperationsResponse`.
    log.warning(
        warning_text.format(', '.join(message.unreachableInstancePartitions))
    )
  return getattr(message, attribute)
