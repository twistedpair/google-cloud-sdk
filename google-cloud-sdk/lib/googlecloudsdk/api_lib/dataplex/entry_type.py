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
"""Client for interaction with EntryType API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.command_lib.iam import iam_util


def GenerateEntryTypeForCreateRequest(args):
  """Create Entry Type Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1EntryType(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(module.GoogleCloudDataplexV1EntryType,
                                       args),
      platform=args.platform,
      system=args.system,
      typeAliases=args.type_aliases,
      requiredAspects=GenerateEntryTypeRequiredAspects(args))

  return request


def GenerateEntryTypeForUpdateRequest(args):
  """Update Entry Type Request."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1EntryType(
      description=args.description,
      displayName=args.display_name,
      etag=args.etag,
      labels=dataplex_api.CreateLabels(module.GoogleCloudDataplexV1EntryType,
                                       args),
      platform=args.platform,
      system=args.system,
      typeAliases=args.type_aliases,
      requiredAspects=GenerateEntryTypeRequiredAspects(args))


def GenerateEntryTypeUpdateMask(args):
  """Create Update Mask for EntryType."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  if args.IsSpecified('platform'):
    update_mask.append('platform')
  if args.IsSpecified('system'):
    update_mask.append('system')
  if args.IsSpecified('type_aliases'):
    update_mask.append('typeAliases')
  if args.IsSpecified('required_aspects'):
    update_mask.append('requiredAspects')
  return update_mask


def GenerateEntryTypeRequiredAspects(args):
  """Create Required Aspects."""
  module = dataplex_api.GetMessageModule()
  required_aspects = []
  if args.required_aspects is not None:
    for required_aspect in args.required_aspects:
      required_aspects.append(
          module.GoogleCloudDataplexV1EntryTypeAspectInfo(
              type=required_aspect.get('type')
          )
      )
  return required_aspects


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_entryTypes)


def EntryTypeSetIamPolicy(entry_type_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsEntryTypesSetIamPolicyRequest(
      resource=entry_type_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule()
      .GoogleIamV1SetIamPolicyRequest(policy=policy))
  return dataplex_api.GetClientInstance(
  ).projects_locations_entryTypes.SetIamPolicy(set_iam_policy_req)


def EntryTypeGetIamPolicy(entry_type_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsEntryTypesGetIamPolicyRequest(
      resource=entry_type_ref.RelativeName())
  return dataplex_api.GetClientInstance(
  ).projects_locations_entryTypes.GetIamPolicy(get_iam_policy_req)


def EntryTypeAddIamPolicyBinding(entry_type_ref, member, role):
  """Add IAM policy binding request."""
  policy = EntryTypeGetIamPolicy(entry_type_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role)
  return EntryTypeSetIamPolicy(entry_type_ref, policy)


def EntryTypeRemoveIamPolicyBinding(entry_type_ref, member, role):
  """Remove IAM policy binding request."""
  policy = EntryTypeGetIamPolicy(entry_type_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return EntryTypeSetIamPolicy(entry_type_ref, policy)


def EntryTypeSetIamPolicyFromFile(entry_type_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file,
      dataplex_api.GetMessageModule().GoogleIamV1Policy)
  return EntryTypeSetIamPolicy(entry_type_ref, policy)

