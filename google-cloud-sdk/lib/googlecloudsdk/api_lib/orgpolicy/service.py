# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Utilities for the Org Policy service."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from googlecloudsdk.api_lib.orgpolicy import utils
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base

ORG_POLICY_API_NAME = 'orgpolicy'
VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v2alpha1', base.ReleaseTrack.GA: 'v2'}


def GetApiVersion(release_track):
  """Returns the api version of the Org Policy service."""
  return VERSION_MAP.get(release_track)


def OrgPolicyClient(release_track):
  """Returns a client instance of the Org Policy service."""
  api_version = GetApiVersion(release_track)
  return apis.GetClientInstance(ORG_POLICY_API_NAME, api_version)


def OrgPolicyMessages(release_track):
  """Returns the messages module for the Org Policy service."""
  api_version = GetApiVersion(release_track)
  return apis.GetMessagesModule(ORG_POLICY_API_NAME, api_version)


def PolicyService(release_track):
  """Returns the service class for the Policy resource."""
  client = OrgPolicyClient(release_track)
  return client.policies


def ConstraintService(release_track):
  """Returns the service class for the Constraint resource."""
  client = OrgPolicyClient(release_track)
  return client.constraints


class OrgPolicyApi(object):
  """Base class for Org Policy API."""

  def __new__(cls, release_track):
    if release_track == base.ReleaseTrack.GA:
      return super(OrgPolicyApi, cls).__new__(OrgPolicyApiGA)
    elif release_track == base.ReleaseTrack.ALPHA:
      return super(OrgPolicyApi, cls).__new__(OrgPolicyApiAlpha)

  def __init__(self, release_track):
    api_version = GetApiVersion(release_track)
    self.client = apis.GetClientInstance(ORG_POLICY_API_NAME, api_version)
    self.messages = apis.GetMessagesModule(ORG_POLICY_API_NAME, api_version)

  @abc.abstractmethod
  def GetPolicy(self, name):
    pass

  @abc.abstractmethod
  def GetEffectivePolicy(self, name):
    pass

  @abc.abstractmethod
  def DeletePolicy(self, name):
    pass

  @abc.abstractmethod
  def ListPolicies(self, parent):
    pass

  @abc.abstractmethod
  def ListConstraints(self, parent):
    pass

  @abc.abstractmethod
  def CreatePolicy(self, policy):
    pass

  @abc.abstractmethod
  def UpdatePolicy(self, policy, update_mask=None):
    pass

  @abc.abstractmethod
  def CreateCustomConstraint(self, custom_constraint):
    pass

  @abc.abstractmethod
  def UpdateCustomConstraint(self, custom_constraint):
    pass

  @abc.abstractmethod
  def GetCustomConstraint(self, name):
    pass

  @abc.abstractmethod
  def CreateEmptyPolicySpec(self):
    pass

  @abc.abstractmethod
  def BuildPolicy(self, name):
    pass

  @abc.abstractmethod
  def BuildPolicySpecPolicyRule(self,
                                condition=None,
                                allow_all=None,
                                deny_all=None,
                                enforce=None,
                                values=None):
    pass

  @abc.abstractmethod
  def BuildPolicySpecPolicyRuleStringValues(self,
                                            allowed_values=(),
                                            denied_values=()):
    pass


class OrgPolicyApiGA(OrgPolicyApi):
  """Base class for all Org Policy V2GA API."""

  def GetPolicy(self, name):
    if name.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesGetRequest(
          name=name)
      return self.client.organizations_policies.Get(request)
    elif name.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesGetRequest(name=name)
      return self.client.folders_policies.Get(request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesGetRequest(name=name)
      return self.client.projects_policies.Get(request)

  def GetEffectivePolicy(self, name):
    if name.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesGetEffectivePolicyRequest(
          name=name)
      return self.client.organizations_policies.GetEffectivePolicy(request)
    elif name.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesGetEffectivePolicyRequest(
          name=name)
      return self.client.folders_policies.GetEffectivePolicy(request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesGetEffectivePolicyRequest(
          name=name)
      return self.client.projects_policies.GetEffectivePolicy(request)

  def DeletePolicy(self, name):
    if name.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesDeleteRequest(
          name=name)
      return self.client.organizations_policies.Delete(request)
    elif name.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesDeleteRequest(name=name)
      return self.client.folders_policies.Delete(request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesDeleteRequest(name=name)
      return self.client.projects_policies.Delete(request)

  def ListPolicies(self, parent):
    if parent.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesListRequest(
          parent=parent)
      return self.client.organizations_policies.List(request)
    elif parent.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesListRequest(parent=parent)
      return self.client.folders_policies.List(request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesListRequest(
          parent=parent)
      return self.client.projects_policies.List(request)

  def ListConstraints(self, parent):
    if parent.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsConstraintsListRequest(
          parent=parent)
      return self.client.organizations_constraints.List(request)
    elif parent.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersConstraintsListRequest(
          parent=parent)
      return self.client.folders_constraints.List(request)
    else:
      request = self.messages.OrgpolicyProjectsConstraintsListRequest(
          parent=parent)
      return self.client.projects_constraints.List(request)

  def CreatePolicy(self, policy):
    parent = utils.GetResourceFromPolicyName(policy.name)
    if parent.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesCreateRequest(
          parent=parent, googleCloudOrgpolicyV2Policy=policy)
      return self.client.organizations_policies.Create(request=request)
    elif parent.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesCreateRequest(
          parent=parent, googleCloudOrgpolicyV2Policy=policy)
      return self.client.folders_policies.Create(request=request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesCreateRequest(
          parent=parent, googleCloudOrgpolicyV2Policy=policy)
      return self.client.projects_policies.Create(request=request)

  def UpdatePolicy(self, policy, update_mask=None):
    if policy.name.startswith('organizations/'):
      request = self.messages.OrgpolicyOrganizationsPoliciesPatchRequest(
          name=policy.name,
          googleCloudOrgpolicyV2Policy=policy,
          updateMask=update_mask)
      return self.client.organizations_policies.Patch(request)
    elif policy.name.startswith('folders/'):
      request = self.messages.OrgpolicyFoldersPoliciesPatchRequest(
          name=policy.name,
          googleCloudOrgpolicyV2Policy=policy,
          updateMask=update_mask)
      return self.client.folders_policies.Patch(request)
    else:
      request = self.messages.OrgpolicyProjectsPoliciesPatchRequest(
          name=policy.name,
          googleCloudOrgpolicyV2Policy=policy,
          updateMask=update_mask)
      return self.client.projects_policies.Patch(request)

  def CreateCustomConstraint(self, custom_constraint):
    parent = utils.GetResourceFromPolicyName(custom_constraint.name)
    request = self.messages.OrgpolicyOrganizationsCustomConstraintsCreateRequest(
        parent=parent, googleCloudOrgpolicyV2CustomConstraint=custom_constraint)
    return self.client.organizations_customConstraints.Create(request=request)

  def UpdateCustomConstraint(self, custom_constraint):
    request = self.messages.OrgpolicyOrganizationsCustomConstraintsPatchRequest(
        googleCloudOrgpolicyV2CustomConstraint=custom_constraint,
        name=custom_constraint.name)
    return self.client.organizations_customConstraints.Patch(request)

  def GetCustomConstraint(self, name):
    request = self.messages.OrgpolicyOrganizationsCustomConstraintsGetRequest(
        name=name)
    return self.client.organizations_customConstraints.Get(request)

  def CreateEmptyPolicySpec(self):
    return self.messages.GoogleCloudOrgpolicyV2PolicySpec()

  def BuildPolicy(self, name):
    spec = self.messages.GoogleCloudOrgpolicyV2PolicySpec()
    return self.messages.GoogleCloudOrgpolicyV2Policy(name=name, spec=spec)

  def BuildPolicySpecPolicyRule(self,
                                condition=None,
                                allow_all=None,
                                deny_all=None,
                                enforce=None,
                                values=None):

    return self.messages.GoogleCloudOrgpolicyV2PolicySpecPolicyRule(
        condition=condition,
        allowAll=allow_all,
        denyAll=deny_all,
        enforce=enforce,
        values=values)

  def BuildPolicySpecPolicyRuleStringValues(self,
                                            allowed_values=(),
                                            denied_values=()):
    return self.messages.GoogleCloudOrgpolicyV2PolicySpecPolicyRuleStringValues(
        allowedValues=allowed_values, deniedValues=denied_values)


class OrgPolicyApiAlpha(OrgPolicyApi):
  """Base class for all Org Policy Alpha API."""

  def GetPolicy(self, name):
    request = self.messages.OrgpolicyPoliciesGetRequest(name=name)
    return self.client.policies.Get(request)

  def GetEffectivePolicy(self, name):
    request = self.messages.OrgpolicyPoliciesGetEffectivePolicyRequest(
        name=name)
    return self.client.policies.GetEffectivePolicy(request)

  def DeletePolicy(self, name):
    request = self.messages.OrgpolicyPoliciesDeleteRequest(name=name)
    return self.client.policies.Delete(request)

  def ListPolicies(self, parent):
    request = self.messages.OrgpolicyPoliciesListRequest(parent=parent)
    return self.client.policies.List(request)

  def ListConstraints(self, parent):
    request = self.messages.OrgpolicyConstraintsListRequest(parent=parent)
    return self.client.constraints.List(request)

  def CreatePolicy(self, policy):
    request = self.messages.OrgpolicyPoliciesCreateRequest(
        parent=utils.GetResourceFromPolicyName(policy.name),
        googleCloudOrgpolicyV2alpha1Policy=policy,
        constraint=utils.GetConstraintFromPolicyName(policy.name))
    return self.client.policies.Create(request)

  def UpdatePolicy(self, policy, update_mask=None):
    request = self.messages.OrgpolicyPoliciesPatchRequest(
        name=policy.name, googleCloudOrgpolicyV2alpha1Policy=policy)
    return self.client.policies.Patch(request)

  def BuildPolicy(self, name):
    spec = self.messages.GoogleCloudOrgpolicyV2alpha1PolicySpec()
    return self.messages.GoogleCloudOrgpolicyV2alpha1Policy(
        name=name, spec=spec)

  def BuildPolicySpecPolicyRule(self,
                                condition=None,
                                allow_all=None,
                                deny_all=None,
                                enforce=None,
                                values=None):
    return self.messages.GoogleCloudOrgpolicyV2alpha1PolicySpecPolicyRule(
        condition=condition,
        allowAll=allow_all,
        denyAll=deny_all,
        enforce=enforce,
        values=values)

  def BuildPolicySpecPolicyRuleStringValues(self,
                                            allowed_values=(),
                                            denied_values=()):
    return self.messages.GoogleCloudOrgpolicyV2alpha1PolicySpecPolicyRuleStringValues(
        allowedValues=allowed_values, deniedValues=denied_values)
