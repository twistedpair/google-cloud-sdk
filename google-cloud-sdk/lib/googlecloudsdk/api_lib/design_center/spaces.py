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
"""DesignCenter Spaces API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.design_center import utils as api_lib_utils
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import iam_util


class SpacesClient(object):
  """Client for Spaces in design center API."""

  def __init__(self, release_track=base.ReleaseTrack.ALPHA):
    self.client = api_lib_utils.GetClientInstance(release_track)
    self.messages = api_lib_utils.GetMessagesModule(release_track)
    self._spaces_client = self.client.projects_locations_spaces

  def GetIamPolicy(self, space_id):
    """Fetch the IAM Policy attached to the sepcified space.

    Args:
      space_id: str, the space id.

    Returns:
      The spaces's IAM Policy.
    """
    # version = iam_util.MAX_LIBRARY_IAM_SUPPORTED_VERSION
    get_req = (
        self.messages.DesigncenterProjectsLocationsSpacesGetIamPolicyRequest(
            resource=space_id,
        )
    )
    return self._spaces_client.GetIamPolicy(get_req)

  def SetIamPolicy(self, space_id, policy_file):
    """Sets an space's IamPolicy to the one provided.

    If 'policy_file' has no etag specified, this will BLINDLY OVERWRITE the IAM
    policy!

    Args:
        space_id: str, the space id..
        policy_file: a policy file.

    Returns:
        The IAM Policy.
    """
    policy = iam_util.ParsePolicyFile(policy_file, self.messages.Policy)
    return self._SetIamPolicyHelper(space_id, policy)

  def _SetIamPolicyHelper(self, space_id, policy):
    set_req = (
        self.messages.DesigncenterProjectsLocationsSpacesSetIamPolicyRequest(
            resource=space_id,
            setIamPolicyRequest=self.messages.SetIamPolicyRequest(
                policy=policy,),
        ))
    return self._spaces_client.SetIamPolicy(set_req)

  def TestIamPermissions(self, space_id, permissions):
    """Tests the IAM permissions for the specified space.

    Args:
      space_id: str, the space id.
      permissions: list of str, the permissions to test.

    Returns:
      The TestIamPermissionsResponse.
    """
    test_iam_perm_req = self.messages.TestIamPermissionsRequest(
        permissions=permissions)
    test_req = (
        self.messages.DesigncenterProjectsLocationsSpacesTestIamPermissionsRequest(
            resource=space_id,
            testIamPermissionsRequest=test_iam_perm_req,
        ))
    return self._spaces_client.TestIamPermissions(test_req)
