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

from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files


class InvalidInstancesFileError(core_exceptions.Error):
  """Indicates that the input file was invalid in some way."""
  pass


def ReadInstances(input_file, data_format, limit=None):
  """Reads the instances from input file.

  Args:
    input_file: An open file-like object for the input file.
    data_format: str, data format of the input file, 'json' or 'text'.
    limit: int, the maximum number of instances allowed in the file

  Returns:
    A list of instances.

  Raises:
    InvalidInstancesFileError: If the input file is invalid (invalid format or
        contains too many/zero instances).
  """
  instances = []

  for line_num, line in enumerate(input_file):
    line_content = line.rstrip('\r\n')
    if not line_content:
      raise InvalidInstancesFileError('Empty line is not allowed in the '
                                      'instances file.')
    if limit and line_num >= limit:
      raise InvalidInstancesFileError(
          'Online prediction can process no more than ' + str(limit) +
          ' instances per file. Please use batch prediction instead.')
    if data_format == 'json':
      try:
        instances.append(json.loads(line_content))
      except ValueError:
        raise InvalidInstancesFileError(
            'Input instances are not in JSON format. '
            'See "gcloud ml-engine predict --help" for details.')
    elif data_format == 'text':
      instances.append(line_content)

  if not instances:
    raise InvalidInstancesFileError('No valid instance was found.')

  return instances


def ReadInstancesFromArgs(json_instances, text_instances, limit=None):
  """Reads the instances from the given file path ('-' for stdin).

  Exactly one of json_instances, text_instances must be given.

  Args:
    json_instances: str or None, a path to a file ('-' for stdin) containing
        instances in JSON format.
    text_instances: str or None, a path to a file ('-' for stdin) containing
        instances in text format.
    limit: int, the maximum number of instances allowed in the file

  Returns:
    A list of instances.

  Raises:
    InvalidInstancesFileError: If the input file is invalid (invalid format or
        contains too many/zero instances), or an improper combination of input
        files was given.
  """
  if (json_instances and text_instances or
      not (json_instances or text_instances)):
    raise InvalidInstancesFileError(
        'Exactly one of --json-instances and --text-instances must be '
        'specified.')

  if json_instances:
    data_format = 'json'
    input_file = json_instances
  elif text_instances:
    data_format = 'text'
    input_file = text_instances

  with files.Open(input_file) as f:
    return ReadInstances(f, data_format, limit=limit)


def ParseModelOrVersionRef(model_id, version_id):
  if version_id:
    return resources.REGISTRY.Parse(
        version_id,
        collection='ml.projects.models.versions',
        params={
            'projectsId': properties.VALUES.core.project.GetOrFail,
            'modelsId': model_id
        })
  else:
    return resources.REGISTRY.Parse(
        model_id,
        params={'projectsId': properties.VALUES.core.project.GetOrFail},
        collection='ml.projects.models')
