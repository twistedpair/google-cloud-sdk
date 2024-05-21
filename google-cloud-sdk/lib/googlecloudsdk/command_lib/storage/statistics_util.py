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
"""Util functions for statistics in gcloud storage."""

from __future__ import annotations

from typing import List


def find_percentile(values: List[int], percentile: float) -> float | None:
  """Finds the percentile value for a given list of values.

  Args:
    values: The list of values to find the percentile in.
    percentile: The percentile to find.

  Returns:
    The percentile value.
  """
  if not values:
    return
  values.sort()
  index = (percentile / 100) * (len(values) - 1)
  index_int = int(index)
  if index.is_integer():
    return values[index_int]
  else:
    # Linear interpolation.
    lower_value = values[index_int]
    upper_value = values[int(index + 1)]
    return lower_value + (upper_value - lower_value) * (index - index_int)
