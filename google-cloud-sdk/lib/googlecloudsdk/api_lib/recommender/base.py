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
"""Base classes for abstracting away common logic."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import enum

API_NAME = 'recommender'

RECOMMENDER_MESSAGE_PREFIX = {
    'v1': 'GoogleCloudRecommenderV1',
    'v1beta1': 'GoogleCloudRecommenderV1beta1',
    'v1alpha2': 'GoogleCloudRecommenderV1alpha2'
}


class EntityType(enum.Enum):
  """Cloud Entity Types."""
  ORGANIZATION = 1
  FOLDER = 2
  PROJECT = 3
  BILLING_ACCOUNT = 4
