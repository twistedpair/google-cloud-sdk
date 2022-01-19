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
"""Support library to handle the staging bucket."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import properties


def GetSafeProject():
  """Returns the encoded project id that can be used as part of the GCS bucket name."""
  return (properties.VALUES.core.project.Get(required=True).replace(
      ':', '_').replace('.', '_')
          # The string 'google' is not allowed in bucket names.
          .replace('google', 'elgoog'))


def GetDefaultStagingBucket(project_id, location):
  """Returns the default source staging bucket."""

  return project_id + '_clouddeploy_' + location
