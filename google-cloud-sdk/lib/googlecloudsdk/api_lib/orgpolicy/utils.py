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
"""Utilities for manipulating organization policies."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy

from googlecloudsdk.api_lib.orgpolicy import service
from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.command_lib.org_policies import exceptions


def GetConstraintFromPolicyName(policy_name):
  """Returns the constraint from the specified policy name.

  A constraint has the following syntax: constraints/{constraint_name}.

  Args:
    policy_name: The name of the policy. A policy name has the following syntax:
      [organizations|folders|projects]/{resource_id}/policies/{constraint_name}.
  """
  policy_name_tokens = _GetPolicyNameTokens(policy_name)
  return 'constraints/{}'.format(policy_name_tokens[3])


def GetResourceFromPolicyName(policy_name):
  """Returns the resource from the specified policy name.

  A resource has the following syntax:
  [organizations|folders|projects]/{resource_id}.

  Args:
    policy_name: The name of the policy. A policy name has the following syntax:
      [organizations|folders|projects]/{resource_id}/policies/{constraint_name}.
  """
  policy_name_tokens = _GetPolicyNameTokens(policy_name)
  return '{}/{}'.format(policy_name_tokens[0], policy_name_tokens[1])


def GetPolicyNameFromConstraintName(constraint_name):
  """Returns the associated policy name for the specified constraint name.

  A policy name has the following syntax:
  [organizations|folders|projects]/{resource_id}/policies/{constraint_name}.

  Args:
    constraint_name: The name of the constraint. A constraint name has the
      following syntax:
        [organizations|folders|projects]/{resource_id}/constraints/{constraint_name}.
  """
  constraint_name_tokens = _GetConstraintNameTokens(constraint_name)
  return '{}/{}/policies/{}'.format(constraint_name_tokens[0],
                                    constraint_name_tokens[1],
                                    constraint_name_tokens[3])


def GetMatchingRulesFromPolicy(policy, condition_expression=None):
  """Returns a list of rules on the policy that contain the specified condition expression.

  In the case that condition_expression is None, rules without conditions are
  returned.

  Args:
    policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy object
      to search.
    condition_expression: str, The condition expression to look for.
  """
  if condition_expression is None:
    condition_filter = lambda rule: rule.condition is None
  else:
    condition_filter = lambda rule: rule.condition is not None and rule.condition.expression == condition_expression

  return list(filter(condition_filter, policy.spec.rules))


def GetNonMatchingRulesFromPolicy(policy, condition_expression=None):
  """Returns a list of rules on the policy that do not contain the specified condition expression.

  In the case that condition_expression is None, rules with conditions are
  returned.

  Args:
    policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy object
      to search.
    condition_expression: str, The condition expression to look for.
  """
  if condition_expression is None:
    condition_filter = lambda rule: rule.condition is not None
  else:
    condition_filter = lambda rule: rule.condition is None or rule.condition.expression != condition_expression

  return list(filter(condition_filter, policy.spec.rules))


def GetPolicyMessageName(release_track):
  """Returns the organization policy message name based on the release_track."""
  api_version = service.GetApiVersion(release_track).capitalize()
  return 'GoogleCloudOrgpolicy' + api_version + 'Policy'


def _Uncapitalize(s):
  return s[0].lower() + s[1:]


def CreatePolicyCreateRequest(release_track, new_policy):
  """Returns an organization policy create request with the message API version related to the release_track."""
  messages = service.OrgPolicyMessages(release_track)
  policy_message_name = _Uncapitalize(GetPolicyMessageName(release_track))
  parent = GetResourceFromPolicyName(new_policy.name)

  if release_track == calliope_base.ReleaseTrack.ALPHA:
    return messages.OrgpolicyPoliciesCreateRequest(
        **{
            'constraint': GetConstraintFromPolicyName(new_policy.name),
            'parent': parent,
            policy_message_name: new_policy
        })

  return messages.OrgpolicyPoliciesCreateRequest(**{
      'parent': parent,
      policy_message_name: new_policy
  })


def CreatePolicyPatchRequest(release_track, policy_name, updated_policy):
  """Returns an organization policy patch request with the message API version related to the release_track."""
  messages = service.OrgPolicyMessages(release_track)
  policy_message_name = _Uncapitalize(GetPolicyMessageName(release_track))

  if release_track == calliope_base.ReleaseTrack.ALPHA:
    return messages.OrgpolicyPoliciesPatchRequest(**{
        'name': policy_name,
        policy_message_name: updated_policy
    })

  return updated_policy


def CreatePolicy(release_track, name):
  """Returns an organization policy with the message API version related to the release_track."""
  messages = service.OrgPolicyMessages(release_track)
  api_version = service.GetApiVersion(release_track).capitalize()
  policy_message_name = GetPolicyMessageName(release_track)
  policy_spec_message_name = 'GoogleCloudOrgpolicy' + api_version + 'PolicySpec'

  return getattr(messages, policy_message_name)(
      name=name, spec=getattr(messages, policy_spec_message_name)())


def CreatePolicySpecPolicyRule(release_track,
                               condition=None,
                               allow_all=None,
                               deny_all=None,
                               enforce=None,
                               values=None):
  """Returns an organization policy specification policy rule with the message API version related to the release_track."""
  messages = service.OrgPolicyMessages(release_track)
  api_version = service.GetApiVersion(release_track).capitalize()
  message_name = 'GoogleCloudOrgpolicy' + api_version + 'PolicySpecPolicyRule'
  return getattr(messages, message_name)(
      condition=condition,
      allowAll=allow_all,
      denyAll=deny_all,
      enforce=enforce,
      values=values)


def CreatePolicySpecPolicyRuleStringValues(release_track,
                                           allowed_values=(),
                                           denied_values=()):
  """Returns an organization policy specification policy rule with the message API version related to the release_track."""
  messages = service.OrgPolicyMessages(release_track)
  api_version = service.GetApiVersion(release_track).capitalize()
  message_name = 'GoogleCloudOrgpolicy' + api_version + 'PolicySpecPolicyRuleStringValues'
  return getattr(messages, message_name)(
      allowedValues=allowed_values, deniedValues=denied_values)


def CreateRuleOnPolicy(policy, release_track, condition_expression=None):
  """Creates a rule on the policy that contains the specified condition expression.

  In the case that condition_expression is None, a rule without a condition is
  created.

  Args:
    policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy object
      to be updated.
    release_track: release track of the command
    condition_expression: str, The condition expression to create a new rule
      with.

  Returns:
    The rule that was created as well as the new policy that includes this
    rule.
  """
  messages = service.OrgPolicyMessages(release_track)

  new_policy = copy.deepcopy(policy)

  condition = None
  if condition_expression is not None:
    condition = messages.GoogleTypeExpr(expression=condition_expression)

  new_rule = CreatePolicySpecPolicyRule(release_track, condition=condition)
  new_policy.spec.rules.append(new_rule)

  return new_rule, new_policy


def _GetPolicyNameTokens(policy_name):
  """Returns the individual tokens from the policy name.

  Args:
    policy_name: The name of the policy. A policy name has the following syntax:
      [organizations|folders|projects]/{resource_id}/policies/{constraint_name}.
  """
  policy_name_tokens = policy_name.split('/')
  if len(policy_name_tokens) != 4:
    raise exceptions.InvalidInputError(
        "Invalid policy name '{}': Name must be in the form [projects|folders|organizations]/{{resource_id}}/policies/{{constraint_name}}."
        .format(policy_name))
  return policy_name_tokens


def _GetConstraintNameTokens(constraint_name):
  """Returns the individual tokens from the constraint name.

  Args:
    constraint_name: The name of the constraint. A constraint name has the
      following syntax:
        [organizations|folders|projects]/{resource_id}/constraints/{constraint_name}.
  """
  constraint_name_tokens = constraint_name.split('/')
  if len(constraint_name_tokens) != 4:
    raise exceptions.InvalidInputError(
        "Invalid constraint name '{}': Name must be in the form [projects|folders|organizations]/{{resource_id}}/constraints/{{constraint_name}}."
        .format(constraint_name))
  return constraint_name_tokens
