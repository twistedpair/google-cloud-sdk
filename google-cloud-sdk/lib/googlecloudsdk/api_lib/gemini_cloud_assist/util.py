# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""API lib for Gemini Cloud Assist."""
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util


VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1alpha'}


# The messages module can also be accessed from client.MESSAGES_MODULE
def GetMessagesModule(release_track=base.ReleaseTrack.ALPHA):
  """Returns the messages module for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The messages module for the given release track.
  """
  return apis.GetMessagesModule('geminicloudassist',
                                VERSION_MAP.get(release_track))


def GetClientInstance(release_track=base.ReleaseTrack.ALPHA):
  """Returns the client instance for the given release track.

  Args:
    release_track: The release track to use.

  Returns:
    The client instance for the given release track.
  """
  return apis.GetClientInstance('geminicloudassist',
                                VERSION_MAP.get(release_track))


def GetInvestigationIamPolicy(investigations_resource_name):
  """Returns the IAM policy for the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.

  Returns:
    The IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  return client.projects_locations_investigations.GetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsGetIamPolicyRequest(
          resource=investigations_resource_name
      )
  )


def AddInvestigationIamPolicyBinding(
    investigations_resource_name,
    member='allUsers',
    role='roles/geminicloudassist.investigationViewer',
):
  """Adds an IAM policy binding to the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    member: The member to add to the binding.
    role: The role to add to the binding.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy = GetInvestigationIamPolicy(investigations_resource_name)
  iam_util.AddBindingToIamPolicy(messages.Binding, policy, member, role)
  return client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
      )
  )


def RemoveInvestigationIamPolicyBinding(
    investigations_resource_name,
    member='allUsers',
    role='roles/geminicloudassist.investigationViewer',
):
  """Removes an IAM policy binding from the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    member: The member to remove from the binding.
    role: The role to remove from the binding.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy = GetInvestigationIamPolicy(investigations_resource_name)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(policy=policy),
      )
  )


def SetInvestigationIamPolicy(investigations_resource_name, policy_file):
  """Sets the IAM policy for the given investigation resource.

  Args:
    investigations_resource_name: The name of the investigation resource.
    policy_file: The path to the policy file.

  Returns:
    The updated IAM policy for the given investigation resource.
  """
  client = GetClientInstance()
  messages = GetMessagesModule()
  policy, update_mask = iam_util.ParseYamlOrJsonPolicyFile(
      policy_file, messages.Policy
  )
  result = client.projects_locations_investigations.SetIamPolicy(
      messages.GeminicloudassistProjectsLocationsInvestigationsSetIamPolicyRequest(
          resource=investigations_resource_name,
          setIamPolicyRequest=messages.SetIamPolicyRequest(
              policy=policy, updateMask=update_mask
          ),
      )
  )
  iam_util.LogSetIamPolicy(investigations_resource_name, 'investigation')
  return result
