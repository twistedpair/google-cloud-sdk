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
"""Command library for run compose resource command.

This library handles the creation of Google Cloud resources required to deploy a
Docker Compose application to Cloud Run. It's utilized by the
`gcloud run compose up` command.

The core responsibilities include:
  1.  Parsing the JSON output from the 'runcompose' Go binary, which lists
      the necessary resources based on the compose file.
  2.  Providing classes to represent these resources (e.g., Cloud Build).
  3.  Orchestrating the creation of these resources in Google Cloud.
"""

import json
from typing import Any, Dict, Optional


class BuildConfig:
  """Represents the build configuration for a service."""

  def __init__(
      self, context: Optional[str] = None, dockerfile: Optional[str] = None
  ):
    self.context = context
    self.dockerfile = dockerfile
    self.image_id: Optional[str] = None

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'BuildConfig':
    return cls(
        context=data.get('context'),
        dockerfile=data.get('dockerfile'),
    )


class ResourcesConfig:
  """Represents the resources config sent form runcompose go binary."""

  def __init__(self, source_builds: Optional[Dict[str, BuildConfig]] = None):
    self.source_builds = source_builds if source_builds is not None else {}

  @classmethod
  def from_json(cls, json_data: str) -> 'ResourcesConfig':
    """Parses the JSON string to create a ResourcesConfig instance."""
    data = json.loads(json_data)
    return cls.from_dict(data)

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'ResourcesConfig':
    """Creates a ResourcesConfig instance from a dictionary."""
    source_builds = {
        key: BuildConfig.from_dict(value)
        for key, value in data.get('source_builds', {}).items()
    }
    return cls(source_builds=source_builds)
