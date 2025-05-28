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


IMPORT_TYPE = 'IMPORT'
EXPORT_TYPE = 'EXPORT'


def GenerateMetadataJob(args):
  """Generates a Metadata Job."""
  if args.type == IMPORT_TYPE:
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
  elif args.type == EXPORT_TYPE:
    module = dataplex_api.GetMessageModule()
    return module.GoogleCloudDataplexV1MetadataJob(
        labels=dataplex_api.CreateLabels(
            module.GoogleCloudDataplexV1MetadataJob, args
        ),
        type=module.GoogleCloudDataplexV1MetadataJob.TypeValueValuesEnum(
            args.type
        ),
        exportSpec=GenerateExportMetadataJobSpec(args),
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
          entryGroups=args.import_entry_groups
          if args.import_entry_groups
          else [],
          glossaries=args.import_glossaries if args.import_glossaries else [],
          entryTypes=args.import_entry_types
          if args.import_entry_types
          else [],
          aspectTypes=args.import_aspect_types
          if args.import_aspect_types
          else [],
          entryLinkTypes=args.import_entry_link_types
          if args.import_entry_link_types
          else [],
          referencedEntryScopes=args.import_referenced_entry_scopes
          if args.import_referenced_entry_scopes
          else [],
      ),
      sourceCreateTime=args.import_source_create_time,
      sourceStorageUri=args.import_source_storage_uri,
  )
  if hasattr(args, 'import_log_level') and args.IsSpecified('import_log_level'):
    import_job_spec.logLevel = module.GoogleCloudDataplexV1MetadataJobImportJobSpec.LogLevelValueValuesEnum(
        args.import_log_level
    )
  return import_job_spec


def GenerateExportMetadataJobSpec(args):
  """Generates a Metadata Export Job Spec."""
  module = dataplex_api.GetMessageModule()
  export_job_spec = module.GoogleCloudDataplexV1MetadataJobExportJobSpec(
      outputPath=args.export_output_path,
      scope=module.GoogleCloudDataplexV1MetadataJobExportJobSpecExportJobScope(
          entryTypes=args.export_entry_types,
          aspectTypes=args.export_aspect_types,
      ),
  )
  if hasattr(args, 'export_organization_level') and args.IsSpecified(
      'export_organization_level'
  ):
    export_job_spec.scope.organizationLevel = args.export_organization_level
  elif hasattr(args, 'export_projects') and args.IsSpecified('export_projects'):
    export_job_spec.scope.projects = args.export_projects
  elif hasattr(args, 'export_entry_groups') and args.IsSpecified(
      'export_entry_groups'
  ):
    export_job_spec.scope.entryGroups = args.export_entry_groups
  return export_job_spec


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_metadataJobs,
  )
