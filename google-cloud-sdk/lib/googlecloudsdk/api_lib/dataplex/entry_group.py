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
"""Client for interaction with EntryGroup API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.command_lib.iam import iam_util


def GenerateEntryGroupForCreateRequest(args):
  """Create Entry Group Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1EntryGroup(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(module.GoogleCloudDataplexV1EntryGroup,
                                       args))
  return request


def GenerateEntryGroupForUpdateRequest(args):
  """Update Entry Group Request."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1EntryGroup(
      description=args.description,
      displayName=args.display_name,
      etag=args.etag,
      labels=dataplex_api.CreateLabels(module.GoogleCloudDataplexV1EntryGroup,
                                       args))


def GenerateEntryGroupUpdateMask(args):
  """Create Update Mask for EntryGroup."""
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
      dataplex_api.GetClientInstance().projects_locations_entryGroups)


def EntryGroupSetIamPolicy(entry_group_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsEntryGroupsSetIamPolicyRequest(
      resource=entry_group_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule()
      .GoogleIamV1SetIamPolicyRequest(policy=policy))
  return dataplex_api.GetClientInstance(
  ).projects_locations_entryGroups.SetIamPolicy(set_iam_policy_req)


def EntryGroupGetIamPolicy(entry_group_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsEntryGroupsGetIamPolicyRequest(
      resource=entry_group_ref.RelativeName())
  return dataplex_api.GetClientInstance(
  ).projects_locations_entryGroups.GetIamPolicy(get_iam_policy_req)


def EntryGroupAddIamPolicyBinding(entry_group_ref, member, role):
  """Add IAM policy binding request."""
  policy = EntryGroupGetIamPolicy(entry_group_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role)
  return EntryGroupSetIamPolicy(entry_group_ref, policy)


def EntryGroupRemoveIamPolicyBinding(entry_group_ref, member, role):
  """Remove IAM policy binding request."""
  policy = EntryGroupGetIamPolicy(entry_group_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return EntryGroupSetIamPolicy(entry_group_ref, policy)


def EntryGroupSetIamPolicyFromFile(entry_group_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file,
      dataplex_api.GetMessageModule().GoogleIamV1Policy)
  return EntryGroupSetIamPolicy(entry_group_ref, policy)

