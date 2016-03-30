# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for building the dataflow CLI."""

import json
import re

from googlecloudsdk.core import log

# Regular expression to match only metrics from Dataflow. Currently, this should
# match at least "dataflow" and "dataflow/v1b3". User metrics have an origin set
# as /^user/.
DATAFLOW_METRICS_RE = re.compile('^dataflow')

# Regular expression to only match watermark metrics.
WINDMILL_WATERMARK_RE = re.compile('^(.*)-windmill-(.*)-watermark')


def GetErrorMessage(error):
  """Extract the error message from an HTTPError.

  Args:
    error: The error exceptions.HttpError thrown by the API client.

  Returns:
    A string describing the error.
  """
  try:
    content_obj = json.loads(error.content)
    return content_obj.get('error', {}).get('message', '')
  except ValueError:
    log.err.Print(error.response)
    return 'Unknown error'
