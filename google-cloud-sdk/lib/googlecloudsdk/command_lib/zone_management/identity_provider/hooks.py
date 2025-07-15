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
"""Argument processors for Zone Management identity provider surface arguments."""

import json

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import yaml


def AddOidcConfigToRequest(ref, args, req):
  """Reads the oidc config from the file and populates the request body.

  Args:
    ref: The resource reference.
    args: The parsed arguments from the command line.
    req: The request to modify.

  Returns:
    The modified request.

  Raises:`
    exceptions.InvalidArgumentException: If file cannot be read or is not a
    valid json/yaml.
  """
  file_path = args.config
  try:
    with open(file_path, "r") as f:
      content = f.read()
      try:
        idp = json.loads(content)
      except json.JSONDecodeError:
        try:
          idp = yaml.load(content)
        except yaml.YAMLParseError as e:
          raise exceptions.InvalidArgumentException(
              "config",
              f"Error parsing file {file_path}. Please provide a valid json or"
              f" yaml file. Error: {e}",
          ) from e
      req.createIdentityProviderRequest.identityProvider = idp
  except FileNotFoundError as e:
    raise exceptions.InvalidArgumentException(
        "config", f"File not found: {file_path}"
    ) from e
  req.createIdentityProviderRequest.identityProvider.name = ref.RelativeName()
  return req
