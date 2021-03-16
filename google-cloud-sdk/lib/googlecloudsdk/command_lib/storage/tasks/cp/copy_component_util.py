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
"""Utils for components in copy operations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import math

from googlecloudsdk.core.util import scaled_integer


def get_component_offsets_and_lengths(file_size, target_component_size,
                                      max_components):
  """Calculates start bytes and sizes for a multi-component copy operation.

  Args:
    file_size (int): Total byte size of file being divided into components.
    target_component_size (int|str): Target size for each component if not total
      components isn't capped by max_components. May be byte count int or size
      string (e.g. "50M").
    max_components (int): Limit on allowed components regardless of file_size
      and target_component_size.

  Returns:
    List of component offsets and lengths: list[(offset, length)].
    Total component count can be found by taking the length of the list.
  """
  if isinstance(target_component_size, int):
    target_component_size_bytes = target_component_size
  else:
    target_component_size_bytes = scaled_integer.ParseInteger(
        target_component_size)

  component_count = max(
      min(math.ceil(file_size / target_component_size_bytes), max_components),
      2)
  component_size = math.ceil(file_size / component_count)

  component_offsets_and_lengths = []
  for i in range(component_count):
    offset = i * component_size
    if offset >= file_size:
      break
    length = min(component_size, file_size - offset)
    component_offsets_and_lengths.append((offset, length))

  return component_offsets_and_lengths
