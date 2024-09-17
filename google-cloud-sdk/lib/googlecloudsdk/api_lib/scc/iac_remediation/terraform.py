# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Library for fetching TF Files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json
import os

from googlecloudsdk.command_lib.code import run_subprocess
from googlecloudsdk.core.util import files


def get_tfstate_information_per_member(
    iam_bindings: dict[str, dict[str, list[str]]],
    tfstate_json_list: list[json],
    resource_name: str,
) -> dict[str, list[json]]:
  """Gets the TFState information for the given IAM bindings.

  Args:
    iam_bindings: IAM bindings for the resource.
    tfstate_json_list: List of TFState files.
    resource_name: Resource name for which the finding was generated.

  Returns:
    List of TFState information for the given IAM bindings.
  """
  tfstate_information = dict[str, list[json]]()
  for member, binding in iam_bindings.items():
    for tfstate_json in tfstate_json_list:
      for role in binding["ADD"]:
        resource_data = fetch_relevant_modules(
            tfstate_json, resource_name, role, member
        )
        if resource_data:
          tfstate_information[member].append(resource_data)

      for role in binding["REMOVE"]:
        resource_data = fetch_relevant_modules(
            tfstate_json, resource_name, role, member
        )
        if resource_data:
          tfstate_information[member].append(resource_data)
    return tfstate_information


def validate_tf_files(response: str) -> bool:
  """Validates the TFState information for the given IAM bindings.

  Args:
    response: Response from the LLM.

  Returns:
    True if the response is valid, False otherwise.
  """
  json_response = json.loads(response)
  for _, file_data in json_response.items():
    output_file = files.WriteFileContents("updated_file.tf", file_data)
    cmd = ["terraform", "fmt", "-write=true", output_file]
    run_subprocess.GetOutputLines(cmd, timeout_sec=10)
    cmd = ["terraform", "validate", output_file]
    validate_output = run_subprocess.GetOutputLines(cmd, timeout_sec=10)
    if validate_output["valid"] == 0:
      return False
  return True


def fetch_tfstate_json_from_dir(dir_path: str) -> str:
  """Fetches the TFState json for the given directory.

  Args:
    dir_path: The path of the directory to fetch the TFState files from.

  Returns:
    The json of the TFState file.
  """
  os.chdir(dir_path)
  cmd = ["terraform", "init"]
  run_subprocess.GetOutputLines(cmd, timeout_sec=10)
  cmd = ["terraform", "show", "-json"]
  tfstate_json = run_subprocess.GetOutputLines(cmd, timeout_sec=10)
  return tfstate_json


def fetch_tfstate_json_from_file(file_path: str) -> str:
  """Fetches the TFState json for the given tfstate file path.

  Args:
    file_path: The path of the file to fetch the TFState json from.

  Returns:
    The json of the TFState files.
  """
  file = files.ReadFileContents(file_path)
  tfstate_json = json.load(file)
  return tfstate_json


def fetch_relevant_modules(
    tfstate_json: json, resource_name: str, role_name: str, member_name: str
) -> str:
  """Fetches the relevant modules from the given TFState files."""
  resource_data = ""
  for resource in tfstate_json["resources"][0]:
    if (
        resource["values"]["member"] == member_name
        and resource["values"]["role"] == role_name
        and resource["project_id"] == resource_name
    ):
      resource_data = resource
      break
  return resource_data


def find_tf_files(root_dir: str) -> list[str]:
  """Finds all the TF files in the given directory.

  Args:
    root_dir: The path of the directory to find the TF files in.

  Returns:
    A list of the TF files paths in the given directory.
  """
  tf_files = []
  queue = collections.deque([root_dir])
  while queue:
    current_dir = queue.popleft()
    for item in os.listdir(current_dir):
      item_path = os.path.join(current_dir, item)
      if os.path.isdir(item_path):
        queue.append(item_path)
      elif os.path.isfile(item_path) and item_path.endswith(".tf"):
        tf_files.append(item_path)
  return tf_files


def fetch_tfstate_list(
    tfstate_file_paths: list[str]| None,
) -> list[json]:
  """Fetches the TFState list for the given TFState file paths.

  Args:
    tfstate_file_paths: List of TFState file paths.

  Returns:
    List of TFState json.
  """
  tfstate_json_list = []
  if tfstate_file_paths:
    for tfstate_file_path in tfstate_file_paths:
      tfstate_json_list.append(
          fetch_tfstate_json_from_file(tfstate_file_path)
      )
  else:
    return find_tfstate_jsons(os.getcwd())
  return tfstate_json_list


def find_tfstate_jsons(
    dir_path: str
) -> str:
  """Finds the TFState jsons in the given directory.

  Args:
    dir_path: The path of the directory to find the TFState jsons in.

  Returns:
    List of TFState jsons.
  """
  tfstate_jsons = []
  queue = collections.deque([dir_path])
  while queue:
    current_dir = queue.popleft()
    tfstate_jsons.append(fetch_tfstate_json_from_dir(current_dir))
    for item in os.listdir(current_dir):
      item_path = os.path.join(current_dir, item)
      if os.path.isdir(item_path):
        queue.append(item_path)
        tfstate_jsons.append(item_path)
  return tfstate_jsons
