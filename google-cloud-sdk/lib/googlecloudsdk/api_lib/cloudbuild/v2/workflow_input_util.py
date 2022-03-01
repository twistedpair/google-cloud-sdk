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
"""Utilities for the parsing input for cloud build v2 API."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_exceptions
from googlecloudsdk.api_lib.cloudbuild.v2 import client_util
from googlecloudsdk.api_lib.cloudbuild.v2 import input_util


def CloudBuildYamlDataToWorkflow(workflow):
  """Convert cloudbuild.yaml file into Workflow message."""
  _VersionCheck(workflow)
  _WorkflowTransform(workflow)

  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(workflow, messages.Workflow)
  input_util.UnrecognizedFields(schema_message)
  return schema_message


def _VersionCheck(data):
  api_version = data.pop("api")
  if api_version != "v2":
    raise cloudbuild_exceptions.CloudBuildAPIVersionError()


def _WorkflowTransform(workflow):
  """Transform workflow message."""

  for param_spec in workflow.get("params", []):
    input_util.ParamSpecTransform(param_spec)

  pipeline = workflow.pop("pipeline")
  if "spec" in pipeline:
    _PipelineSpecTransform(pipeline["spec"])
    workflow["pipelineSpec"] = pipeline["spec"]
  elif "bundle" in pipeline:
    workflow["bundle"] = pipeline["bundle"]
  else:
    raise cloudbuild_exceptions.InvalidYamlError(
        "PipelineSpec or Bundle is required.")

  for workspace_binding in workflow.get("workspaces", []):
    _WorkspaceBindingTransform(workspace_binding)


def _PipelineSpecTransform(pipeline_spec):
  """Transform pipeline spec message."""

  for pipeline_task in pipeline_spec.get("tasks", []):
    _PipelineTaskTransform(pipeline_task)

  for param_spec in pipeline_spec.get("params", []):
    input_util.ParamSpecTransform(param_spec)

  if "finally" in pipeline_spec:
    for pipeline_task in pipeline_spec.get("finally", []):
      for param_spec in pipeline_task.get("params", []):
        input_util.ParamSpecTransform(param_spec)
    pipeline_spec["finallyTasks"] = pipeline_spec.pop("finally")


def _PipelineTaskTransform(pipeline_task):
  """Transform pipeline task message."""

  if "taskSpec" in pipeline_task:
    popped_task_spec = pipeline_task.pop("taskSpec")
    pipeline_task["taskSpec"] = {}
    pipeline_task["taskSpec"]["taskSpec"] = popped_task_spec
  elif "taskRef" in pipeline_task:
    pipeline_task["taskRef"] = pipeline_task.pop("taskRef")

  if "when" in pipeline_task:
    for when_expression in pipeline_task.get("when", []):
      _WhenExpressionTransform(when_expression)
    pipeline_task["whenExpressions"] = pipeline_task.pop("when")

  for param in pipeline_task.get("params", []):
    input_util.ParamSpecTransform(param)


def _WhenExpressionTransform(when_expression):
  if "operator" in when_expression:
    when_expression["expressionOperator"] = input_util.CamelToSnake(
        when_expression.pop("operator")).upper()


def _WorkspaceBindingTransform(workspace_binding):
  """Transform workspace binding message."""

  # Empty Workspace.
  if ("storage" not in workspace_binding) and ("accessMode"
                                               not in workspace_binding):
    workspace_binding["emptyDir"] = {}
    return

  # Volume Claim Template.
  workspace_binding["volumeClaimTemplate"] = {"spec": {}}

  if "accessMode" in workspace_binding:
    access_modes = []
    for access_mode in workspace_binding.pop("accessMode").split(" | "):
      if access_mode == "read":
        access_modes.append("READ_ONLY_MANY")
      if access_mode == "read-write":
        access_modes.append("READ_WRITE_MANY")
    workspace_binding["volumeClaimTemplate"]["spec"][
        "accessModes"] = access_modes

  if "storage" in workspace_binding:
    storage = workspace_binding.pop("storage")
    workspace_binding["volumeClaimTemplate"]["spec"]["resources"] = {}
    workspace_binding["volumeClaimTemplate"]["spec"]["resources"][
        "requests"] = {
            "storage": storage
        }
