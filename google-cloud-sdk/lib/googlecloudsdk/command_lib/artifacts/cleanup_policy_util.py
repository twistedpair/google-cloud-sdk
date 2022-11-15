# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Utility for forming Artifact Registry requests around cleanup policies."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import encoding
from googlecloudsdk.core.util import times
import six


def ParseCleanupPolicy(path):
  """Reads a cleanup policy from a JSON formatted file.

  Args:
    path: str, path to the policy file.

  Returns:
    A dict describing a cleanup policy, matching the proto description.

  Raises:
    InvalidInputValueError: The JSON file could not be parsed or the data does
    not follow the correct schema.
  """
  content = console_io.ReadFromFileOrStdin(path, binary=False)
  try:
    file_policies = json.loads(encoding.Decode(content))
  except ValueError as e:
    raise apitools_exceptions.InvalidUserInputError(
        'Could not read JSON file {}: {}'.format(path, e))
  policies = dict()
  for policy in file_policies:
    for key in ['name', 'action', 'condition']:
      if key not in policy:
        raise ar_exceptions.InvalidInputValueError(
            'Key "{}" not found in policy.'.format(key))
    if 'type' not in policy['action']:
      raise ar_exceptions.InvalidInputValueError(
          'Key "type" not found in policy action.')
    condition = dict()
    if 'versionAge' in policy['condition']:
      seconds = times.ParseDuration(policy['condition']['versionAge'])
      condition['versionAge'] = six.text_type(seconds.total_seconds) + 's'
    policies[policy['name']] = {
        'id': policy['name'],
        'condition': condition,
        'action': policy['action']['type'],
    }
  return policies


def SetDeleteCleanupPolicyUpdateMask(unused_ref, unused_args, request):
  """Sets update mask for deleting Cleanup Policies."""
  request.updateMask = 'cleanup_policies'
  return request


def RepositoryToCleanupPoliciesResponse(response, unused_args):
  if not response.cleanupPolicies:
    return None
  return response.cleanupPolicies.additionalProperties


def RepositoryToSetCleanupPolicyResponse(response, unused_args):
  if not response.cleanupPolicies:
    raise ar_exceptions.ArtifactRegistryError(
        'Failed to set cleanup policy. Cleanup policies are currently in '
        'private preview.')
  return response.cleanupPolicies.additionalProperties
