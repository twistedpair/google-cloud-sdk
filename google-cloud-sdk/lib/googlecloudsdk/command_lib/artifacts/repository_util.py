# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Utility for forming CreateRepository requests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib import artifacts


def RetainFormatConfig(m, repo):
  """Add format-specific conifg to the repo."""
  if repo.format == m.Repository.FormatValueValuesEnum.DOCKER:

    # mavenConfig does not exist in v1beta2
    if hasattr(repo, 'mavenConfig'):
      repo.mavenConfig = None
    return
  if repo.format == m.Repository.FormatValueValuesEnum.MAVEN:

    # dockerConfig does not exist in v1beta2
    if hasattr(repo, 'dockerConfig'):
      repo.dockerConfig = None
    return

  # Do not set any per format config in all other cases
  if hasattr(repo, 'mavenConfig'):
    repo.mavenConfig = None
  if hasattr(repo, 'dockerConfig'):
    repo.dockerConfig = None


def RetainFormatConfigHook(ref, unused_args, req):
  """Add format-specific conifg to the repo."""
  m = artifacts.Messages(ref.GetCollectionInfo().api_version)
  RetainFormatConfig(m, req.repository)
  return req
