# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utils for Fleet memberships commands."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import base as calliope_base
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.command_lib.container.fleet import api_util
from googlecloudsdk.command_lib.container.fleet import resources
from googlecloudsdk.command_lib.container.fleet import util as cmd_util
from googlecloudsdk.command_lib.container.fleet.memberships import errors
from googlecloudsdk.command_lib.util.apis import arg_utils


def SetInitProjectPath(ref, args, request):
  """Set the appropriate request path in project attribute for initializeHub requests.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """
  del ref, args  # Unused.
  request.project = request.project + '/locations/global/memberships'
  return request


def SetParentCollection(ref, args, request):
  """Set parent collection with location for created resources.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """
  del ref, args  # Unused.
  request.parent = request.parent + '/locations/-'
  return request


def SetMembershipLocation(ref, args, request):
  """Set membership location for requested resource.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued

  Returns:
    modified request
  """
  del ref  # Unused
  if cmd_util.APIEndpoint() == cmd_util.AUTOPUSH_API:
    # If a membership is provided
    if args.IsKnownAndSpecified('membership'):
      if resources.MembershipLocationSpecified(args):
        request.name = resources.MembershipResourceName(args)
      else:
        request.name = resources.SearchMembershipResource(args)
    else:
      raise calliope_exceptions.RequiredArgumentException(
          'MEMBERSHIP', 'membership is required for this command.')

  return request


def ExecuteUpdateMembershipRequest(ref, args):
  """Set membership location for requested resource.

  Args:
    ref: API response from update membership call
    args: command line arguments.

  Returns:
    response
  """
  del ref
  if cmd_util.APIEndpoint() == cmd_util.AUTOPUSH_API:
    if resources.MembershipLocationSpecified(args):
      name = resources.MembershipResourceName(args)
    else:
      name = resources.SearchMembershipResource(args)
  else:
    project = arg_utils.GetFromNamespace(args, '--project', use_defaults=True)
    membership_id = args.membership
    location = 'global'
    name = 'projects/{}/locations/{}/memberships/{}'.format(
        project, location, membership_id)
  # Update membership from Fleet API.
  obj = api_util.GetMembership(name, calliope_base.ReleaseTrack.ALPHA)
  update_fields = []
  if args.external_id:
    update_fields.append('externalId')
  if args.infra_type:
    update_fields.append('infrastructureType')
  if args.clear_labels or args.update_labels or args.remove_labels:
    update_fields.append('labels')
  update_mask = ','.join(update_fields)
  response = api_util.UpdateMembership(
      name,
      obj,
      update_mask,
      calliope_base.ReleaseTrack.ALPHA,
      external_id=args.external_id,
      infra_type=args.infra_type,
      clear_labels=args.clear_labels,
      update_labels=args.update_labels,
      remove_labels=args.remove_labels,
      issuer_url=None,
      oidc_jwks=None,
      api_server_version=None,
      async_flag=args.GetValue('async'))

  return response


def GetConnectGatewayServiceName(endpoint_override, location):
  """Get the appropriate Connect Gateway endpoint.

  This function checks the environment endpoint overide configuration for
  Fleet and uses it to determine which Connect Gateway endpoint to use.
  The overridden Fleet value will look like
  https://autopush-gkehub.sandbox.googleapis.com/.

  When there is no override set, this command will return a Connect Gateway
  prod endpoint. When an override is set, an appropriate non-prod endpoint
  will be provided instead.

  For example, when the overridden value looks like
  https://autopush-gkehub.sandbox.googleapis.com/,
  the function will return
  autopush-connectgateway.sandbox.googleapis.com.

  Regional prefixes are supported via the location argument. For example, when
  the overridden value looks like
  https://autopush-gkehub.sandbox.googleapis.com/ and location is passed in as
  "us-west1", the function will return
  us-west1-autopush-connectgateway.sandbox.googleapis.com.

  Args:
    endpoint_override: The URL set as the API endpoint override for 'gkehub'.
      Empty string if the override is not set.
    location: The location against which the command is supposed to run. This
      will be used to dynamically modify the service name to a location-specific
      value. If this is the value 'global' or None, a global service name is
      returned.

  Returns:
    The service name to use for this command invocation, optionally modified
    to target a specific location.

  Raises:
    UnknownApiEndpointOverrideError if the Fleet API endpoint override is not
    one of the standard values.
  """

  # Determine the location prefix, if any
  prefix = '' if location in ('global', None) else '{}-'.format(location)
  if not endpoint_override:
    # endpoint_override will be empty string for Prod.
    return '{}connectgateway.googleapis.com'.format(prefix)
  elif 'autopush-gkehub' in endpoint_override:
    return '{}autopush-connectgateway.sandbox.googleapis.com'.format(prefix)
  elif 'staging-gkehub' in endpoint_override:
    return '{}staging-connectgateway.sandbox.googleapis.com'.format(prefix)
  else:
    raise errors.UnknownApiEndpointOverrideError('gkehub')
