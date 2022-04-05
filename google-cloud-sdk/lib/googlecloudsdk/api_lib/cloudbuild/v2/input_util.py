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

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_exceptions
from googlecloudsdk.core import yaml


def LoadYamlFromPath(path):
  try:
    data = yaml.load_path(path)
  except yaml.Error as e:
    raise cloudbuild_exceptions.ParserError(path, e.inner_error)
  if not yaml.dict_like(data):
    raise cloudbuild_exceptions.ParserError(path,
                                            "Could not parse as a dictionary.")
  return data


def CamelToSnake(data):
  return re.sub(
      pattern=r"([A-Z]+)", repl=r"_\1", string=data).lower().lstrip("_")


def UnrecognizedFields(message):
  unrecognized_fields = message.all_unrecognized_fields()
  if unrecognized_fields:
    raise cloudbuild_exceptions.InvalidYamlError(
        "Unrecognized fields in yaml: {f}".format(
            f=", ".join(unrecognized_fields)))


def ParamSpecTransform(param_spec):
  if "default" in param_spec:
    param_spec["default"] = ParamValueTransform(param_spec["default"])

  if "type" in param_spec:
    param_spec["type"] = param_spec["type"].upper()


def ParamDictTransform(params):
  for param in params:
    param["value"] = ParamValueTransform(param["value"])


def ParamValueTransform(param_value):
  if isinstance(param_value, str) or isinstance(param_value, float):
    return {"type": "STRING", "stringVal": str(param_value)}
  elif isinstance(param_value, list):
    return {"type": "ARRAY", "arrayVal": param_value}
  else:
    raise cloudbuild_exceptions.InvalidYamlError(
        "Unsupported param value type. {msg_type}".format(
            msg_type=type(param_value)))
