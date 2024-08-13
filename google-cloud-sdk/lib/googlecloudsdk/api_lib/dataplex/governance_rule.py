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
"""Client for interaction with Governance Rules API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.api_lib.util import messages as messages_util


def GenerateGovernanceRuleForCreateRequest(args):
  """Create Governance Rule Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1GovernanceRule(
      description=args.description,
      displayName=args.display_name,
      rlabels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GovernanceRule, args
      ),
      query=GenerateGovernanceRuleQuery(args),
      specs=GenerateGovernanceRuleSpecs(args),
      fields=GenerateGovernanceRuleFields(args),
  )

  if args.IsSpecified('rule_metadata_file'):
    rule_metadata_file = dataplex_api.ReadObject(args.rule_metadata_file)
    if rule_metadata_file is None:
      raise ValueError(
          'Rule metadata file is empty for Governance Rules create request.'
      )
    governance_rule_specs = messages_util.DictToMessageWithErrorCheck(
        dataplex_api.SnakeToCamelDict(rule_metadata_file),
        module.GoogleCloudDataplexV1GovernanceRuleSpecs,
    )
    governance_rule_fields = messages_util.DictToMessageWithErrorCheck(
        dataplex_api.SnakeToCamelDict(rule_metadata_file),
        module.GoogleCloudDataplexV1GovernanceRuleField,
    )
    if governance_rule_specs is None and governance_rule_fields is None:
      raise ValueError(
          'Either specs or field should be provided for Governance Rules create'
          ' request.'
      )
  else:
    raise ValueError(
        'Rule metadata file is not specified for Governance Rules create'
        ' request.'
    )

  return request


def GenerateGovernanceRuleForUpdateRequest(args):
  """Update Governance Rule Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1GovernanceRule(
      description=args.description,
      displayName=args.display_name,
      etag=args.etag,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GovernanceRule, args
      ),
      query=GenerateGovernanceRuleQuery(args),
      specs=GenerateGovernanceRuleSpecs(args),
      fields=GenerateGovernanceRuleFields(args),
  )
  return request


def GenerateGovernanceRuleQuery(args):
  """Generate Governance Rule Query From Arguments."""
  module = dataplex_api.GetMessageModule()
  governance_rule_query = module.GoogleCloudDataplexV1GovernanceRuleQuery()

  if args.IsSpecified('rule_metadata_file'):
    rule_metadata_file = dataplex_api.ReadObject(args.rule_metadata_file)
    if rule_metadata_file is not None:
      governance_rule_query = messages_util.DictToMessageWithErrorCheck(
          dataplex_api.SnakeToCamelDict(rule_metadata_file),
          module.GoogleCloudDataplexV1GovernanceRuleQuery,
      )
  return governance_rule_query


def GenerateGovernanceRuleSpecs(args):
  """Generate Governance Rule Specs From Arguments."""
  module = dataplex_api.GetMessageModule()
  governance_rule_specs = module.GoogleCloudDataplexV1GovernanceRuleSpecs()
  if args.IsSpecified('rule_metadata_file'):
    rule_specs_file = dataplex_api.ReadObject(args.rule_metadata_file)
    if rule_specs_file is not None:
      governance_rule_specs = messages_util.DictToMessageWithErrorCheck(
          dataplex_api.SnakeToCamelDict(rule_specs_file),
          module.GoogleCloudDataplexV1GovernanceRuleSpecs,
      )
  return governance_rule_specs


def GenerateGovernanceRuleFields(args):
  """Generate Governance Rule Fields From Arguments."""
  module = dataplex_api.GetMessageModule()
  governance_rule_fields = module.GoogleCloudDataplexV1GovernanceRuleField()
  if args.IsSpecified('rule_metadata_file'):
    rule_fields_file = dataplex_api.ReadObject(args.rule_metadata_file)
    if rule_fields_file is not None:
      governance_rule_fields = messages_util.DictToMessageWithErrorCheck(
          dataplex_api.SnakeToCamelDict(rule_fields_file),
          module.GoogleCloudDataplexV1GovernanceRuleField,
      )
  return governance_rule_fields


def GenerateUpdateMask(args):
  """Create Update Mask for Governance Rule."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  return update_mask


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_governanceRules,
  )
