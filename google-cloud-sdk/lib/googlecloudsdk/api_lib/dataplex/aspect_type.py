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
"""Client for interaction with AspectType API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.command_lib.iam import iam_util


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_aspectTypes)


def AspectTypeSetIamPolicy(aspect_type_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsAspectTypesSetIamPolicyRequest(
      resource=aspect_type_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule()
      .GoogleIamV1SetIamPolicyRequest(policy=policy))
  return dataplex_api.GetClientInstance(
  ).projects_locations_aspectTypes.SetIamPolicy(set_iam_policy_req)


def AspectTypeGetIamPolicy(aspect_type_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsAspectTypesGetIamPolicyRequest(
      resource=aspect_type_ref.RelativeName())
  return dataplex_api.GetClientInstance(
  ).projects_locations_aspectTypes.GetIamPolicy(get_iam_policy_req)


def AspectTypeAddIamPolicyBinding(aspect_type_ref, member, role):
  """Add IAM policy binding request."""
  policy = AspectTypeGetIamPolicy(aspect_type_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)


def AspectTypeRemoveIamPolicyBinding(aspect_type_ref, member, role):
  """Remove IAM policy binding request."""
  policy = AspectTypeGetIamPolicy(aspect_type_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)


def AspectTypeSetIamPolicyFromFile(aspect_type_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file,
      dataplex_api.GetMessageModule().GoogleIamV1Policy)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)

