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
"""Org Policy command utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy
import json

from apitools.base.py import encoding
from googlecloudsdk.api_lib.orgpolicy import service as org_policy_service
from googlecloudsdk.api_lib.orgpolicy import utils as org_policy_utils
from googlecloudsdk.command_lib.org_policies import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

CONSTRAINT_PREFIX = 'constraints/'


def GetConstraintFromArgs(args):
  """Returns the constraint from the user-specified arguments.

  A constraint has the following syntax: constraints/{constraint_name}.

  This handles both cases in which the user specifies and does not specify the
  constraint prefix.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.constraint.startswith(CONSTRAINT_PREFIX):
    return args.constraint

  return CONSTRAINT_PREFIX + args.constraint


def GetConstraintNameFromArgs(args):
  """Returns the constraint name from the user-specified arguments.

  This handles both cases in which the user specifies and does not specify the
  constraint prefix.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  if args.constraint.startswith(CONSTRAINT_PREFIX):
    return args.constraint[len(CONSTRAINT_PREFIX):]

  return args.constraint


def GetResourceFromArgs(args):
  """Returns the resource from the user-specified arguments.

  A resource has the following syntax:
  [organizations|folders|projects]/{resource_id}.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  resource_id = args.organization or args.folder or args.project

  if args.organization:
    resource_type = 'organizations'
  elif args.folder:
    resource_type = 'folders'
  else:
    resource_type = 'projects'

  return '{}/{}'.format(resource_type, resource_id)


def GetPolicyNameFromArgs(args):
  """Returns the policy name from the user-specified arguments.

  A policy name has the following syntax:
  [organizations|folders|projects]/{resource_id}/policies/{constraint_name}.

  Args:
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.
  """
  resource = GetResourceFromArgs(args)
  constraint_name = GetConstraintNameFromArgs(args)

  return '{}/policies/{}'.format(resource, constraint_name)


def GetMessageFromFile(filepath, message):
  """Returns a message populated from the JSON or YAML file on the specified filepath.

  Args:
    filepath: str, A local path to an object specification in JSON or YAML
      format.
    message: messages.Message, The message class to populate from the file.
  """
  file_contents = files.ReadFileContents(filepath)

  try:
    yaml_obj = yaml.load(file_contents)
    json_str = json.dumps(yaml_obj)
  except yaml.YAMLParseError:
    json_str = file_contents

  try:
    return encoding.JsonToMessage(message, json_str)
  except Exception as e:
    raise exceptions.InvalidInputError('Unable to parse file [{}]: {}.'.format(
        filepath, e))


def RemoveAllowedValuesFromPolicy(policy, args):
  """Removes the specified allowed values from all policy rules containing the specified condition.

  This first searches the policy for all rules that contain the specified
  condition. Then it searches for and removes the specified values from the
  lists of allowed values on those rules. Any modified rule with empty lists
  of allowed values and denied values after this operation is deleted.

  Args:
    policy: messages.GoogleCloudOrgpolicyV2alpha1Policy, The policy to be
      updated.
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.

  Returns:
    The updated policy.
  """
  new_policy = copy.deepcopy(policy)

  rules_to_update = org_policy_utils.GetMatchingRulesFromPolicy(
      new_policy, args.condition)
  if not rules_to_update:
    return policy

  # Remove the specified values from the list of allowed values for each rule.
  specified_values = set(args.value)
  for rule_to_update in rules_to_update:
    if rule_to_update.values is not None:
      rule_to_update.values.allowedValues = [
          value for value in rule_to_update.values.allowedValues
          if value not in specified_values
      ]

  return _DeleteRulesWithEmptyValues(new_policy, args)


def RemoveDeniedValuesFromPolicy(policy, args):
  """Removes the specified denied values from all policy rules containing the specified condition.

  This first searches the policy for all rules that contain the specified
  condition. Then it searches for and removes the specified values from the
  lists of denied values on those rules. Any modified rule with empty lists
  of allowed values and denied values after this operation is deleted.

  Args:
    policy: messages.GoogleCloudOrgpolicyV2alpha1Policy, The policy to be
      updated.
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.

  Returns:
    The updated policy.
  """
  new_policy = copy.deepcopy(policy)

  rules_to_update = org_policy_utils.GetMatchingRulesFromPolicy(
      new_policy, args.condition)
  if not rules_to_update:
    return policy

  # Remove the specified values from the list of denied values for each rule.
  specified_values = set(args.value)
  for rule_to_update in rules_to_update:
    if rule_to_update.values is not None:
      rule_to_update.values.deniedValues = [
          value for value in rule_to_update.values.deniedValues
          if value not in specified_values
      ]

  return _DeleteRulesWithEmptyValues(new_policy, args)


def _DeleteRulesWithEmptyValues(policy, args):
  """Delete any rule containing the specified condition with empty lists of allowed values and denied values and no other field set.

  Args:
    policy: messages.GoogleCloudOrgpolicyV2alpha1Policy, The policy to be
      updated.
    args: argparse.Namespace, An object that contains the values for the
      arguments specified in the Args method.

  Returns:
    The updated policy.
  """
  new_policy = copy.deepcopy(policy)

  org_policy_messages = org_policy_service.OrgPolicyMessages()

  condition = None
  if args.condition is not None:
    condition = org_policy_messages.GoogleTypeExpr(expression=args.condition)
  empty_values = org_policy_messages.GoogleCloudOrgpolicyV2alpha1PolicySpecPolicyRuleStringValues(
  )
  matching_empty_rule = org_policy_messages.GoogleCloudOrgpolicyV2alpha1PolicySpecPolicyRule(
      condition=condition, values=empty_values)
  new_policy.spec.rules = [
      rule for rule in new_policy.spec.rules if rule != matching_empty_rule
  ]

  return new_policy
