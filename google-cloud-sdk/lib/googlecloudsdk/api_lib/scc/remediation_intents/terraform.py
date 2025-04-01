# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Module for interacting with Terraform files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import json
import os
import subprocess
from typing import Dict, List, Any

from googlecloudsdk.api_lib.scc.remediation_intents import const
from googlecloudsdk.api_lib.scc.remediation_intents import parsers
from googlecloudsdk.command_lib.code import run_subprocess
from googlecloudsdk.command_lib.scc.remediation_intents import errors
from googlecloudsdk.core.util import files


def fetch_tf_files(root_dir: str) -> Dict[str, str]:
  """Fetches all the relevant TF files in the given directory recusively and returns a dictionary of the file paths and contents.

  Args:
    root_dir: The path of the directory to find the TF files in.

  Returns:
    A dictionary of the TF files in the given directory {path: contents}.
  """
  tf_files: Dict[str, str] = {}
  dir_queue = collections.deque([root_dir])

  # Algo: Recursively search the items in the current directory, if it's a
  # directory, add it to the queue. If it is a tf file, read it to the
  # dictionary.
  while dir_queue:
    current_dir = dir_queue.popleft()
    for item in os.listdir(current_dir):
      item_path = os.path.join(current_dir, item)
      if os.path.isdir(item_path):
        if not item.startswith("."):  # Ignore hidden directories
          dir_queue.append(item_path)
      elif os.path.isfile(item_path) and (
          item_path.endswith(".tf") or item_path.endswith(".tfvars")
          and not item_path.startswith(".")
      ):
        tf_files[item_path] = files.ReadFileContents(item_path)
  return tf_files


def fetch_tfstate(dir_path: str)-> json:
  """Fetches the TfState json for the given directory and returns in json format.

  Args:
    dir_path: The path of the directory to fetch the TfState data from.

  Returns:
    The json of the TfState data or throws an exception if there is an error.
  """
  # Fetching tfState data is a two step process:
  # 1. Run terraform init command to initialize the terraform directory.
  # 2. Run terraform show command to fetch the tfstate data.
  try:
    org_dir = os.getcwd()
    os.chdir(dir_path)
    cmd = ["terraform", "init"]  # Step 1
    run_subprocess.GetOutputLines(cmd, timeout_sec=const.TF_CMD_TIMEOUT)
  except Exception as e:
    raise errors.TfStateFetchingError(str(e))
  try:
    cmd = ["terraform", "show", "-json"]  # Step 2
    tfstate_data = run_subprocess.GetOutputLines(
        cmd, timeout_sec=const.TF_CMD_TIMEOUT, strip_output=True
    )
    os.chdir(org_dir)
    return json.loads(tfstate_data[0])
  except Exception as e:
    raise errors.TfStateFetchingError(str(e))


def validate_tf_files(modified_tf_files: Dict[str, str]) -> str:
  """Validates the given TF files and returns the appropriate error message if any.

  Args:
    modified_tf_files: The dictionary of the modified TF files {path: contents}.

  Returns:
    The error message if any in string format, otherwise None.
  """
  # Save the original contents of just the modified TF files.
  original_tf_files: Dict[str, str] = {}
  for file_path, _ in modified_tf_files.items():
    original_tf_files[file_path] = files.ReadFileContents(file_path)

  # Format the modified TF files one by one.
  for file_path, file_content in modified_tf_files.items():
    files.WriteFileContents(file_path, file_content)
    try:
      cmd = ["terraform", "fmt", "-write=true", file_path]
      _ = subprocess.run(
          cmd,
          text=True,
          check=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
      )
    except subprocess.CalledProcessError as e:
      # Restore the original contents of the files in case of error.
      _ = [
          files.WriteFileContents(fp, fc)
          for fp, fc in original_tf_files.items()
      ]

      return const.TF_FMT_ERROR_MSG.format(
          file_path=file_path, stdout=e.stdout, stderr=e.stderr
      )

  # Validate the modified TF files by running terraform validate command.
  cmd = ["terraform", "validate"]
  try:
    _ = subprocess.run(
        cmd,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
  except subprocess.CalledProcessError as e:
    # Restore the original contents of the files in case of error.
    _ = [
        files.WriteFileContents(fp, fc)
        for fp, fc in original_tf_files.items()
    ]

    return const.TF_VALIDATE_ERROR_MSG.format(
        stdout=e.stdout, stderr=e.stderr
    )

  # Restore the original contents of the files finally.
  _ = [files.WriteFileContents(fp, fc) for fp, fc in original_tf_files.items()]
  return None


def get_resources_from_tfstate(
    tfstate_json: Dict[str, Any],
) -> List[Dict[str, Any]]:
  """Traverses the TfState json and returns a list of resources in json format.

  Args:
    tfstate_json: The json of the TfState data. Structure:
                  {
                      "values": {
                          "root_module": {
                              "resources": [ ... ],  # List of resources
                              "child_modules": [     # List of nested modules
                                  {
                                      "resources": [ ... ],
                                      "child_modules": [ ... ]
                                  }
                              ]
                          }
                      }
                  }
  Returns:
    A list of json objects, each representing a resource in the TfState.
    or an empty list if there are no resources in the TfState or if the TfState
    is not in the expected format.
  """

  all_resources = []
  # Recursive function to traverse the tfstate data and extract the resources.
  def traverse(module: Dict[str, Any]):
    if "resources" in module:
      all_resources.extend(module["resources"])
    if "child_modules" in module:
      for child in module["child_modules"]:
        traverse(child)

  root_module = tfstate_json.get("values", {}).get("root_module", {})
  traverse(root_module)
  return all_resources


def parse_tf_file(dir_path: str, finding_data) -> str:
  """Parses the tfstate file for the given finding.

  Args:
    dir_path: The path of the directory to parse the tfstate file from.
    finding_data: SCC Finding data in form of class
      (securityposture.messages.Finding).

  Returns:
    The structured data depending on the finding category, in string format. If
    the finding category is not supported, returns an empty string.
  """
  tftstate_json = fetch_tfstate(dir_path)
  resources = get_resources_from_tfstate(tftstate_json)

  # Mapping of finding category to the parser function.
  parser_map = {  # category: parser_function
      **{
          category: parsers.iam_recommender_parser
          for category in const.IAM_RECOMMENDER_FINDINGS
      },
      **{
          category: parsers.firewall_parser
          for category in const.FIREWALL_FINDINGS
      },
  }
  # Each parser function takes the list of resources and the finding data as
  # input and returns the structured data in string format.
  if finding_data.category in parser_map:
    return parser_map[finding_data.category](resources, finding_data)
  return ""
