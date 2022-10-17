# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Command line processing utilities for cloud access bindings."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources


def AddUpdateMask(ref, args, req):
  """Hook to add update mask."""
  del ref
  update_mask = []
  if args.IsSpecified('level'):
    update_mask.append('access_levels')

  req.updateMask = ','.join(update_mask)
  return req


def ProcessOrganization(ref, args, req):
  """Hook to process organization input."""
  del ref, args
  if req.parent is not None:
    return req

  org = properties.VALUES.access_context_manager.organization.Get()
  if org is None:
    raise calliope_exceptions.RequiredArgumentException(
        '--organization', 'The attribute can be set in the following ways: \n' +
        '- provide the argument `--organization` on the command line \n' +
        '- set the property `access_context_manager/organization`')

  org_ref = resources.REGISTRY.Parse(
      org, collection='accesscontextmanager.organizations')
  req.parent = org_ref.RelativeName()
  return req


def ProcessLevels(ref, args, req):
  """Hook to process level input."""
  del ref

  level_inputs = req.gcpUserAccessBinding.accessLevels
  req.gcpUserAccessBinding.accessLevels = []
  param = {}
  if args.IsKnownAndSpecified('policy'):
    param = {'accessPoliciesId': args.GetValue('policy')}

  for level_input in level_inputs:
    try:
      level_ref = resources.REGISTRY.Parse(
          level_input,
          params=param,
          collection='accesscontextmanager.accessPolicies.accessLevels')
    except:
      raise calliope_exceptions.InvalidArgumentException(
          '--level',
          'The input must be the full identifier for the access level, such as `accessPolicies/123/accessLevels/abc`.'
      )
    req.gcpUserAccessBinding.accessLevels.append(level_ref.RelativeName())
  return req
