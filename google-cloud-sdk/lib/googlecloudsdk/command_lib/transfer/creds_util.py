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
"""Utils for handing transfer credentials."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import os

import boto3
from googlecloudsdk.core.util import files

from six.moves import configparser


def get_values_for_keys_from_file(file_path, keys):
  """Reads JSON or INI file and returns dict with values for requested keys.

  JSON file keys should be top level.
  INI file sections will be flattened.

  Args:
    file_path (str): Path of JSON or INI file to read.
    keys (list[str]): Search for these keys to return from file.

  Returns:
    Dict[cred_key: cred_value].

  Raises:
    ValueError: The file was the incorrect format.
    KeyError: Key was missing or duplicate key was found.
  """
  result = {}
  real_path = os.path.realpath(file_path)
  with files.FileReader(real_path) as file_reader:
    try:
      file_dict = json.loads(file_reader.read())
      for key in keys:
        if key in file_dict:
          result[key] = file_dict[key]
    except json.JSONDecodeError:
      # More file formats to try before raising error.
      config = configparser.ConfigParser()
      try:
        config.read(real_path)
      except configparser.ParsingError:
        raise ValueError('Source creds file must be JSON or INI format.')
      # Parse all sections of INI file into dict.
      for section in config:
        section_dict = dict(config[section])
        for key in keys:
          if key in section_dict:
            if key in result:
              raise KeyError('Duplicate key in file: {}'.format(key))
            result[key] = section_dict[key]

  for key in keys:
    if key not in result:
      raise KeyError('Key missing from file: {}'.format(key))
  return result


def get_aws_creds():
  """Returns creds from common AWS config file paths.

  Returns:
    Dict with AWS creds if valid config file present, else dict with None
      values for credentials.
  """
  credentials = boto3.session.Session().get_credentials()

  if credentials:
    return {
        'aws_access_key_id': credentials.access_key,
        'aws_secret_access_key': credentials.secret_key
    }
  return {'aws_access_key_id': None, 'aws_secret_access_key': None}
