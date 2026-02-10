# -*- coding: utf-8 -*- #
# Copyright 2026 Google LLC. All Rights Reserved.
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
"""Exit codes for Cloud Run compose commands.

These exit codes are populated along with GcloudError exception.
Error codes within the ranges defined by comments (e.g. 101-110) but not
explicitly assigned are reserved for future use within that category.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

DEFAULT_EXIT_CODE = 100

# 101-110: EnvConfigError
COMPOSE_FILE_NOT_FOUND = 101
PROJECT_NOT_SET = 102
REGION_NOT_SET = 103
GO_BINARY_FAILED = 104
API_ENABLEMENT_FAILED = 105
PROJECT_NAME_MISSING = 106

# 111-115: SecretError
SECRET_CONFIG_INCOMPLETE = 111
SECRET_FILE_NOT_FOUND = 112
SECRET_IAM_FAILED = 113

# 116-125: StorageError
GCS_BUCKET_CREATE_FAILED = 116
GCS_BUCKET_IAM_FAILED = 117
GCS_UPLOAD_SOURCE_INVALID = 118
CONFIG_INVALID = 119
BIND_MOUNT_SOURCE_INVALID = 120

# 126-135: BuildError
BUILD_FAILED = 126
BUILD_SUBMISSION_ERROR = 127
BUILD_CONTEXT_INVALID = 128
BUILD_NO_BUILD_INVALID = 129

# 136-145: DeployError
DEPLOY_YAML_PARSE_FAILED = 136
DEPLOY_SERVICE_NAME_MISSING = 137
DEPLOY_API_ERROR = 138

UNKNOWN_ERROR = 199
