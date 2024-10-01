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
import os
import re

from typing import Dict, List
from googlecloudsdk.command_lib.code import run_subprocess
from googlecloudsdk.core.util import files
import hcl2


def get_tfstate_information_per_member(
    iam_bindings: Dict[str, Dict[str, List[str]]],
    tfstate_json_list: List[Dict[str, str]],
    resource_name: str,
) -> Dict[str, List[Dict[str, str]]]:
  """Gets the TFState information for the given IAM bindings.

  Args:
    iam_bindings: IAM bindings for the resource.
    tfstate_json_list: List of TFState files.
    resource_name: Resource name for which the finding was generated.

  Returns:
    List of TFState information for the given IAM bindings.
  """
  tfstate_information: Dict[str, List[Dict[str, str]]] = {}
  for member, binding in iam_bindings.items():
    for tfstate_json in tfstate_json_list:
      if "ADD" in binding:
        for role in binding["ADD"]:
          resource_data = fetch_relevant_modules(
              tfstate_json, resource_name, role, member
          )
          if resource_data:
            if member not in tfstate_information:
              tfstate_information[member] = []
            tfstate_information[member].append(resource_data)
      if "REMOVE" in binding:
        for role in binding["REMOVE"]:
          resource_data = fetch_relevant_modules(
              tfstate_json, resource_name, role, member
          )
          if resource_data:
            if member not in tfstate_information:
              tfstate_information[member] = []
            tfstate_information[member].append(resource_data)
    return tfstate_information


def read_original_files_content(
    tf_files_paths: List[str],
)-> Dict[str, str]:
  """Reads the original files content.

  Args:
    tf_files_paths: List of TF files paths.

  Returns:
    Dict of file path and file content.
  """
  original_tf_files = dict[str, str]()
  for file_path in tf_files_paths:
    original_file_content = files.ReadFileContents(file_path)
    original_tf_files[file_path] = original_file_content
  return original_tf_files


def update_tf_files(
    response_dict: Dict[str, str],
):
  """Updates the TF files with the response dict.

  Args:
    response_dict: Response dict containing the updated TF files.

  """
  for file_path, file_data in response_dict.items():
    _ = files.WriteFileContents(file_path, file_data)


def validate_tf_files(
    response_dict: Dict[str, str]
) -> (bool, Dict[str, str]):
  """Validates the TFState information for the given IAM bindings.

  Args:
    response_dict: response dict containing the updated TF files.

  Returns:
    True if the response is valid, False otherwise.
    updated_response_dict: Updated response dict containing the original TF
    files.
  """
  original_tf_files = dict[str, str]()
  for file_path, file_data in response_dict.items():
    original_file_content = files.ReadFileContents(file_path)
    original_tf_files[file_path] = original_file_content
    try:
      _ = files.WriteFileContents(file_path, file_data)
      cmd = ["terraform", "fmt", "-write=true", file_path]
      run_subprocess.GetOutputLines(cmd, timeout_sec=25, show_stderr=False)
      response_dict[file_path] = files.ReadFileContents(file_path)
    except Exception as e:  # pylint: disable=broad-exception-caught
      update_tf_files(original_tf_files)
      return False, e
  cmd = ["terraform", "validate"]
  try:
    validate_output = run_subprocess.GetOutputLines(
        cmd, timeout_sec=25, show_stderr=False
    )
  except Exception as e:  # pylint: disable=broad-exception-caught
    update_tf_files(original_tf_files)
    return False, e
  update_tf_files(original_tf_files)
  if  re.search("Success", validate_output[0], re.IGNORECASE):
    return True, response_dict
  return False, None


def fetch_tfstate_json_from_dir(dir_path: str) -> str:
  """Fetches the TFState json for the given directory.

  Args:
    dir_path: The path of the directory to fetch the TFState files from.

  Returns:
    The json of the TFState file or None if there is an error.
  """
  try:
    os.chdir(dir_path)
    cmd = ["terraform", "init"]
    run_subprocess.GetOutputLines(cmd, timeout_sec=10)
  except Exception as _:  # pylint: disable=broad-exception-caught
    return ""
  try:
    cmd = ["terraform", "show", "-json"]
    tfstate_json = run_subprocess.GetOutputLines(cmd, timeout_sec=10)
  except Exception as _:  # pylint: disable=broad-exception-caught
    return ""
  return tfstate_json


def fetch_tfstate_json_from_file(file_path: str) -> str:
  """Fetches the TFState json for the given tfstate file path.

  Args:
    file_path: The path of the file to fetch the TFState json from.

  Returns:
    The json of the TFState files.
  """
  file = files.ReadFileContents(file_path)
  tfstate_json = hcl2.loads(file)
  return tfstate_json


def fetch_relevant_modules(
    tfstate_json: Dict[str, str],
    resource_name: str, role_name: str, member_name: str,
) -> str:
  """Fetches the relevant modules from the given TFState files."""
  resource_data = ""
  if (
      "values" not in tfstate_json
      or "root_module" not in tfstate_json["values"]
      or "resources" not in tfstate_json["values"]["root_module"]
  ):
    return resource_data
  for resource in tfstate_json["values"]["root_module"]["resources"]:
    if (
        "values" in resource
        and "member" in resource["values"]
        and "role" in resource["values"]
        and "project_id" in resource["values"]
        and resource["values"]["member"] == member_name
        and resource["values"]["role"] == role_name
        and resource["values"]["project_id"] == resource_name
    ):
      resource_data = resource
      break
  return resource_data


def find_tf_files(root_dir: str) -> List[str]:
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
        if not item.startswith("."):
          queue.append(item_path)
      elif os.path.isfile(item_path) and (
          item_path.endswith(".tf") or item_path.endswith(".tfvars")
          and not item_path.startswith(".")
      ):
        tf_files.append(item_path)
  return tf_files


def fetch_tfstate_list(
    tfstate_file_paths: List[str],
    root_dir: str,
) -> List[Dict[str, str]]:
  """Fetches the TFState list for the given TFState file paths.

  Args:
    tfstate_file_paths: List of TFState file paths.
    root_dir: The path of the root directory.

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
    return find_tfstate_jsons(root_dir)
  return tfstate_json_list


def find_tfstate_jsons(
    dir_path: str
) -> List[Dict[str, str]]:
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
      if not item.startswith("."):
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path):
          queue.append(item_path)
  return tfstate_jsons
