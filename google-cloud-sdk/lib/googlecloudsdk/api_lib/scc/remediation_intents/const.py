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
"""Constants used in the Remediation Intent related commands."""

TF_CMD_TIMEOUT = 10

TF_FMT_ERROR_MSG = (
    "Following error occurred while formatting the terraform file: {file_path}"
    "\n STDOUT: {stdout}"
    "\n STDERR: {stderr}"
)

TF_VALIDATE_ERROR_MSG = (
    "Following error occurred while validating the terraform files: "
    "\n STDOUT: {stdout}"
    "\n STDERR: {stderr}"
)
