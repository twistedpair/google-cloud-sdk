# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Argument processors for Zone Management service account surface arguments."""

import json

from apitools.base.py import encoding
from googlecloudsdk.core.util import files


def PossiblyWritePrivateKeyToOutputFile(response, parsed_args):
  """Write the private key response to parsed_args.output_file."""
  json_response = encoding.MessageToJson(response)
  try:
    json_data = json.loads(json_response)
  except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")
    return None
  # Jsonify python object with indents
  formatted_json = json.dumps(json_data, indent=2)
  if not parsed_args.output_file:
    return None
  files.WriteFileContents(parsed_args.output_file, formatted_json)
  return "Service account key file [{}] created".format(parsed_args.output_file)
