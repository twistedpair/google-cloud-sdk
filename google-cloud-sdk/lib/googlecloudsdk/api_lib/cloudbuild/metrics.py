# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Cloud Build CSI metric names and metric collection methods."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
from googlecloudsdk.core import metrics


# Metric names for client side instruments(CSI).

# Reserved CSI metric prefix for cloudbuild
_CLOUDBUILD_PREFIX = 'cloudbuild_'

# Time to create a configuration
UPLOAD_SOURCE = _CLOUDBUILD_PREFIX + 'upload_source'


@contextlib.contextmanager
def record_duration(method_name):
  """Record duration of a serverless API method call.

  Two timestamps will be sent, and the duration in between will be considered as
  the client side latency of this method call.

  Args:
    method_name: str, The name of the method to time.

  Yields:
    None
  """
  metrics.CustomTimedEvent(method_name + '_start')
  yield
  metrics.CustomTimedEvent(method_name)
