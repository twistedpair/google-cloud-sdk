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

import json
from typing import Dict, List

from googlecloudsdk.api_lib.scc.iac_remediation import prompt_format
from googlecloudsdk.core.util import files


def read_file(file_path: str) -> str:
  """Reads the TF file.

  Args:
    file_path: The path of the file to read.

  Returns:
    The contents of the file.
  """
  file = files.ReadFileContents(file_path)
  return file


def fetch_input_prompt(
    tfstate_information: str,
    iam_bindings: Dict[str, Dict[str, List[str]]],
    resource_name: str,
    tf_files: List[str],
    member: str,
) -> str:
  """Generates the prompt for iam policy.

  Args:
    tfstate_information: TFState information for the given IAM bindings.
    iam_bindings: IAM bindings for the resource.
    resource_name: Resource name for which the finding was generated.
    tf_files: List of TF files.
    member: Member for which the prompt is generated.

  Returns:
    Prompt string.
  """
  prompt_format_data = prompt_format.PromptFormatLookup()
  if "google_project_iam_policy" in tfstate_information:
    prompt_str = prompt_format_data.get_policy_prompt_template()
  else:
    prompt_str = prompt_format_data.get_binding_prompt_template()
  return _fetch_prompt(
      iam_bindings,
      tfstate_information,
      resource_name,
      tf_files,
      prompt_str,
      member,
  )


def _fetch_prompt(
    iam_bindings: Dict[str, Dict[str, List[str]]],
    tfstate_information: str,
    resource_name: str,
    tf_files: List[str],
    prompt_str: str,
    member: str,
) -> str:
  """Generates the prompt string.

  Args:
    iam_bindings: IAM bindings for the resource.
    tfstate_information: TFState information for the given IAM bindings.
    resource_name: Resource name for which the finding was generated.
    tf_files: List of TF files.
    prompt_str: Prompt file name.
    member: Member for which the prompt is generated.

  Returns:
    Prompt for iam policy.
  """
  iam_bindings_str = "member: " + member + "\n"
  for action, roles in iam_bindings.items():
    iam_bindings_str += action + " : \n" + json.dumps(roles) + "\n"
  prompt_str = prompt_str.replace(
      "{{iam_bindings}}", iam_bindings_str
  )
  prompt_str = prompt_str.replace(
      "{{tfstate_information}}", json.dumps(tfstate_information)
  )
  prompt_str = prompt_str.replace("{{resource_name}}", resource_name)
  files_str = ""
  for tf_file in tf_files:
    files_str += "FilePath= " + tf_file + "\n" + "```\n"
    files_str += read_file(tf_file) + "\n```\n"
  prompt_str = prompt_str.replace("{{input_tf_files}}", files_str)
  return prompt_str


def llm_response_parser(
    response: str
)-> Dict[str, str]:
  """Parses the LLM response.

  Args:
    response: LLM response.

  Returns:
    Dict of file path and file content.
  """
  response_dict = {}
  file_path = ""
  file_content = ""
  for line in response.splitlines():
    if line.startswith("FilePath"):
      if file_path:
        file_content = file_content.replace("```\n", "")
        file_content = file_content.replace("\n```", "")
        file_content = file_content.replace("```", "")
        response_dict[file_path] = file_content
      file_path = line.split("=")[1].strip()
      file_content = ""
    else:
      file_content += line + "\n"
  if file_path:
    file_content = file_content.replace("```\n", "")
    file_content = file_content.replace("\n```", "")
    file_content = file_content.replace("```", "")
    response_dict[file_path] = file_content
  return response_dict
