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
"""oslogin client functions."""
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import apis_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions as core_exceptions

VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1alpha',
               base.ReleaseTrack.BETA: 'v1beta',
               base.ReleaseTrack.GA: 'v1'}


def _GetClient(version):
  return apis.GetClientInstance('oslogin', version)


class OsloginException(core_exceptions.Error):
  """OsloginException is for non-code-bug errors in oslogin client utils."""


class OsloginClient(object):
  """Class for working with oslogin users."""

  def __init__(self, release_track):
    version = VERSION_MAP[release_track]
    try:
      self.client = _GetClient(version)
      self.messages = self.client.MESSAGES_MODULE
    except apis_util.UnknownVersionError:
      self.client = None
      self.messages = None

  def __nonzero__(self):
    return bool(self.client)

  def GetLoginProfile(self, user):
    """Return the OS Login profile for a user.

    The login profile includes some information about the user, a list of
    Posix accounts with things like home directory location, and public SSH
    keys for logging into instances.

    Args:
      user: str, The email address of the OS Login user.
    Returns:
      The login profile for the user.
    """
    message = self.messages.OsloginUsersGetLoginProfileRequest(
        name='users/{0}'.format(user))
    res = self.client.users.GetLoginProfile(message)
    return res

  def ImportSshPublicKey(self, user, public_key):
    """Upload an SSH public key to the user's login profile.

    Args:
      user: str, The email address of the OS Login user.
      public_key: str, An SSH public key.
    Returns:
      The login profile for the user.
    """
    public_key_message = self.messages.SshPublicKey(
        key=public_key)
    message = self.messages.OsloginUsersImportSshPublicKeyRequest(
        parent='users/{0}'.format(user),
        sshPublicKey=public_key_message)
    res = self.client.users.ImportSshPublicKey(message)
    return res

