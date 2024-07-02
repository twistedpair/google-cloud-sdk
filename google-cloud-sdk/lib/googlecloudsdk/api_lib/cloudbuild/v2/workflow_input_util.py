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
from googlecloudsdk.core import yaml


_WORKFLOW_OPTIONS_ENUMS = [
    "options.provenance.enabled",
    "options.provenance.storage",
    "options.provenance.region",
]


def CloudBuildYamlDataToWorkflow(workflow):
  """Convert cloudbuild.yaml file into Workflow message."""
  _WorkflowTransform(workflow)
  _WorkflowValidate(workflow)

  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(workflow, messages.Workflow)
  input_util.UnrecognizedFields(schema_message)
  return schema_message


def _WorkflowValidate(workflow):
  """Check that the given workflow has all required fields.

  Args:
    workflow: The user-supplied Cloud Build Workflow YAML.

  Raises:
    InvalidYamlError: If the workflow is invalid.
  """
  if (
      "options" not in workflow
      or "security" not in workflow["options"]
      or "serviceAccount" not in workflow["options"]["security"]
  ):
    raise cloudbuild_exceptions.InvalidYamlError(
        "A service account is required. Specify your user-managed service"
        " account using the options.security.serviceAccount field"
    )


def _WorkflowTransform(workflow):
  """Transform workflow message."""

  if "triggers" in workflow:
    workflow["workflowTriggers"] = workflow.pop("triggers")

  for workflow_trigger in workflow.get("workflowTriggers", []):
    input_util.WorkflowTriggerTransform(workflow_trigger)

  for param_spec in workflow.get("params", []):
    input_util.ParamSpecTransform(param_spec)
    if not param_spec.get("name", ""):
      raise cloudbuild_exceptions.InvalidYamlError(
          "Workflow parameter name is required"
      )
    if (
        param_spec.get("type", "string") != "string"
        or param_spec.get("default", {"type": "STRING"}).get("type") != "STRING"
    ):
      raise cloudbuild_exceptions.InvalidYamlError(
          "Only string are supported for workflow parameters, error at "
          "parameter with name: {}".format(param_spec.get("name"))
      )

  if "pipelineSpec" in workflow:
    workflow["pipelineSpecYaml"] = yaml.dump(
        workflow.pop("pipelineSpec"), round_trip=True
    )
  elif "pipelineRef" in workflow:
    input_util.RefTransform(workflow["pipelineRef"])
  else:
    raise cloudbuild_exceptions.InvalidYamlError(
        "PipelineSpec or PipelineRef is required.")

  for workspace_binding in workflow.get("workspaces", []):
    _WorkspaceBindingTransform(workspace_binding)

  if "options" in workflow and "status" in workflow["options"]:
    popped_status = workflow["options"].pop("status")
    workflow["options"]["statusUpdateOptions"] = popped_status

  for option in _WORKFLOW_OPTIONS_ENUMS:
    input_util.SetDictDottedKeyUpperCase(workflow, option)


def _PipelineSpecTransform(pipeline_spec):
  """Transform pipeline spec message."""

  for pipeline_task in pipeline_spec.get("tasks", []):
    _PipelineTaskTransform(pipeline_task)

  for param_spec in pipeline_spec.get("params", []):
    input_util.ParamSpecTransform(param_spec)

  if "finally" in pipeline_spec:
    finally_tasks = pipeline_spec.pop("finally")
    for task in finally_tasks:
      _PipelineTaskTransform(task)
    pipeline_spec["finallyTasks"] = finally_tasks


def _PipelineTaskTransform(pipeline_task):
  """Transform pipeline task message."""

  if "taskSpec" in pipeline_task:
    popped_task_spec = pipeline_task.pop("taskSpec")
    for param_spec in popped_task_spec.get("params", []):
      input_util.ParamSpecTransform(param_spec)
    pipeline_task["taskSpec"] = {}
    pipeline_task["taskSpec"]["taskSpec"] = popped_task_spec
  elif "taskRef" in pipeline_task:
    input_util.RefTransform(pipeline_task["taskRef"])
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
    workspace_binding["volumeClaim"] = {}

    if "storage" in popped_volume:
      storage = popped_volume.pop("storage")
      workspace_binding["volumeClaim"]["storage"] = storage

  else:
    return
