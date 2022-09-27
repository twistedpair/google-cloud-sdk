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
"""Utilities Service Directory endpoints API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.service_directory import base as sd_base
from googlecloudsdk.calliope import base


class RegistrationPoliciesClient(sd_base.ServiceDirectoryApiLibBase):
  """Client for registration poclicies in the Service Directory API."""

  def __init__(self, release_track=base.ReleaseTrack.BETA):
    super(RegistrationPoliciesClient, self).__init__(release_track)
    self.service = self.client.projects_locations_registrationPolicies

  def Create(self, location_ref, policy_yaml):
    """Registration policiy create request."""
    registration_policy_name = location_ref.RelativeName(
    ) + '/registrationPolicies/' + policy_yaml['metadata']['name']

    resource_policies = []
    for resource_policy_spec in policy_yaml['spec']['resource_policies']:
      policy_kind = None
      policy_selector = None
      # For MVP we only support kind=MIG and selector=*
      if 'kind' in resource_policy_spec:
        if resource_policy_spec['kind'] == 'MIG':
          policy_kind = self.msgs.ResourcePolicy.KindValueValuesEnum.KIND_MIG
      else:
        policy_kind = self.msgs.ResourcePolicy.KindValueValuesEnum.KIND_UNSPECIFIED
      if resource_policy_spec['selector'] == '*':
        policy_selector = self.msgs.Expr(expression='*')
      resource_policy = self.msgs.ResourcePolicy(
          kind=policy_kind, selector=policy_selector)
      resource_policies.append(resource_policy)

    namespace_name = None
    # For MVP, this is always false
    if 'namespace' in policy_yaml['metadata']:
      namespace_name = policy_yaml['metadata']['namespace']

    registration_policy_to_create = self.msgs.RegistrationPolicy(
        name=registration_policy_name,
        namespace=namespace_name,
        resourcePolicies=resource_policies)
    create_req = self.msgs.ServicedirectoryProjectsLocationsRegistrationPoliciesCreateRequest(
        parent=location_ref.RelativeName(),
        registrationPolicy=registration_policy_to_create,
        registrationPolicyId=policy_yaml['metadata']['name'])
    return self.service.Create(create_req)

  def Update(self, location_ref, policy_yaml):
    """Registration policiy create request."""
    registration_policy_name = location_ref.RelativeName(
    ) + '/registrationPolicies/' + policy_yaml['metadata']['name']

    # For MVP the only allowed field is resource_policies
    mask_parts = ['resource_policies']
    resource_policies = []
    for resource_policy_spec in policy_yaml['spec']['resource_policies']:
      policy_kind = None
      policy_selector = None
      # For MVP we only support kind=MIG and selector=*
      if 'kind' in resource_policy_spec:
        if resource_policy_spec['kind'] == 'MIG':
          policy_kind = self.msgs.ResourcePolicy.KindValueValuesEnum.KIND_MIG
      else:
        policy_kind = self.msgs.ResourcePolicy.KindValueValuesEnum.KIND_UNSPECIFIED
      if resource_policy_spec['selector'] == '*':
        policy_selector = self.msgs.Expr(expression='*')
      resource_policy = self.msgs.ResourcePolicy(
          kind=policy_kind, selector=policy_selector)
      resource_policies.append(resource_policy)

    namespace_name = None
    # For MVP, this is always false
    if 'namespace' in policy_yaml['metadata']:
      namespace_name = policy_yaml['metadata']['namespace']

    updated_registration_policy = self.msgs.RegistrationPolicy(
        name=registration_policy_name,
        namespace=namespace_name,
        resourcePolicies=resource_policies)
    update_req = self.msgs.ServicedirectoryProjectsLocationsRegistrationPoliciesPatchRequest(
        name=registration_policy_name,
        registrationPolicy=updated_registration_policy,
        updateMask=','.join(mask_parts))
    return self.service.Patch(update_req)

  def Delete(self, registration_policy_ref):
    """Registration policies delete request."""
    delete_req = self.msgs.ServicedirectoryProjectsLocationsRegistrationPoliciesDeleteRequest(
        name=registration_policy_ref.RelativeName())
    return self.service.Delete(delete_req)

  def Describe(self, registration_policy_ref):
    """Registration policies describe request."""
    describe_req = self.msgs.ServicedirectoryProjectsLocationsRegistrationPoliciesGetRequest(
        name=registration_policy_ref.RelativeName())
    return self.service.Get(describe_req)

  def List(self, location_ref, filter_=None, order_by=None, page_size=None):
    """Registration policies list request."""
    list_req = self.msgs.ServicedirectoryProjectsLocationsRegistrationPoliciesListRequest(
        parent=location_ref.RelativeName(),
        filter=filter_,
        orderBy=order_by,
        pageSize=page_size)
    return list_pager.YieldFromList(
        self.service,
        list_req,
        batch_size=page_size,
        field='registrationPolicies',
        batch_size_attribute='pageSize')
