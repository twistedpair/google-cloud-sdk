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
"""Higher-level interfaces for Org Policy commands to inherit from."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import copy

from apitools.base.py import exceptions as api_exceptions
from googlecloudsdk.api_lib.orgpolicy import service as org_policy_service
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.org_policies import arguments
from googlecloudsdk.command_lib.org_policies import exceptions
from googlecloudsdk.command_lib.org_policies import utils
from googlecloudsdk.core import log
import six


class OrgPolicyGetAndUpdateCommand(
    six.with_metaclass(abc.ABCMeta, base.Command)):
  """Abstract class for Org Policy commands that need to get and then create or update a policy."""

  @staticmethod
  def Args(parser):
    arguments.AddConstraintArgToParser(parser)
    arguments.AddResourceFlagsToParser(parser)

  def __init__(self, cli, context):
    """Extends superclass method and add shared properties as well as a new property to toggle creation behavior.

    The new `disable_create` toggle controls behavior for when a policy cannot
    be found. If set to False (the default), the resource in question is
    created. If set to True, an exception is thrown.

    Args:
      cli: calliope.cli.CLI, The CLI object representing this command line tool.
      context: {str:object}, A set of key-value pairs that can be used for
        common initialization among commands.
    """
    super(OrgPolicyGetAndUpdateCommand, self).__init__(cli, context)

    self.org_policy_api = org_policy_service.OrgPolicyApi(self.ReleaseTrack())
    self.disable_create = False

  def Run(self, args):
    """Retrieves and then creates/updates a policy as needed.

    The following workflow is used:
       Retrieve policy through GetPolicy.
       If policy exists:
           Check policy to see if an update needs to be applied - it could be
           the case that the policy is already in the correct state.
           If policy does not need to be updated:
               No action.
           If new policy is empty:
               Delete policy through DeletePolicy.
           If policy needs to be updated:
               Update policy through UpdatePolicy.
       If policy does not exist:
           If new policy is empty:
               No action.
           If new policy is not empty:
               Create policy through CreatePolicy.

    Note that in the case that a policy exists, an error could be thrown by the
    backend if the policy is updated in between the GetPolicy request and the
    UpdatePolicy request. In the case that a policy does not exist, an error
    could be thrown if the policy did not initially exist but is created in
    between the GetPolicy request and the CreatePolicy request.

    Args:
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      The policy to return to the user after successful execution.
    """
    policy = self._GetPolicy(args)
    if not policy:
      return self._CreatePolicy(args)
    if policy.spec:
      for rule in policy.spec.rules:
        if rule.condition and args.command_path[-1] != 'reset':
          raise exceptions.OperationNotSupportedError(
              'Cannot be used to modify a conditional policy. Use set-policy instead.'
          )
    if self.ReleaseTrack() is base.ReleaseTrack.ALPHA:
      return self._UpdateOrDeletePolicyAlpha(policy, args)
    else:
      return self._UpdateOrDeletePolicy(policy, args)

  @abc.abstractmethod
  def UpdatePolicy(self, policy, args):
    """Updates the fields on the retrieved (or empty) policy before it is created/updated on the backend.

    Args:
      policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy
        object to be updated.
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      The updated policy.
    """
    raise NotImplementedError('Method has not been implemented.')

  def _GetPolicy(self, args):
    """Get the policy from the service.

    Args:
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      The retrieved policy, or None if not found.
    """
    name = utils.GetPolicyNameFromArgs(args)

    try:
      return self.org_policy_api.GetPolicy(name)
    except api_exceptions.HttpNotFoundError as e:
      if self.disable_create:
        raise e

  def _CreatePolicy(self, args):
    """Create the policy on the service if needed.

    Args:
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      The created policy.
    """
    name = utils.GetPolicyNameFromArgs(args)

    empty_policy = self.org_policy_api.BuildPolicy(name)
    new_policy = self.UpdatePolicy(empty_policy, args)

    if not new_policy.spec.rules and not new_policy.spec.inheritFromParent and not new_policy.spec.reset:
      return self.org_policy_api.messages.GoogleProtobufEmpty()

    create_response = self.org_policy_api.CreatePolicy(new_policy)
    log.CreatedResource(name, 'policy')
    return create_response

  def _UpdateOrDeletePolicyAlpha(self, policy, args):
    """Update or delete the policy on the service as needed.

    Args:
      policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy
        object to be updated.
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      If the policy is deleted, then messages.GoogleProtobufEmpty. If the policy
      is updated, then the updated policy.
    """
    policy_copy = copy.deepcopy(policy)
    policy_copy.spec.reset = None
    updated_policy = self.UpdatePolicy(policy_copy, args)
    if updated_policy == policy:
      return policy

    policy_name = utils.GetPolicyNameFromArgs(args)

    if not updated_policy.spec.rules and not updated_policy.spec.inheritFromParent and not updated_policy.spec.reset:
      delete_response = self.org_policy_api.DeletePolicy(policy_name)
      log.DeletedResource(policy_name, 'policy')
      return delete_response

    update_response = self.org_policy_api.UpdatePolicy(updated_policy)
    log.UpdatedResource(policy_name, 'policy')
    return update_response

  def _UpdateOrDeletePolicy(self, policy, args):
    """Update or delete the policy on the service as needed.

    Only updates the live spec if needed. The dryrun spec if exists, will remain
    unchanged.

    Args:
      policy: messages.GoogleCloudOrgpolicy{api_version}Policy, The policy
        object to be updated.
      args: argparse.Namespace, An object that contains the values for the
        arguments specified in the Args method.

    Returns:
      If the policy is deleted, then messages.GoogleProtobufEmpty. If the policy
      is updated, then the updated policy.
    """
    policy_copy = copy.deepcopy(policy)
    if not policy_copy.spec:
      policy_copy.spec = self.org_policy_api.CreateEmptyPolicySpec()
    policy_copy.spec.reset = None
    updated_policy = self.UpdatePolicy(policy_copy, args)
    if updated_policy == policy:
      return policy

    policy_name = utils.GetPolicyNameFromArgs(args)

    if (not updated_policy.spec.rules and
        not updated_policy.spec.inheritFromParent and
        not updated_policy.spec.reset and not updated_policy.dryRunSpec):
      delete_response = self.org_policy_api.DeletePolicy(policy_name)
      log.DeletedResource(policy_name, 'policy')
      return delete_response
    update_response = None
    if updated_policy.dryRunSpec:
      update_response = self.org_policy_api.UpdatePolicy(
          updated_policy, update_mask='policy.spec')
    else:
      update_response = self.org_policy_api.UpdatePolicy(updated_policy)
    log.UpdatedResource(policy_name, 'policy')
    return update_response
