# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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

"""Shared util methods common to BQExports commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.scc import errors


def ValidateAndGetBigQueryExportId(args):
  """Validate BigQueryExport ID."""
  bq_export_id = args.BIG_QUERY_EXPORT
  pattern = re.compile("^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")
  if not pattern.match(bq_export_id):
    raise errors.InvalidSCCInputError(
        "BigQuery export id does not match the pattern "
        "'^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$'."
    )
  else:
    return bq_export_id


def ValidateAndGetBigQueryExportFullResourceName(args):
  """Validates BigQuery export full resource name."""
  bq_export_name = args.BIG_QUERY_EXPORT
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/bigQueryExports/[a-z]([a-z0-9-]{0,61}[a-z0-9])?$"
  )
  if not resource_pattern.match(bq_export_name):
    raise errors.InvalidSCCInputError(
        "BigQuery export must match the full resource name, or "
        "`--organization=`, `--folder=` or `--project=` must be provided."
    )
  return bq_export_name
