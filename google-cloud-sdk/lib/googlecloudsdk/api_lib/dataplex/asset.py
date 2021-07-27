# -*- coding: utf-8 -*- #
# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Client for interaction with Asset API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.command_lib.iam import iam_util


def SetIamPolicy(asset_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsLakesZonesAssetsSetIamPolicyRequest(
      resource=asset_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule()
      .GoogleIamV1SetIamPolicyRequest(policy=policy))
  return dataplex_api.GetClientInstance(
  ).projects_locations_lakes_zones_assets.SetIamPolicy(set_iam_policy_req)


def GetIamPolicy(asset_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsLakesZonesAssetsGetIamPolicyRequest(
      resource=asset_ref.RelativeName())
  return dataplex_api.GetClientInstance(
  ).projects_locations_lakes_zones_assets.GetIamPolicy(get_iam_policy_req)


def AddIamPolicyBinding(asset_ref, member, role):
  """Add IAM policy binding request."""
  policy = GetIamPolicy(asset_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role)
  return SetIamPolicy(asset_ref, policy)


def RemoveIamPolicyBinding(zone_ref, member, role):
  """Remove IAM policy binding request."""
  policy = GetIamPolicy(zone_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return SetIamPolicy(zone_ref, policy)


def SetIamPolicyFromFile(asset_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file,
      dataplex_api.GetMessageModule().GoogleIamV1Policy)
  return SetIamPolicy(asset_ref, policy)


def GenerateAssetForCreateRequest(description, display_name, labels,
                                  resource_name, resource_spec_type,
                                  creation_policy, deletion_policy,
                                  discovery_spec_enabled, schedule):
  """Create Asset for Message Create Requests."""
  module = dataplex_api.GetMessageModule()
  resource_spec = module.GoogleCloudDataplexV1AssetResourceSpec
  return module.GoogleCloudDataplexV1Asset(
      description=description,
      displayName=display_name,
      labels=labels,
      resourceSpec=module.GoogleCloudDataplexV1AssetResourceSpec(
          name=resource_name,
          type=resource_spec.TypeValueValuesEnum(resource_spec_type),
          creationPolicy=resource_spec.CreationPolicyValueValuesEnum(
              creation_policy),
          deletionPolicy=resource_spec.DeletionPolicyValueValuesEnum(
              deletion_policy)),
      discoverySpec=module.GoogleCloudDataplexV1AssetDiscoverySpec(
          enabled=discovery_spec_enabled, schedule=schedule))


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_lakes_zones_assets)

