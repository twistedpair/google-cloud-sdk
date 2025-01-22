# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Client for interaction with Metadata Job API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.calliope import exceptions


def GenerateMetadataJob(args):
  """Generates a Metadata Job."""
  if args.type == 'IMPORT':
    module = dataplex_api.GetMessageModule()
    return module.GoogleCloudDataplexV1MetadataJob(
        labels=dataplex_api.CreateLabels(
            module.GoogleCloudDataplexV1MetadataJob, args
        ),
        type=module.GoogleCloudDataplexV1MetadataJob.TypeValueValuesEnum(
            args.type
        ),
        importSpec=GenerateImportMetadataJobSpec(args),
    )
  raise exceptions.BadArgumentException(
      '--type', 'Current type is not supported in Gcloud.'
  )


def GenerateImportMetadataJobSpec(args):
  """Generates a Metadata Import Job Spec."""
  module = dataplex_api.GetMessageModule()
  import_job_spec = module.GoogleCloudDataplexV1MetadataJobImportJobSpec(
      aspectSyncMode=module.GoogleCloudDataplexV1MetadataJobImportJobSpec.AspectSyncModeValueValuesEnum(
          args.import_aspect_sync_mode
      ),
      entrySyncMode=module.GoogleCloudDataplexV1MetadataJobImportJobSpec.EntrySyncModeValueValuesEnum(
          args.import_entry_sync_mode
      ),
      scope=module.GoogleCloudDataplexV1MetadataJobImportJobSpecImportJobScope(
          entryGroups=args.import_entry_groups,
          entryTypes=args.import_entry_types,
          aspectTypes=args.import_aspect_types,
      ),
      sourceCreateTime=args.import_source_create_time,
      sourceStorageUri=args.import_source_storage_uri,
  )
  if hasattr(args, 'import_log_level') and args.IsSpecified('import_log_level'):
    import_job_spec.logLevel = module.GoogleCloudDataplexV1MetadataJobImportJobSpec.LogLevelValueValuesEnum(
        args.import_log_level
    )
  return import_job_spec


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_metadataJobs,
  )
