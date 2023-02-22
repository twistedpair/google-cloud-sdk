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
"""Worklad Certificate API errors."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


def ConstructNotAuthorizedError(resource_name, project=None):
  """Constructs a new Error for reporting when it is not authorized to access the resource."""
  project = project or properties.VALUES.core.project.GetOrFail()
  return exceptions.Error(
      'Not authorized to access {} for project [{}]'.format(
          resource_name, project
      )
  )


def ConstructResourceNotFoundError(resource_name, project=None):
  """Constructs a new Error for reporting when this resource is not found."""
  project = project or properties.VALUES.core.project.GetOrFail()
  return exceptions.Error(
      'Resource [{}] for project [{}] is not found'.format(
          resource_name, project
      )
  )
