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
