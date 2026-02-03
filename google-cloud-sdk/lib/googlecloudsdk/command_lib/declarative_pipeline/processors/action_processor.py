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
"""Action processors factory for declarative pipelines."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.declarative_pipeline.processors import base
from googlecloudsdk.command_lib.declarative_pipeline.processors import dataproc_gce
from googlecloudsdk.command_lib.declarative_pipeline.processors import dataproc_serverless


def get_action_processor(
    action, work_dir, artifact_base_uri, env_pack_file, subprocess_mod, defaults
) -> base.ActionProcessor:
  """Returns the appropriate ActionProcessor for the given action."""
  engine = action.get("engine", "dataproc-serverless")
  if isinstance(engine, dict):
    engine_type = engine.get("engineType", "dataproc-serverless")
  else:
    engine_type = engine

  if engine_type == "dataproc-serverless":
    return dataproc_serverless.DataprocServerlessActionProcessor(
        action,
        work_dir,
        artifact_base_uri,
        env_pack_file,
        subprocess_mod,
        defaults,
    )
  if engine_type == "dataproc-gce":
    return dataproc_gce.DataprocGCEActionProcessor(
        action,
        work_dir,
        artifact_base_uri,
        env_pack_file,
        subprocess_mod,
        defaults,
    )
  # TODO: b/474620155 - Support other actions.
  return dataproc_serverless.DataprocServerlessActionProcessor(
      action,
      work_dir,
      artifact_base_uri,
      env_pack_file,
      subprocess_mod,
      defaults,
  )
