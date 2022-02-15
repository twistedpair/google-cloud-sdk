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

  pipeline = workflow.pop("pipeline")
  if "spec" in pipeline:
    _PipelineSpecTransform(pipeline["spec"])
    workflow["pipelineSpec"] = pipeline["spec"]
  elif "bundle" in pipeline:
    workflow["bundle"] = pipeline["bundle"]
  else:
    raise cloudbuild_exceptions.InvalidYamlError(
        "PipelineSpec or Bundle is required.")

  for workspace in workflow.get("workspaces", []):
    input_util.WorkspaceTransform(workspace)


def _PipelineSpecTransform(pipeline_spec):
  for task in pipeline_spec.get("tasks", []):
    _PipelineTaskTransform(task)


def _PipelineTaskTransform(pipeline_task):
  task = pipeline_task.pop("task")
  if "taskSpec" in task:
    pipeline_task["taskSpec"] = task["taskSpec"]
  elif "taskRef" in task:
    pipeline_task["taskRef"] = task["taskRef"]

  for when_expression in pipeline_task.get("whenExpressions", []):
    _WhenExpressionTransform(when_expression)


def _WhenExpressionTransform(when_expression):
  if "expressionOperator" in when_expression:
    when_expression["expressionOperator"] = input_util.CamelToSnake(
        when_expression.pop("expressionOperator")).upper()
