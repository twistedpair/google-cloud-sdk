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
"""Common flags for the SCC IAC Remediation commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base

FINDING_ORG_ID_FLAG = base.Argument(
    '--finding-org-id',
    help=""" Organization ID of the finding""",
    required=True
)

FINDING_NAME_FLAG = base.Argument(
    '--finding-name',
    help=""" Canonical name of the finding
        Format: projects/{proj_id}/sources/{src_id}/locations/global/findings/{finding_id} """,
    required=True
)

LLM_PROJ_ID_FLAG = base.Argument(
    '--project-id',
    help=""" Project ID of the LLM enabled project""",
    required=True
)

TFSTATE_FILE_PATHS_LIST_FLAG = base.Argument(
    '--tfstate-file-paths',
    help=""" Comma seperated list of paths to terraform state files.
        Format: /path/to/file1.tfstate,/path/to/file2.tfstate """,
    metavar='PATHS',
    type=arg_parsers.ArgList(),
    required=False,
)

GIT_CONFIG_FILE_PATH_FLAG = base.Argument(
    '--git-config-path',
    help=""" Path to the git config file in YAML format to raise the PR.
            Format: /path/to/file.yaml. Sample Config file:\n
              remote: origin
              main-branch-name: master
              branch-prefix: iac-remediation-
            """,
    metavar='GIT_SETTINGS',
    type=arg_parsers.YAMLFileContents(),
    required=True,
)
