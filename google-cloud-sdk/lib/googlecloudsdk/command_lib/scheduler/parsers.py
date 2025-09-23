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
from googlecloudsdk.core import properties

_PROJECT = properties.VALUES.core.project.GetOrFail


def ParseKmsDescribeArgs(args):
  """Parses KMS describe args."""
  location_id = args.location if args.location else None
  project_id = _PROJECT()

  return project_id, location_id
