# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Flags and helpers for the compute security policies commands."""

from googlecloudsdk.command_lib.compute import flags as compute_flags


def SecurityPolicyArgument(required=True, plural=False):
  return compute_flags.ResourceArgument(
      resource_name='security policy',
      completion_resource_id='compute.securityPolicies',
      plural=plural,
      custom_plural='security policies',
      required=required,
      global_collection='compute.securityPolicies')


def SecurityPolicyArgumentForTargetResource(resource, required=True):
  return compute_flags.ResourceArgument(
      resource_name='security policy',
      name='--security-policy',
      completion_resource_id='compute.securityPolicies',
      plural=False,
      required=required,
      global_collection='compute.securityPolicies',
      short_help=('The security policy that will be set for this {0}.'
                  .format(resource)))
