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
"""Utilities for ``gcloud memcache instances create``."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class Error(Exception):
  """Exceptions for this module."""


class InvalidTimeOfDayError(Error):
  """Error for passing invalid time of day."""


def check_maintenance_window_start_time_field(maintenance_window_start_time):
  if maintenance_window_start_time < 0 or maintenance_window_start_time > 23:
    raise InvalidTimeOfDayError(
        'A valid time of day must be specified (0, 23) hours.'
    )
  return maintenance_window_start_time
