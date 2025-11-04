# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
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
"""Client for interaction with Datascan API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.command_lib.iam import iam_util


def GenerateData(args: parser_extensions.Namespace):
  """Generate Data From Arguments."""
  module = dataplex_api.GetMessageModule()
  if args.IsKnownAndSpecified('data_source_entity'):
    data = module.GoogleCloudDataplexV1DataSource(
        entity=args.data_source_entity
    )
  else:
    data = module.GoogleCloudDataplexV1DataSource(
        resource=args.data_source_resource
    )
  return data


def GenerateDataQualitySpec(args):
  """Generate DataQualitySpec From Arguments."""
  module = dataplex_api.GetMessageModule()

  if args.IsSpecified('data_quality_spec_file'):
    dataqualityspec = dataplex_api.ReadObject(args.data_quality_spec_file)
    if dataqualityspec is not None:
      dataqualityspec = messages_util.DictToMessageWithErrorCheck(
          dataplex_api.SnakeToCamelDict(dataqualityspec),
          module.GoogleCloudDataplexV1DataQualitySpec,
      )
  else:
    dataqualityspec = module.GoogleCloudDataplexV1DataQualitySpec()
  return dataqualityspec


def GenerateDataProfileSpec(args: parser_extensions.Namespace):
  """Generate DataProfileSpec From Arguments."""
  module = dataplex_api.GetMessageModule()

  if args.IsSpecified('data_profile_spec_file'):
    dataprofilespec = dataplex_api.ReadObject(args.data_profile_spec_file)
    if dataprofilespec is not None:
      dataprofilespec = messages_util.DictToMessageWithErrorCheck(
          dataplex_api.SnakeToCamelDict(dataprofilespec),
          module.GoogleCloudDataplexV1DataProfileSpec,
      )
  else:
    exclude_fields, include_fields, sampling_percent, row_filter = [None] * 4
    if args.IsKnownAndSpecified('exclude_field_names'):
      exclude_fields = (
          module.GoogleCloudDataplexV1DataProfileSpecSelectedFields(
              fieldNames=list(
                  val.strip() for val in args.exclude_field_names.split(',')
              )
          )
      )
    if args.IsKnownAndSpecified('include_field_names'):
      include_fields = (
          module.GoogleCloudDataplexV1DataProfileSpecSelectedFields(
              fieldNames=list(
                  val.strip() for val in args.include_field_names.split(',')
              )
          )
      )
    if args.IsKnownAndSpecified('sampling_percent'):
      sampling_percent = float(args.sampling_percent)
    if args.IsKnownAndSpecified('row_filter'):
      row_filter = args.row_filter
    dataprofilespec = module.GoogleCloudDataplexV1DataProfileSpec(
        excludeFields=exclude_fields,
        includeFields=include_fields,
        samplingPercent=sampling_percent,
        rowFilter=row_filter,
    )
    if args.IsKnownAndSpecified('export_results_table'):
      dataprofilespec.postScanActions = module.GoogleCloudDataplexV1DataProfileSpecPostScanActions(
          bigqueryExport=module.GoogleCloudDataplexV1DataProfileSpecPostScanActionsBigQueryExport(
              resultsTable=args.export_results_table
          )
      )
  return dataprofilespec


def GenerateDataDiscoverySpec(args: parser_extensions.Namespace):
  """Generate DataDiscoverySpec From Arguments."""
  module = dataplex_api.GetMessageModule()

  datadiscoveryspec = module.GoogleCloudDataplexV1DataDiscoverySpec()

  # BigQuery publishing config.
  datadiscoveryspec.bigqueryPublishingConfig = (
      module.GoogleCloudDataplexV1DataDiscoverySpecBigQueryPublishingConfig()
  )
  if args.IsKnownAndSpecified('bigquery_publishing_connection'):
    datadiscoveryspec.bigqueryPublishingConfig.connection = (
        args.bigquery_publishing_connection
    )
  if args.IsKnownAndSpecified('bigquery_publishing_table_type'):
    datadiscoveryspec.bigqueryPublishingConfig.tableType = module.GoogleCloudDataplexV1DataDiscoverySpecBigQueryPublishingConfig.TableTypeValueValuesEnum(
        args.bigquery_publishing_table_type
    )
  if args.IsKnownAndSpecified('bigquery_publishing_dataset_project'):
    datadiscoveryspec.bigqueryPublishingConfig.project = (
        args.bigquery_publishing_dataset_project
    )
  if args.IsKnownAndSpecified('bigquery_publishing_dataset_location'):
    datadiscoveryspec.bigqueryPublishingConfig.location = (
        args.bigquery_publishing_dataset_location
    )

  datadiscoveryspec.storageConfig = (
      module.GoogleCloudDataplexV1DataDiscoverySpecStorageConfig()
  )
  if args.IsKnownAndSpecified('storage_include_patterns'):
    datadiscoveryspec.storageConfig.includePatterns = (
        args.storage_include_patterns
    )
  if args.IsKnownAndSpecified('storage_exclude_patterns'):
    datadiscoveryspec.storageConfig.excludePatterns = (
        args.storage_exclude_patterns
    )

  # CSV options.
  datadiscoveryspec.storageConfig.csvOptions = (
      module.GoogleCloudDataplexV1DataDiscoverySpecStorageConfigCsvOptions()
  )
  if args.IsKnownAndSpecified('csv_delimiter'):
    datadiscoveryspec.storageConfig.csvOptions.delimiter = args.csv_delimiter
  if args.IsKnownAndSpecified('csv_header_row_count'):
    try:
      datadiscoveryspec.storageConfig.csvOptions.headerRows = int(
          args.csv_header_row_count
      )
    except ValueError:
      raise ValueError(
          'csv_header_row_count must be an integer, but got'
          f' {args.csv_header_row_count}'
      )
  if args.IsKnownAndSpecified('csv_quote_character'):
    datadiscoveryspec.storageConfig.csvOptions.quote = args.csv_quote_character
  if args.IsKnownAndSpecified('csv_encoding'):
    datadiscoveryspec.storageConfig.csvOptions.encoding = args.csv_encoding
  if args.IsKnownAndSpecified('csv_disable_type_inference'):
    datadiscoveryspec.storageConfig.csvOptions.typeInferenceDisabled = (
        args.csv_disable_type_inference
    )

  # JSON options.
  datadiscoveryspec.storageConfig.jsonOptions = (
      module.GoogleCloudDataplexV1DataDiscoverySpecStorageConfigJsonOptions()
  )
  if args.IsKnownAndSpecified('json_encoding'):
    datadiscoveryspec.storageConfig.jsonOptions.encoding = args.json_encoding
  if args.IsKnownAndSpecified('json_disable_type_inference'):
    datadiscoveryspec.storageConfig.jsonOptions.typeInferenceDisabled = (
        args.json_disable_type_inference
    )

  return datadiscoveryspec


def GenerateDataDocumentationSpec():
  """Generate DataDocumentationSpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1DataDocumentationSpec()


def GenerateSchedule(args):
  """Generate DataQualitySpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  schedule = module.GoogleCloudDataplexV1TriggerSchedule(cron=args.schedule)
  return schedule


def GenerateTrigger(args):
  """Generate DataQualitySpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  trigger = module.GoogleCloudDataplexV1Trigger()
  if args.IsSpecified('schedule'):
    trigger.schedule = GenerateSchedule(args)
  else:
    trigger.onDemand = module.GoogleCloudDataplexV1TriggerOnDemand()
  return trigger


def GenerateExecutionSpecForCreateRequest(args):
  """Generate ExecutionSpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  if hasattr(args, 'field'):
    field = args.field
  else:
    field = (
        args.incremental_field if hasattr(args, 'incremental_field') else None
    )
  executionspec = module.GoogleCloudDataplexV1DataScanExecutionSpec(
      field=field,
      trigger=GenerateTrigger(args),
  )
  return executionspec


def GenerateExecutionSpecForUpdateRequest(args):
  """Generate ExecutionSpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  executionspec = module.GoogleCloudDataplexV1DataScanExecutionSpec(
      trigger=GenerateTrigger(args),
  )
  return executionspec


def GenerateUpdateMask(args: parser_extensions.Namespace):
  """Create Update Mask for Datascan."""
  update_mask = []
  args_to_mask = {
      'description': 'description',
      'display_name': 'displayName',
      'labels': 'labels',
      'on_demand': 'executionSpec.trigger.onDemand',
      'schedule': 'executionSpec.trigger.schedule',
  }
  args_to_mask_attr = {
      'data_profile_spec_file': 'dataProfileSpec',
      'data_quality_spec_file': 'dataQualitySpec',
      'row_filter': 'dataProfileSpec.rowFilter',
      'sampling_percent': 'dataProfileSpec.samplingPercent',
      'include_field_names': 'dataProfileSpec.includeFields',
      'exclude_field_names': 'dataProfileSpec.excludeFields',
      'bigquery_publishing_table_type': (
          'dataDiscoverySpec.bigqueryPublishingConfig.tableType'
      ),
      'bigquery_publishing_connection': (
          'dataDiscoverySpec.bigqueryPublishingConfig.connection'
      ),
      'bigquery_publishing_dataset_location': (
          'dataDiscoverySpec.bigqueryPublishingConfig.location'
      ),
      'bigquery_publishing_dataset_project': (
          'dataDiscoverySpec.bigqueryPublishingConfig.project'
      ),
      'storage_include_patterns': (
          'dataDiscoverySpec.storageConfig.includePatterns'
      ),
      'storage_exclude_patterns': (
          'dataDiscoverySpec.storageConfig.excludePatterns'
      ),
      'csv_delimiter': 'dataDiscoverySpec.storageConfig.csvOptions.delimiter',
      'csv_header_row_count': (
          'dataDiscoverySpec.storageConfig.csvOptions.headerRows'
      ),
      'csv_quote_character': 'dataDiscoverySpec.storageConfig.csvOptions.quote',
      'csv_encoding': 'dataDiscoverySpec.storageConfig.csvOptions.encoding',
      'csv_disable_type_inference': (
          'dataDiscoverySpec.storageConfig.csvOptions.typeInferenceDisabled'
      ),
      'json_encoding': 'dataDiscoverySpec.storageConfig.jsonOptions.encoding',
      'json_disable_type_inference': (
          'dataDiscoverySpec.storageConfig.jsonOptions.typeInferenceDisabled'
      ),
  }

  for arg, val in args_to_mask.items():
    if args.IsSpecified(arg):
      update_mask.append(val)

  for arg, val in args_to_mask_attr.items():
    if args.IsKnownAndSpecified(arg):
      update_mask.append(val)
  return update_mask


def GenerateDatascanForCreateRequest(args: parser_extensions.Namespace):
  """Create Datascan for Message Create Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1DataScan(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1DataScan, args
      ),
      data=GenerateData(args),
      executionSpec=GenerateExecutionSpecForCreateRequest(args),
  )
  if args.scan_type == 'PROFILE':
    if args.IsKnownAndSpecified('data_quality_spec_file'):
      raise ValueError(
          'Data quality spec file specified for data profile scan.'
      )
    else:
      request.dataProfileSpec = GenerateDataProfileSpec(args)
  elif args.scan_type == 'QUALITY':
    if args.IsKnownAndSpecified('data_profile_spec_file'):
      raise ValueError(
          'Data profile spec file specified for data quality scan.'
      )
    elif args.IsSpecified('data_quality_spec_file'):
      request.dataQualitySpec = GenerateDataQualitySpec(args)
    else:
      raise ValueError(
          'If scan-type="QUALITY" , data-quality-spec-file is a required'
          ' argument.'
      )
  elif args.scan_type == 'DISCOVERY':
    request.dataDiscoverySpec = GenerateDataDiscoverySpec(args)
  elif args.scan_type == 'DOCUMENTATION':
    request.dataDocumentationSpec = GenerateDataDocumentationSpec()
  return request


def GenerateDatascanForUpdateRequest(args: parser_extensions.Namespace):
  """Create Datascan for Message Update Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1DataScan(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1DataScan, args
      ),
      executionSpec=GenerateExecutionSpecForUpdateRequest(args),
  )
  if args.scan_type == 'PROFILE':
    if args.IsKnownAndSpecified('data_quality_spec_file'):
      raise ValueError(
          'Data quality spec file specified for data profile scan.'
      )
    request.dataProfileSpec = GenerateDataProfileSpec(args)
  elif args.scan_type == 'QUALITY':
    if args.IsKnownAndSpecified('data_profile_spec_file'):
      raise ValueError(
          'Data profile spec file specified for data quality scan.'
      )
    elif args.IsSpecified('data_quality_spec_file'):
      request.dataQualitySpec = GenerateDataQualitySpec(args)
    else:
      request.dataQualitySpec = module.GoogleCloudDataplexV1DataQualitySpec()
  elif args.scan_type == 'DISCOVERY':
    request.dataDiscoverySpec = GenerateDataDiscoverySpec(args)
  elif args.scan_type == 'DOCUMENTATION':
    request.dataDocumentationSpec = GenerateDataDocumentationSpec()
  return request


def SetIamPolicy(datascan_ref, policy):
  """Set IAM Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule().DataplexProjectsLocationsDataScansSetIamPolicyRequest(
      resource=datascan_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule().GoogleIamV1SetIamPolicyRequest(
          policy=policy
      ),
  )
  return dataplex_api.GetClientInstance().projects_locations_dataScans.SetIamPolicy(
      set_iam_policy_req
  )


def SetIamPolicyFromFile(datascan_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file, dataplex_api.GetMessageModule().GoogleIamV1Policy
  )
  return SetIamPolicy(datascan_ref, policy)


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation, dataplex_api.GetClientInstance().projects_locations_dataScans
  )
