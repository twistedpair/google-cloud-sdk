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
"""Utilities for parsing arguments to `gcloud scheduler` commands."""

import re
from googlecloudsdk.core import properties

_PROJECT = properties.VALUES.core.project.GetOrFail


def ParseFullKmsKeyName(kms_key_name):
  """Parses and retrieves the segments of a full KMS key name."""
  if not kms_key_name:
    return None

  match = re.match(
      r'projects\/(?P<project>.*)\/locations\/(?P<location>.*)\/keyRings\/(?P<keyring>.*)\/cryptoKeys\/(?P<key>.*)',
      kms_key_name,
  )
  if match:
    return [
        match.group('project'),
        match.group('location'),
        match.group('keyring'),
        match.group('key'),
    ]
  return None


def ParseKmsDescribeArgs(args):
  """Parses KMS describe args."""
  location_id = args.location if args.location else None
  return _PROJECT(), location_id


def ParseKmsClearArgs(args):
  """Parses KMS clear args."""
  location_id = args.location if args.location else None

  return _PROJECT(), location_id


def ParseKmsUpdateArgs(args):
  """Parses KMS update args."""
  location_id = args.location if args.location else None

  full_kms_key_name = None
  parse_result = ParseFullKmsKeyName(args.kms_key_name)
  if parse_result:
    # A full KMS key name resource was set as kms_key_name. Continue.
    location_id = parse_result[1]
    full_kms_key_name = args.kms_key_name
  elif args.kms_key_name and args.kms_keyring and args.location:
    # A full kms-key-name was not provided, so build the key using each
    # component since they are available..
    full_kms_key_name = 'projects/{kms_project_id}/locations/{location_id}/keyRings/{kms_keyring}/cryptoKeys/{kms_key_name}'.format(
        kms_project_id=args.kms_project if args.kms_project else _PROJECT(),
        location_id=location_id,
        kms_keyring=args.kms_keyring,
        kms_key_name=args.kms_key_name,  # short key name
    )

  return _PROJECT(), location_id, full_kms_key_name
