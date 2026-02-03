# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Base action processor for declarative pipelines."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from collections.abc import MutableMapping, Sequence
import pathlib
from typing import Any

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.declarative_pipeline.tools import python_environment


class ActionProcessor:
  """Base class for engine-specific action processors."""

  def __init__(
      self,
      action,
      work_dir,
      artifact_base_uri,
      env_pack_file,
      subprocess_mod,
      defaults,
  ):
    self.action = action
    self._work_dir = work_dir
    self._artifact_base_uri = artifact_base_uri
    self._env_pack_file = env_pack_file
    self._subprocess_mod = subprocess_mod
    self._defaults = defaults
    self.full_python_path = None

  def process_action(self):
    """Processes a single action in the pipeline, resolving local paths to GCS URIs."""

    if (self._work_dir / "jobs" / "requirements.txt").exists():
      python_version = self.get_python_version()
      self.full_python_path = f"./libs/lib/python{python_version}/site-packages"
      python_environment.build_env_local(
          self._subprocess_mod,
          self._work_dir,
          self._work_dir / "jobs" / "requirements.txt",
          self._work_dir / self._env_pack_file,
          python_version,
      )

    if "filename" not in self.action:
      return

    raw_path = self.action["filename"]
    local_path = pathlib.Path(raw_path.lstrip("/"))

    absolute_local_path = self._work_dir / local_path
    if not absolute_local_path.exists():
      raise exceptions.BadFileException(
          f"File in YAML does not exist locally: {local_path}"
      )

    self.action["filename"] = (
        f"{self._artifact_base_uri}{local_path.as_posix()}"
    )

    self._update_yaml_properties(self.action)

  def get_python_version(self) -> str:
    """Returns the Python version for this action, or None if not specified."""
    raise NotImplementedError()

  def _update_yaml_properties(self, action):
    """Performs updates on YAML properties."""
    pass

  def _get_nested_dict(
      self, d: MutableMapping[str, Any], keys: Sequence[str]
  ) -> MutableMapping[str, Any]:
    """Gets a nested dictionary from `d`, creating keys with empty dictionaries if they don't exist."""
    current = d
    for key in keys:
      current = current.setdefault(key, {})
    return current
