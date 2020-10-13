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
"""Utils for resource classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime


def convert_to_json_parsable_type(value):
  """Converts values encountered in metadata to be JSON-parsable."""
  if isinstance(value, Exception):
    return str(value)
  if isinstance(value, datetime.datetime):
    return value.strftime('%Y-%m-%dT%H:%M:%S%z')
  # datetime.datetime is an instance of datetime.date, but not the opposite.
  if isinstance(value, datetime.date):
    return value.strftime('%Y-%m-%d')
  return value


def should_preserve_falsy_metadata_value(value):
  """There are falsy values we want to keep as metadata."""
  # pylint:disable=g-explicit-bool-comparison, singleton-comparison
  return value in (0, 0.0, False)
  # pylint:enable=g-explicit-bool-comparison, singleton-comparison
