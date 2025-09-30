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
"""Enums for Run Compose command stages."""

import enum
from typing import Optional


class StagedProgressTrackerStage(enum.Enum):
  """Enum for progress tracker stages."""

  BUILD = 'build'
  SECRETS = 'secrets'
  VOLUMES = 'volumes'
  CONFIGS = 'configs'

  def get_key(self, container: Optional[str] = None) -> str:
    """Returns the progress tracker stage key."""
    if self == StagedProgressTrackerStage.BUILD:
      if not container:
        raise ValueError('Container name is required for BUILD stage')
      return f'{self.value}_{container}'
    return self.value
