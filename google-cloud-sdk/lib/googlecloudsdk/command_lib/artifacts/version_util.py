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
"""Utility for parsing Artifact Registry versions."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from apitools.base.protorpclite import protojson
from googlecloudsdk.core import resources


def ShortenRelatedTags(response, unused_args):
  """Convert the tag resources into tag IDs."""
  tags = []
  for t in response.relatedTags:
    tag = resources.REGISTRY.ParseRelativeName(
        t.name,
        'artifactregistry.projects.locations.repositories.packages.tags')
    tags.append(tag.tagsId)

  json_obj = json.loads(protojson.encode_message(response))
  json_obj.pop('relatedTags', None)
  if tags:
    json_obj['relatedTags'] = tags
  return json_obj
