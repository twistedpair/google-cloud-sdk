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

import re

from apitools.base.py import encoding
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_exceptions
from googlecloudsdk.api_lib.cloudbuild.v2 import client_util
from googlecloudsdk.core import log
from googlecloudsdk.core import yaml

_PIPELINERUN_UNSUPPORTED_FIELDS = [
    "podTemplate", "timeOuts", "taskRunSpec", "serviceAccountNames"
]
_TASKRUN_UNSUPPORTED_FIELDS = ["resources", "podTemplate"]
_WORKER_POOL_ANNOTATION = "cloudbuild.googleapis.com/worker-pool"


def LoadYamlFromPath(path):
  try:
    data = yaml.load_path(path)
  except yaml.Error as e:
    raise cloudbuild_exceptions.ParserError(path, e.inner_error)
  if not yaml.dict_like(data):
    raise cloudbuild_exceptions.ParserError(path,
                                            "Could not parse as a dictionary.")
  return data


def _CamelToSnake(data):
  return re.sub(
      pattern=r"([A-Z]+)", repl=r"_\1", string=data).lower().lstrip("_")


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

  _WorkspacesTransform(spec.get("workspaces", []))
  _ServiceAccountTransform(spec)
  _ParamDictTransform(spec.get("params", []))

  discarded_fields = _CheckUnsupportedFields(spec,
                                             _PIPELINERUN_UNSUPPORTED_FIELDS)
  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(spec, messages.PipelineRun)

  _UnrecognizedFields(schema_message)
  return schema_message, discarded_fields


def TektonYamlDataToTaskRun(data):
  """Convert Tekton yaml file into TaskRun message."""
  _VersionCheck(data)
  _MetadataTransform(data)
  spec = data["spec"]
  if "taskSpec" in spec:
    _TaskSpecTransform(spec["taskSpec"])
  elif "taskRef" not in spec:
    raise cloudbuild_exceptions.InvalidYamlError(
        "TaskSpec or TaskRef is required.")

  _WorkspacesTransform(spec.get("workspaces", []))
  _ServiceAccountTransform(spec)
  _ParamDictTransform(spec.get("params", []))

  discarded_fields = _CheckUnsupportedFields(spec, _TASKRUN_UNSUPPORTED_FIELDS)
  messages = client_util.GetMessagesModule()
  schema_message = encoding.DictToMessage(spec, messages.TaskRun)

  _UnrecognizedFields(schema_message)
  return schema_message, discarded_fields


def _UnrecognizedFields(message):
  unrecognized_fields = message.all_unrecognized_fields()
  if unrecognized_fields:
    raise cloudbuild_exceptions.InvalidYamlError(
        "Unrecognized fields in yaml: {f}".format(
            f=", ".join(unrecognized_fields)))


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
  _ParamSpecsTransform(spec.get("params", []))


def _TaskTransform(task):
  if "taskSpec" in task:
    task_spec = task.pop("taskSpec")
    task["taskSpec"] = {"taskSpec": task_spec}
  whens = task.pop("when", [])
  for when in whens:
    if "operator" in when:
      when["expressionOperator"] = _CamelToSnake(when.pop("operator")).upper()
  task["whenExpressions"] = whens
  _ParamDictTransform(task.get("params", []))


def _ParamDictTransform(params):
  for param in params:
    param["value"] = _ParamValueTransform(param["value"])


def _ParamSpecsTransform(param_specs):
  for param in param_specs:
    if "default" in param:
      param["default"] = _ParamValueTransform(param["default"])
    if "type" in param:
      param["type"] = param["type"].upper()


def _ParamValueTransform(param_value):
  if isinstance(param_value, str):
    return {"type": "STRING", "stringVal": param_value}
  elif isinstance(param_value, list):
    return {"type": "ARRAY", "arrayVal": param_value}
  else:
    raise cloudbuild_exceptions.InvalidYamlError(
        "Unsupported param value type. {msg_type}".format(
            msg_type=type(param_value)))


def _WorkspacesTransform(workspaces):
  for workspace in workspaces:
    if "volumeClaimTemplate" in workspace and "spec" in workspace[
        "volumeClaimTemplate"] and "accessModes" in workspace[
            "volumeClaimTemplate"]["spec"]:
      access_modes = workspace["volumeClaimTemplate"]["spec"]["accessModes"]
      workspace["volumeClaimTemplate"]["spec"]["accessModes"] = list(
          map(lambda mode: _CamelToSnake(mode).upper(), access_modes))


def _ServiceAccountTransform(spec):
  if "serviceAccountName" in spec:
    spec["serviceAccount"] = spec.pop("serviceAccountName")
