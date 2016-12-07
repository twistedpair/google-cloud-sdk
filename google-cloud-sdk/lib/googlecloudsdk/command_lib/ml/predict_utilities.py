# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Utilities for reading instances for prediction."""

import json
import sys

from googlecloudsdk.core import exceptions as core_exceptions


class InvalidInstancesFileError(core_exceptions.Error):
  """Indicates that the input file was invalid in some way."""
  pass


def _ReadInstancesInternal(input_file=None, data_format=None, line_limit=100):
  """Read the instances from input file.

  Args:
    input_file: An open file object for the input file.
    data_format: data format of the input file, 'json' or 'text'.
    line_limit: maximum number of instances allowed from the input_file.

  Returns:
    A list of instances.

  Raises:
    InvalidInstancesFileError: if the input_file is empty, ill-formatted,
        or contains more than 100 instances.
  """
  instances = []
  line_num = 0

  for line_num, line in enumerate(input_file):
    line_content = line.rstrip('\n')
    if not line_content:
      raise InvalidInstancesFileError('Empty line is not allowed in the '
                                      'instances file.')
    if line_limit and line_num > line_limit:
      raise InvalidInstancesFileError(
          'Online prediction can process no more than ' + str(line_limit) +
          ' instances per file. Please use batch prediction instead.')
    if data_format == 'json':
      try:
        instances.append(json.loads(line_content))
      except ValueError:
        raise InvalidInstancesFileError(
            'Input instances are not in JSON format. '
            'See "gcloud beta ml predict --help" for details.')
    elif data_format == 'text':
      instances.append(line_content)

  if not instances:
    raise InvalidInstancesFileError('No valid instance was found.')

  return instances


def ReadInstances(input_file, data_format, local_predict=False):
  """Read the instances from input file.

  Args:
    input_file: path to the input file. '-' denotes stdin.
    data_format: data format of the input file, 'json' or 'text'.
    local_predict: whether this is called for local prediction.

  Returns:
    A list of instances.
  """

  line_limit = None
  if not local_predict:
    line_limit = 100

  instances = []
  if input_file == '-':
    instances = _ReadInstancesInternal(sys.stdin, data_format, line_limit)
  else:
    with open(input_file, 'r') as f:
      instances = _ReadInstancesInternal(f, data_format, line_limit)

  return instances
