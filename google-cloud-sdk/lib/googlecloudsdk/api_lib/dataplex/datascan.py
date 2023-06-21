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


def GenerateData(args):
  """Generate Data From Arguments."""
  module = dataplex_api.GetMessageModule()

  if args.IsSpecified('data_source_entity'):
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
          dataqualityspec,
          module.GoogleCloudDataplexV1DataQualitySpec,
      )
  else:
    dataqualityspec = module.GoogleCloudDataplexV1DataQualitySpec()
  return dataqualityspec


def GenerateDataProfileSpec(args):
  """Generate DataProfileSpec From Arguments."""
  module = dataplex_api.GetMessageModule()

  if args.IsSpecified('data_profile_spec_file'):
    dataprofilespec = dataplex_api.ReadObject(args.data_profile_spec_file)
    if dataprofilespec is not None:
      dataprofilespec = messages_util.DictToMessageWithErrorCheck(
          dataprofilespec,
          module.GoogleCloudDataplexV1DataProfileSpec,
      )
  else:
    dataprofilespec = module.GoogleCloudDataplexV1DataProfileSpec()
  return dataprofilespec


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


def GenerateExecutionSpec(args):
  """Generate ExecutionSpec From Arguments."""
  module = dataplex_api.GetMessageModule()
  executionspec = module.GoogleCloudDataplexV1DataScanExecutionSpec(
      field=args.field if hasattr(args, 'field') else args.incremental_field,
      trigger=GenerateTrigger(args),
  )
  return executionspec


def GenerateDatascanForCreateRequest(args):
  """Create Datascan for Message Create Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1DataScan(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1DataScan, args
      ),
      data=GenerateData(args),
      executionSpec=GenerateExecutionSpec(args),
  )
  if args.scan_type == 'PROFILE':
    if args.IsSpecified('data_quality_spec_file'):
      raise ValueError(
          'Data Quality Spec file specified for Data Profile Scan.'
      )
    elif args.IsSpecified('data_profile_spec_file'):
      request.dataProfileSpec = GenerateDataProfileSpec(args)
    else:
      request.dataProfileSpec = module.GoogleCloudDataplexV1DataProfileSpec()
  elif args.scan_type == 'QUALITY':
    if args.IsSpecified('data_quality_spec_file'):
      request.dataQualitySpec = GenerateDataQualitySpec(args)
    else:
      raise ValueError(
          'If scan-type="QUALITY" , data-quality-spec-file is a required'
          ' argument.'
      )
  return request


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation, dataplex_api.GetClientInstance().projects_locations_dataScans
  )
