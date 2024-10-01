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
"""Constants used in the IAC remediation commands."""

FINDINGS_API_NAME = 'securitycenter'
FINDINGS_API_VERSION = 'v1'

LLM_API_NAME = 'aiplatform'
LLM_API_VERSION = 'v1'

# LLM model parameters
LLM_DEFAULT_MODEL_NAME = 'gemini-1.5-pro-002'
TEMP = 0.1
TOPK = 40
TOPP = 0.95
MAX_OUTPUT_TOKENS = 8192

SUPPORTED_FINDING_CATEGORIES = (
    # go/keep-sorted start
    'IAM_ROLE_HAS_EXCESSIVE_PERMISSIONS',
    'IAM_ROLE_REPLACEMENT',
    'SERVICE_AGENT_GRANTED_BASIC_ROLE',
    'SERVICE_AGENT_ROLE_REPLACED_WITH_BASIC_ROLE',
    'UNUSED_IAM_ROLE',
    # go/keep-sorted end
)

SUPPORTED_IAM_MEMBER_COUNT_LIMIT = 4
