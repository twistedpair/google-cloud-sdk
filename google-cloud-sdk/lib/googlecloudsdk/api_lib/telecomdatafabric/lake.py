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
"""Functions to transform input args to request field params."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def Lake(lake_id):
  """Convert a lake_id to lake object.

  Args:
    lake_id: An id of the lake which exists in Dataplex.

  Returns:
    A lake object.
  """
  return {"lake_id": lake_id}


def LakeInfo(lake_id):
  """Convert a lake_id to lake_info object.

  Args:
    lake_id: A lake_id used to create resources in Dataplex.

  Returns:
    A lake_info object.
  """
  return {"lake": {"lake_id": lake_id}}
