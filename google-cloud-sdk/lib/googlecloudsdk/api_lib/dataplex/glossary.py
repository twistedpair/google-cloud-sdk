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
"""Client for interaction with Glossary API CRUD DATAPLEX."""


from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.command_lib.iam import iam_util


def GenerateGlossaryForCreateRequest(args):
  """Create Glossary Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1Glossary(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1Glossary, args
      ),
  )
  return request


def GenerateGlossaryForUpdateRequest(args):
  """Update Glossary Request."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1Glossary(
      description=args.description,
      displayName=args.display_name,
      etag=args.etag,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1Glossary, args
      ),
  )


def GenerateGlossaryCategoryForCreateRequest(args):
  """Create Glossary Category Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1GlossaryCategory(
      description=args.description,
      displayName=args.display_name,
      # parent represents the immediate parent of the category in glossary
      # hierarchy.
      parent=args.parent,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GlossaryCategory, args
      ),
  )
  return request


def GenerateGlossaryCategoryForUpdateRequest(args):
  """Update Glossary Category Requests."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1GlossaryCategory(
      description=args.description,
      displayName=args.display_name,
      parent=args.parent,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GlossaryCategory, args
      ),
  )


def GenerateGlossaryTermForCreateRequest(args):
  """Create Glossary Term Requests."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1GlossaryTerm(
      description=args.description,
      displayName=args.display_name,
      # parent represents the immediate parent of the term in glossary
      # hierarchy.
      parent=args.parent,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GlossaryTerm, args
      ),
  )
  return request


def GenerateGlossaryTermForUpdateRequest(args):
  """Update Glossary Term Requests."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1GlossaryTerm(
      description=args.description,
      displayName=args.display_name,
      parent=args.parent,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1GlossaryTerm, args
      ),
  )


def GenerateUpdateMask(args):
  """Creates Update Mask for Glossary."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  return update_mask


def GenerateCategoryUpdateMask(args):
  """Create Update Mask for Glossary Category."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  if args.IsSpecified('parent'):
    update_mask.append('parent')
  return update_mask


def GenerateTermUpdateMask(args):
  """Create Update Mask for Glossary Term."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  if args.IsSpecified('parent'):
    update_mask.append('parent')
  return update_mask


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation, dataplex_api.GetClientInstance().projects_locations_glossaries
  )


def GlossarySetIamPolicy(glossary_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule().DataplexProjectsLocationsGlossariesSetIamPolicyRequest(
      resource=glossary_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule().GoogleIamV1SetIamPolicyRequest(
          policy=policy
      ),
  )
  return dataplex_api.GetClientInstance().projects_locations_glossaries.SetIamPolicy(
      set_iam_policy_req
  )


def GlossaryGetIamPolicy(glossary_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule().DataplexProjectsLocationsGlossariesGetIamPolicyRequest(
      resource=glossary_ref.RelativeName()
  )
  return dataplex_api.GetClientInstance().projects_locations_glossaries.GetIamPolicy(
      get_iam_policy_req
  )


def GlossaryAddIamPolicyBinding(glossary_ref, member, role):
  """Add IAM policy binding request."""
  policy = GlossaryGetIamPolicy(glossary_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role
  )
  return GlossarySetIamPolicy(glossary_ref, policy)


def GlossaryRemoveIamPolicyBinding(glossary_ref, member, role):
  """Remove IAM policy binding request."""
  policy = GlossaryGetIamPolicy(glossary_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return GlossarySetIamPolicy(glossary_ref, policy)


def GlossarySetIamPolicyFromFile(glossary_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file, dataplex_api.GetMessageModule().GoogleIamV1Policy
  )
  return GlossarySetIamPolicy(glossary_ref, policy)
