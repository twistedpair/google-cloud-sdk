# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Declarative Request Hooks for Cloud SCC's BigQuery Exports."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.command_lib.scc.hooks import CleanUpUserInput
from googlecloudsdk.command_lib.scc.hooks import InvalidSCCInputError


def CreateBigQueryExportReqHook(ref, args, req):
  """Creates a BigQuery export."""
  del ref
  req.parent = _ValidateAndGetParent(args)
  if req.parent is not None:
    req.bigQueryExportId = _ValidateAndGetBigQueryExportId(args)
  else:
    bq_export_name = _ValidateAndGetBigQueryExportFullResourceName(args)
    req.bigQueryExportId = _GetBigQueryExportIdFromFullResourceName(
        bq_export_name)
    req.parent = _GetParentFromFullResourceName(bq_export_name)
  args.filter = ""
  return req


def DeleteBigQueryExportReqHook(ref, args, req):
  """Deletes a BigQuery export."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    bq_export_id = _ValidateAndGetBigQueryExportId(args)
    req.name = parent + "/bigQueryExports/" + bq_export_id
  else:
    bq_export_name = _ValidateAndGetBigQueryExportFullResourceName(args)
    req.name = bq_export_name
  return req


def GetBigQueryExportReqHook(ref, args, req):
  """Gets a BigQuery export."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    bq_export_id = _ValidateAndGetBigQueryExportId(args)
    req.name = parent + "/bigQueryExports/" + bq_export_id
  else:
    bq_export_name = _ValidateAndGetBigQueryExportFullResourceName(args)
    req.name = bq_export_name
  return req


def ListBigQueryExportsReqHook(ref, args, req):
  """Lists BigQuery exports."""
  del ref
  req.parent = _ValidateAndGetParent(args)
  return req


def UpdateBigQueryExportReqHook(ref, args, req):
  """Updates a BigQuery export."""
  del ref
  parent = _ValidateAndGetParent(args)
  if parent is not None:
    bq_export_id = _ValidateAndGetBigQueryExportId(args)
    req.name = parent + "/bigQueryExports/" + bq_export_id
  else:
    bq_export_name = _ValidateAndGetBigQueryExportFullResourceName(args)
    req.name = bq_export_name
  req.updateMask = CleanUpUserInput(req.updateMask)
  args.filter = ""
  return req


def _ValidateAndGetParent(args):
  """Validates parent."""
  if args.organization is not None:
    if "/" in args.organization:
      pattern = re.compile("^organizations/[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^organizations/[0-9]{1,19}$'.")
      else:
        return args.organization
    else:
      pattern = re.compile("^[0-9]{1,19}$")
      if not pattern.match(args.organization):
        raise InvalidSCCInputError(
            "Organization does not match the pattern '^[0-9]{1,19}$'.")
      else:
        return "organizations/" + args.organization

  if args.folder is not None:
    if "/" in args.folder:
      pattern = re.compile("^folders/.*$")
      if not pattern.match(args.folder):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^folders/.*$'.")
      else:
        return args.folder
    else:
      return "folders/" + args.folder

  if args.project is not None:
    if "/" in args.project:
      pattern = re.compile("^projects/.*$")
      if not pattern.match(args.project):
        raise InvalidSCCInputError(
            "When providing a full resource path, it must include the pattern "
            "'^projects/.*$'.")
      else:
        return args.project
    else:
      return "projects/" + args.project


def _ValidateAndGetBigQueryExportId(args):
  """Validate BigQueryExport ID."""
  bq_export_id = args.big_query_export
  pattern = re.compile("^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")
  if not pattern.match(bq_export_id):
    raise InvalidSCCInputError(
        "BigQiery export id does not match the pattern '^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$'."
    )
  else:
    return bq_export_id


def _ValidateAndGetBigQueryExportFullResourceName(args):
  """Validates BigQuery export full resource name."""
  bq_export_name = args.big_query_export
  resource_pattern = re.compile(
      "(organizations|projects|folders)/.*/bigQueryExports/[a-z]([a-z0-9-]{0,61}[a-z0-9])?$"
  )
  if not resource_pattern.match(bq_export_name):
    raise InvalidSCCInputError(
        "BigQuery export must match the full resource name, or `--organization=`, `--folder=` or `--project=` must be provided."
    )
  return bq_export_name


def _GetBigQueryExportIdFromFullResourceName(bq_export_name):
  """Gets BigQuery export id from the full resource name."""
  bq_export_components = bq_export_name.split("/")
  return bq_export_components[len(bq_export_components) - 1]


def _GetParentFromFullResourceName(bq_export_name):
  """Gets parent from the full resource name."""
  bq_export_components = bq_export_name.split("/")
  return bq_export_components[0] + "/" + bq_export_components[1]
