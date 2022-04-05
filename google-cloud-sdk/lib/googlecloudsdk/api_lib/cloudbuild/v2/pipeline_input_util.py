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
from googlecloudsdk.core import log

_PIPELINERUN_UNSUPPORTED_FIELDS = [
    "podTemplate", "timeOuts", "taskRunSpec", "serviceAccountNames"
]
_TASKRUN_UNSUPPORTED_FIELDS = ["resources", "podTemplate"]
_WORKER_POOL_ANNOTATION = "cloudbuild.googleapis.com/worker-pool"
_MANAGED_SIDECARS_ANNOTATION = "cloudbuild.googleapis.com/managed-sidecars"


def TektonYamlDataToPipelineRun(data):
  """Convert Tekton yaml file into PipelineRun message."""
  _VersionCheck(data)
  _MetadataTransform(data)
  spec = data["spec"]
  if "pipelineSpec" in spec:
    _PipelineSpecTransform(spec["pipelineSpec"])
  elif "pipelineRef" not in spec:
    raise cloudbuild_exceptions.InvalidYamlError(
        "PipelineSpec or PipelineRef is required.")

  if "resources" in spec:
    spec.pop("resources")
    log.warning(
        "PipelineResources are dropped because they are deprecated: "
        "https://github.com/tektoncd/pipeline/blob/main/docs/resources.md")

  for workspace in spec.get("workspaces", []):
    _WorkspaceTransform(workspace)
  _ServiceAccountTransform(spec)
  input_util.ParamDictTransform(spec.get("params", []))

  discarded_fields = _CheckUnsupportedFields(spec,
                                             _PIPELINERUN_UNSUPPORTED_FIELDS)
  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(spec, messages.PipelineRun)

  input_util.UnrecognizedFields(schema_message)
  return schema_message, discarded_fields


def TektonYamlDataToTaskRun(data):
  """Convert Tekton yaml file into TaskRun message."""
  _VersionCheck(data)
  metadata = _MetadataTransform(data)
  spec = data["spec"]
  if "taskSpec" in spec:
    _TaskSpecTransform(spec["taskSpec"])
    managed_sidecars = _MetadataToSidecar(metadata)
    if managed_sidecars:
      spec["taskSpec"]["managedSidecars"] = managed_sidecars
  elif "taskRef" not in spec:
    raise cloudbuild_exceptions.InvalidYamlError(
        "TaskSpec or TaskRef is required.")

  for workspace in spec.get("workspaces", []):
    _WorkspaceTransform(workspace)
  _ServiceAccountTransform(spec)
  input_util.ParamDictTransform(spec.get("params", []))

  discarded_fields = _CheckUnsupportedFields(spec, _TASKRUN_UNSUPPORTED_FIELDS)
  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(spec, messages.TaskRun)

  input_util.UnrecognizedFields(schema_message)
  return schema_message, discarded_fields


def _VersionCheck(data):
  api_version = data.pop("apiVersion")
  if api_version != "tekton.dev/v1beta1":
    raise cloudbuild_exceptions.TektonVersionError()


def _MetadataTransform(data):
  """Helper funtion to transform the metadata."""
  spec = data["spec"]
  if not spec:
    raise cloudbuild_exceptions.InvalidYamlError("spec is empty.")

  metadata = data.pop("metadata")
  if not metadata:
    raise cloudbuild_exceptions.InvalidYamlError("Metadata is missing in yaml.")
  annotations, labels = metadata.get("annotations",
                                     {}), metadata.get("labels", {})
  if _WORKER_POOL_ANNOTATION not in annotations:
    raise cloudbuild_exceptions.InvalidYamlError(
        "Workerpool needs to be specified in metadata.annotations.")
  spec["workerPool"] = annotations[_WORKER_POOL_ANNOTATION]
  spec["annotations"] = annotations
  if labels:
    spec["labels"] = labels
  return metadata


def _MetadataToSidecar(metadata):
  if "annotations" in metadata and _MANAGED_SIDECARS_ANNOTATION in metadata[
      "annotations"]:
    return metadata["annotations"][_MANAGED_SIDECARS_ANNOTATION]
  return None


def _CheckUnsupportedFields(spec, unsupported_fields):
  discarded_fields = []
  for field in unsupported_fields:
    if field in spec:
      spec.pop(field)
      discarded_fields.append("spec." + field)
  return discarded_fields


def _PipelineSpecTransform(spec):
  for task in spec["tasks"]:
    _TaskTransform(task)
  if "finally" in spec:
    finally_tasks = spec.pop("finally")
    for task in finally_tasks:
      _TaskTransform(task)
    spec["finallyTasks"] = finally_tasks


def _TaskSpecTransform(spec):
  for param_spec in spec.get("params", []):
    input_util.ParamSpecTransform(param_spec)


def _TaskTransform(task):
  """Transform task message."""

  if "taskSpec" in task:
    task_spec = task.pop("taskSpec")
    _TaskSpecTransform(task_spec)
    managed_sidecars = _MetadataToSidecar(
        task_spec.pop("metadata")) if "metadata" in task_spec else []
    if managed_sidecars:
      task_spec["managedSidecars"] = managed_sidecars
    task["taskSpec"] = {"taskSpec": task_spec}
  whens = task.pop("when", [])
  for when in whens:
    if "operator" in when:
      when["expressionOperator"] = input_util.CamelToSnake(
          when.pop("operator")).upper()
  task["whenExpressions"] = whens
  input_util.ParamDictTransform(task.get("params", []))


def _ServiceAccountTransform(spec):
  if "serviceAccountName" in spec:
    spec["serviceAccount"] = spec.pop("serviceAccountName")


def _WorkspaceTransform(workspace):
  if "volumeClaimTemplate" in workspace and "spec" in workspace[
      "volumeClaimTemplate"] and "accessModes" in workspace[
          "volumeClaimTemplate"]["spec"]:
    access_modes = workspace["volumeClaimTemplate"]["spec"]["accessModes"]
    workspace["volumeClaimTemplate"]["spec"]["accessModes"] = list(
        map(lambda mode: input_util.CamelToSnake(mode).upper(), access_modes))
