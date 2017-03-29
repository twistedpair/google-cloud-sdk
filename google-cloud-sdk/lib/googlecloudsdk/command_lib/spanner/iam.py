# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Provides helper methods for dealing with JSON files for Spanner IAM."""

from googlecloudsdk.api_lib.spanner import instances
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.iam import iam_util


def AddIamPolicyBinding(instance_ref, member, role):
  """Adds a policy binding to an instance IAM policy."""
  msgs = apis.GetMessagesModule('spanner', 'v1')
  policy = instances.GetIamPolicy(instance_ref)
  iam_util.AddBindingToIamPolicy(msgs, policy, member, role)
  return instances.SetPolicy(instance_ref, policy)


def SetIamPolicy(instance_ref, policy):
  """Sets the IAM policy on an instance."""
  msgs = apis.GetMessagesModule('spanner', 'v1')
  policy = iam_util.ParseJsonPolicyFile(policy, msgs.Policy)
  return instances.SetPolicy(instance_ref, policy)


def RemoveIamPolicyBinding(instance_ref, member, role):
  """Removes a policy binding from an instance IAM policy."""
  policy = instances.GetIamPolicy(instance_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return instances.SetPolicy(instance_ref, policy)
