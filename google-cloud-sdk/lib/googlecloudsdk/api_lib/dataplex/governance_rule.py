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

import os

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files
import six


def GenerateGovernanceRuleForCreateRequest(args):
  """Create Governance Rule Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1GovernanceRule(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GovernanceRule, args
      ),
      query=GenerateGovernanceRuleQuery(args),
      specs=GenerateGovernanceRuleSpecs(args),
      fields=GenerateGovernanceRuleFields(args),
  )

  if args.IsSpecified('rule_metadata_file'):
    rule_metadata_file = ReadRuleMetadataFile(args)
    if rule_metadata_file is None:
      raise ValueError(
          'Rule metadata file is empty for Governance Rules create request.'
      )
    if rule_metadata_file.get('query') is None:
      raise ValueError(
          'Query should be provided for Governance Rules create request.'
      )
    if GenerateGovernanceRuleSpecs(
        args
    ) is None and not GenerateGovernanceRuleFields(args):
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
  )
  if (
      args.IsSpecified('rule_metadata_file')
      and args.rule_metadata_file is not None
  ):
    query = GenerateGovernanceRuleQuery(args)
    specs = GenerateGovernanceRuleSpecs(args)
    fields = GenerateGovernanceRuleFields(args)
    if query is not None:
      request.query = query
    if specs is not None:
      request.specs = specs
    if fields:
      request.fields = fields
  return request


def ReadRuleMetadataFile(args):
  """Read Rule Metadata File."""
  if not os.path.exists(args.rule_metadata_file):
    raise exceptions.BadFileException(
        'No such file [{0}]'.format(args.rule_metadata_file)
    )
  if os.path.isdir(args.rule_metadata_file):
    raise exceptions.BadFileException(
        '[{0}] is a directory'.format(args.rule_metadata_file)
    )
  try:
    with files.FileReader(args.rule_metadata_file) as import_file:
      return yaml.load(import_file)
  except Exception as exp:
    exp_msg = getattr(exp, 'message', six.text_type(exp))
    msg = (
        'Unable to read Rule Metadata config from specified file '
        '[{0}] because [{1}]'.format(args.rule_metadata_file, exp_msg)
    )
    raise exceptions.BadFileException(msg)


def GenerateGovernanceRuleQuery(args):
  """Generate Governance Rule Query From Rule Metadata File."""
  module = dataplex_api.GetMessageModule()
  governance_rule_query = module.GoogleCloudDataplexV1GovernanceRuleQuery()
  rule_metadata_file = ReadRuleMetadataFile(args)
  if (
      rule_metadata_file is not None
      and rule_metadata_file.get('query') is not None
  ):
    governance_rule_query = messages_util.DictToMessageWithErrorCheck(
        dataplex_api.SnakeToCamelDict(rule_metadata_file.get('query')),
        module.GoogleCloudDataplexV1GovernanceRuleQuery,
        True,
    )
  return governance_rule_query


def GenerateGovernanceRuleSpecs(args):
  """Generate Governance Rule Specs From Rule Metadata File."""
  module = dataplex_api.GetMessageModule()
  governance_rule_specs = None
  rule_metadata_file = ReadRuleMetadataFile(args)
  if (
      rule_metadata_file is not None
      and rule_metadata_file.get('specs') is not None
  ):
    governance_rule_specs = messages_util.DictToMessageWithErrorCheck(
        dataplex_api.SnakeToCamelDict(rule_metadata_file.get('specs')),
        module.GoogleCloudDataplexV1GovernanceRuleSpecs,
    )
  return governance_rule_specs


def GenerateGovernanceRuleFields(args):
  """Generate Governance Rule Fields From Rule Metadata File."""
  module = dataplex_api.GetMessageModule()
  governance_rule_fields = []
  rule_metadata_file = ReadRuleMetadataFile(args)
  if (
      rule_metadata_file is not None
      and rule_metadata_file.get('fields') is not None
  ):
    fields = rule_metadata_file.get('fields')
    for field in fields:
      governance_rule_fields.append(
          messages_util.DictToMessageWithErrorCheck(
              dataplex_api.SnakeToCamelDict(field),
              module.GoogleCloudDataplexV1GovernanceRuleField,
          )
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

  if args.IsSpecified('rule_metadata_file'):
    if args.rule_metadata_file is not None:
      if GenerateGovernanceRuleQuery(args) is not None:
        update_mask.append('query')
      if GenerateGovernanceRuleSpecs(args) is not None:
        update_mask.append('specs')
      if GenerateGovernanceRuleFields(args):
        update_mask.append('fields')
  return update_mask


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_governanceRules,
  )


def SetIamPolicy(governance_rule_ref, policy):
  """Set Iam Policy request."""
  google_iam_v1_set_iam_policy_request = (
      dataplex_api.GetMessageModule().GoogleIamV1SetIamPolicyRequest(
          policy=policy
      )
  )
  set_iam_policy_req = dataplex_api.GetMessageModule().DataplexProjectsLocationsGovernanceRulesSetIamPolicyRequest(
      resource=governance_rule_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=google_iam_v1_set_iam_policy_request,
  )

  return dataplex_api.GetClientInstance().projects_locations_governanceRules.SetIamPolicy(
      set_iam_policy_req
  )


def GetIamPolicy(governance_rule_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule().DataplexProjectsLocationsGovernanceRulesGetIamPolicyRequest(
      resource=governance_rule_ref.RelativeName()
  )
  return dataplex_api.GetClientInstance().projects_locations_governanceRules.GetIamPolicy(
      get_iam_policy_req
  )


def AddIamPolicyBinding(governance_rule_ref, member, role):
  """Add IAM policy binding request."""
  policy = GetIamPolicy(governance_rule_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role
  )
  return SetIamPolicy(governance_rule_ref, policy)


def RemoveIamPolicyBinding(governance_rule_ref, member, role):
  """Remove IAM policy binding request."""
  policy = GetIamPolicy(governance_rule_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return SetIamPolicy(governance_rule_ref, policy)


def SetIamPolicyFromFile(governance_rule_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file, dataplex_api.GetMessageModule().GoogleIamV1Policy
  )
  return SetIamPolicy(governance_rule_ref, policy)
