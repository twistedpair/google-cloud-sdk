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
"""Dataproc Serverless action processor."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.declarative_pipeline.processors import base


class DataprocServerlessActionProcessor(base.ActionProcessor):
  """Action processor for Dataproc Serverless actions."""

  def get_python_version(self) -> str:
    # See
    # https://docs.cloud.google.com/dataproc-serverless/docs/concepts/versions/dataproc-serverless-versions
    config = self.action.get("config", {})
    runtime_version = (
        config.get("sessionTemplate", {})
        .get("inline", {})
        .get("runtimeVersion")
    )
    if not runtime_version:
      return "3.12"
    return "3.11" if str(runtime_version).startswith("2.3") else "3.12"

  def _update_yaml_properties(self, action):
    env_pack_path = self._work_dir / self._env_pack_file
    if env_pack_path.exists():
      env_pack_uri = f"{self._artifact_base_uri}{self._env_pack_file}#libs"
      if "archives" not in self.action:
        self.action["archives"] = []
      if not any(env_pack_uri in arch for arch in self.action["archives"]):
        self.action["archives"].append(env_pack_uri)
      # Add PYTHONPATH to Spark driver and executors
      # to include the site-packages
      # from the uploaded dependencies.zip, allowing the Spark jobs to find
      # the required Python libraries.
      props = self._get_nested_dict(
          action, ["config", "sessionTemplate", "inline", "properties"]
      )
      props["spark.dataproc.driverEnv.PYTHONPATH"] = self.full_python_path
      props["spark.executorEnv.PYTHONPATH"] = self.full_python_path
