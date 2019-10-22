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

"""Declarative hooks for Cloud Identity Groups CLI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.identity import cloudidentity_client as ci_client
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.identity.groups import hooks as groups_hooks

_CIG_API_VERSION = 'v1alpha1'


# request hooks
def SetEntityKey(unused_ref, args, request):
  """Set EntityKey in group resource.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if hasattr(request, 'member_email') and args.IsSpecified('member_email'):
    request.membership.preferredMemberKey.id = args.member_email

  return request


def SetPageSize(unused_ref, args, request):
  """Set page size to request.pageSize.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if hasattr(args, 'page_size') and args.IsSpecified('page_size'):
    request.pageSize = int(args.page_size)

  return request


def SetMembershipParent(unused_ref, args, request):
  """Set resource name to request.parent.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if args.IsSpecified('group_email'):
    # Resource name example: groups/03qco8b4452k99t
    request.parent = groups_hooks.ConvertEmailToResourceName(
        args.group_email, 'group_email')

  return request


def SetMembershipResourceName(unused_ref, args, request):
  """Set membership resource name to request.name.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  name = ''
  if args.IsSpecified('group_email') and args.IsSpecified('member_email'):
    name = ConvertEmailToMembershipResourceName(
        args.group_email, args.member_email, 'group_email', 'member_email')
  else:
    raise exceptions.InvalidArgumentException(
        'Must specify group-email and member-email argument.')

  if hasattr(request, 'group'):
    request.group.name = name
  else:
    request.name = name

  return request


def SetMembershipUpdateMask(unused_ref, args, request):
  """Set the update mask on the request based on the args.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  Raises:
    InvalidArgumentException: If no fields are specified to update.
  """
  update_mask = []

  if args.IsSpecified('roles'):
    update_mask.append('roles')

  if (args.IsSpecified('expiration')
      or args.IsSpecified('clear_expiration')):
    update_mask.append('expiry_detail')

  # TODO(b/139939605): Add PosixGroups check once it is added.

  if not update_mask:
    raise exceptions.InvalidArgumentException(
        'Must specify at least one field mask.')

  request.updateMask = ','.join(update_mask)

  return request


# processor hooks
def ReformatExpiryDetail(expiration):
  """Reformat expiration string to ExpiryDetail object.

  Args:
    expiration: expiration string.
  Returns:
    ExpiryDetail object that contains the expiration data.
  """

  messages = ci_client.GetMessages()
  expiration_ts = expiration
  return messages.ExpiryDetail(expireTime=expiration_ts)


def ReformatMembershipRoles(roles_list):
  """Reformat roles string to MembershipRoles object list.

  Args:
    roles_list: list of roles in a string format.
  Returns:
    List of MembershipRoles object.
  """

  messages = ci_client.GetMessages()
  roles = []
  for role in roles_list:
    new_membership_role = messages.MembershipRole(name=role)
    roles.append(new_membership_role)

  return roles


# private methods
def ConvertEmailToMembershipResourceName(
    group_email, member_email, group_arg_name, member_arg_name):
  """Convert email to membership resource name.

  Args:
    group_email: group email
    member_email: member email
    group_arg_name: argument/parameter name related to group info
    member_arg_name: argument/parameter name related to member info

  Returns:
    Membership Id (e.g. groups/11zu0gzc3tkdgn2/memberships/1044279104595057141)

  """

  # Resource name example: groups/03qco8b4452k99t
  group_id = groups_hooks.ConvertEmailToResourceName(
      group_email, group_arg_name)

  lookup_membership_name_resp = ci_client.LookupMembershipName(
      group_id, member_email)

  if 'name' in lookup_membership_name_resp:
    return lookup_membership_name_resp['name']

  # If there is no group exists (or deleted) for the given group email,
  # print out an error message.
  parameter_name = group_arg_name + ', ' + member_arg_name
  error_msg = ('There is no such a membership associated with the specified '
               'arguments:{}, {}').format(group_email, member_email)

  raise exceptions.InvalidArgumentException(parameter_name, error_msg)
