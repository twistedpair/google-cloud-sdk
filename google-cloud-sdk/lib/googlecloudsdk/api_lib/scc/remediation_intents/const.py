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

# Max retry count for doing the remediation of the intents.
REMEDIATION_RETRY_COUNT = 3

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

BLOCK_SEPARATOR = "---------------------------------------------------------\n"

PR_FAILURE_MSG = (
    "Following error occurred while creating the PR: "
    "\n STDOUT: {stdout}"
    "\n STDERR: {stderr}"
)

IAM_RECOMMENDER_FINDINGS = (
    # go/keep-sorted start
    "IAM_ROLE_HAS_EXCESSIVE_PERMISSIONS",
    "IAM_ROLE_REPLACEMENT",
    "SERVICE_AGENT_GRANTED_BASIC_ROLE",
    "SERVICE_AGENT_ROLE_REPLACED_WITH_BASIC_ROLE",
    "UNUSED_IAM_ROLE",
    # go/keep-sorted end
)

FIREWALL_FINDINGS = (
    # go/keep-sorted start
    "OPEN_FIREWALL",
    # go/keep-sorted end
)

COMMIT_MSG = (
    "[Gemini Generated] [SCC] Remediation for finding: {finding_id}, Project:"
    " {project_id}, Category {category}"
)

PR_TITLE = (
    "[Gemini Generated] [SCC] Remediation for finding: {finding_id}, Project:"
    " {project_id}, Category {category}"
)

PR_DESC = (
    "Remediation explanation: {remediation_explanation}\n"
    "Last file modifiers:\n{file_modifiers}\n"
    "File owners:\n{file_owners}\n"
)
