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

from apitools.base.py import encoding

from googlecloudsdk.api_lib.cloudresourcemanager import organizations
from googlecloudsdk.api_lib.identity import cloudidentity_client as ci_client
from googlecloudsdk.calliope import exceptions

_CIG_API_VERSION = 'v1alpha1'


# request hooks
def SetParent(unused_ref, args, request):
  """Set obfuscated customer id to request.group.parent or request.parent.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if args.IsSpecified('organization'):
    customer_id = ConvertOrgIdToObfuscatedCustomerId(args.organization)
    if hasattr(request, 'group'):
      request.group.parent = 'customerId/' + customer_id
    else:
      request.parent = 'customerId/' + customer_id

  return request


def SetEntityKey(unused_ref, args, request):
  """Set EntityKey to request.group.groupKey.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if hasattr(args, 'email'):
    messages = ci_client.GetMessages()
    request.group.groupKey = messages.EntityKey(id=args.email)

  return request


def SetResourceName(unused_ref, args, request):
  """Set resource name to request.name.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if hasattr(args, 'email') and args.IsSpecified('email'):
    request.name = ConvertEmailToResourceName(args.email, 'email')

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

  if hasattr(args, 'page-size') and args.IsSpecified('page_size'):
    request.pageSize = int(args.page_size)

  return request


def SetGroupUpdateMask(unused_ref, args, request):
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

  if (args.IsSpecified('display_name')
      or args.IsSpecified('clear_display_name')):
    update_mask.append('display_name')

  if (args.IsSpecified('description')
      or args.IsSpecified('clear_description')):
    update_mask.append('description')

  # TODO(b/139939605): Add PosixGroups check once it is added.

  if not update_mask:
    raise exceptions.InvalidArgumentException(
        'Must specify at least one field mask.')

  request.updateMask = ','.join(update_mask)

  return request


def GenerateQuery(unused_ref, args, request):
  """Generate and set the query on the request based on the args.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """
  customer_id = ConvertOrgIdToObfuscatedCustomerId(args.organization)
  request.query = 'parent==\"customerId/{0}\" && \"{1}\" in labels'.format(
      customer_id, args.label)

  return request


def UpdateDisplayName(unused_ref, args, request):
  """Update displayName.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if args.IsSpecified('clear_display_name'):
    request.group.displayName = ''
  elif args.IsSpecified('display_name'):
    request.group.displayName = args.display_name

  return request


def UpdateDescription(unused_ref, args, request):
  """Update description.

  Args:
    unused_ref: unused.
    args: The argparse namespace.
    request: The request to modify.
  Returns:
    The updated request.
  """

  if args.IsSpecified('clear_description'):
    request.group.description = ''
  elif args.IsSpecified('description'):
    request.group.description = args.description

  return request


# processor hooks
def AddDynamicGroupUserQuery(arg_list):
  """Add DynamicGroupUserQuery to DynamicGroupQueries object list.

  Args:
    arg_list: dynamicGroupQuery whose resource type is USER.
  Returns:
    The updated dynamic group queries.
  """

  queries = []

  if arg_list:
    dg_user_query = ','.join(arg_list)
    messages = ci_client.GetMessages()
    resource_type = messages.DynamicGroupQuery.ResourceTypeValueValuesEnum
    new_dynamic_group_query = messages.DynamicGroupQuery(
        resourceType=resource_type.USER, query=dg_user_query)
    queries.append(new_dynamic_group_query)

  return queries


def ReformatLabels(labels_dict):
  """Reformat labels string to labels map.

  Args:
    labels_dict: labels map.
  Returns:
    Encoded label message.
  """

  messages = ci_client.GetMessages()
  return encoding.DictToMessage(labels_dict, messages.Group.LabelsValue)


# private methods
def ConvertOrgIdToObfuscatedCustomerId(org_id):
  """Convert organization id to obfuscated customer id.

  Args:
    org_id: organization id

  Returns:
    Obfuscated customer id

  Example:
    org_id: 12345
    organization_obj:
    {
      owner: {
        directoryCustomerId: A08w1n5gg
      }
    }
  """

  organization_obj = organizations.Client().Get(org_id)
  return organization_obj.owner.directoryCustomerId


def ConvertEmailToResourceName(email, arg_name):
  """Convert email to resource name.

  Args:
    email: group email
    arg_name: argument/parameter name

  Returns:
    Group Id (e.g. groups/11zu0gzc3tkdgn2)

  """
  lookup_group_name_resp = ci_client.LookupGroupName(email)

  if 'name' in lookup_group_name_resp:
    return lookup_group_name_resp['name']

  # If there is no group exists (or deleted) for the given group email,
  # print out an error message.
  error_msg = 'There is no such a group associated with the specified argument:' + email
  raise exceptions.InvalidArgumentException(arg_name, error_msg)
