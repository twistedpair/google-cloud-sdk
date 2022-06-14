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

  _ResourcesTransform(workflow)

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

  if "options" in workflow:
    if "status" in workflow["options"]:
      popped_status = workflow["options"].pop("status")
      workflow["options"]["statusUpdateOptions"] = popped_status


def _ResourcesTransform(workflow):
  """Transform resources message."""

  resources_map = {}
  has_resources = False
  for resource in workflow.get("resources", []):
    has_resources = True

    if "ref" in resource and "kind" in resource and resource[
        "kind"] == "cloudbuild.googleapis.com/SecretManagerSecret":
      resource.pop("kind")
      resource["secret"] = {}
      resource["secret"]["secretVersion"] = resource.pop("ref")
      resources_map[resource.pop("name")] = resource

  if has_resources:
    workflow["resources"] = resources_map


def _PipelineSpecTransform(pipeline_spec):
  """Transform pipeline spec message."""

  for pipeline_task in pipeline_spec.get("tasks", []):
    _PipelineTaskTransform(pipeline_task)

  for param_spec in pipeline_spec.get("params", []):
    input_util.ParamSpecTransform(param_spec)

  if "finally" in pipeline_spec:
    for pipeline_task in pipeline_spec.get("finally", []):
      input_util.ParamDictTransform(pipeline_task.get("params", []))
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

  input_util.ParamDictTransform(pipeline_task.get("params", []))


def _WhenExpressionTransform(when_expression):
  if "operator" in when_expression:
    when_expression["expressionOperator"] = input_util.CamelToSnake(
        when_expression.pop("operator")).upper()


def _WorkspaceBindingTransform(workspace_binding):
  """Transform workspace binding message."""

  if "secretName" in workspace_binding:
    popped_secret = workspace_binding.pop("secretName")
    workspace_binding["secret"] = {}
    workspace_binding["secret"]["secretName"] = popped_secret

  elif "volume" in workspace_binding:
    popped_volume = workspace_binding.pop("volume")
    # Volume Claim Template.
    workspace_binding["volumeClaimTemplate"] = {"spec": {}}

    if "accessMode" in popped_volume:
      access_modes = []
      for access_mode in popped_volume.pop("accessMode").split(
          " | "):
        if access_mode == "read":
          access_modes.append("READ_ONLY_MANY")
        if access_mode == "read-write":
          access_modes.append("READ_WRITE_ONCE")
      workspace_binding["volumeClaimTemplate"]["spec"][
          "accessModes"] = access_modes

    if "storage" in popped_volume:
      storage = popped_volume.pop("storage")
      workspace_binding["volumeClaimTemplate"]["spec"]["resources"] = {}
      workspace_binding["volumeClaimTemplate"]["spec"]["resources"][
          "requests"] = {
              "storage": storage
          }

  else:
    # Empty Workspace.
    workspace_binding["emptyDir"] = {}
    return
