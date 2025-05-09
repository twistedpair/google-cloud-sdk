# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import apis_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import properties

VERSION_MAP = {base.ReleaseTrack.ALPHA: 'v1alpha',
               base.ReleaseTrack.BETA: 'v1beta',
               base.ReleaseTrack.GA: 'v1'}


def _GetClient(version):
  return apis.GetClientInstance('oslogin', version)


class OsloginException(core_exceptions.Error):
  """OsloginException is for non-code-bug errors in oslogin client utils."""


class OsloginKeyNotFoundError(OsloginException):
  """OsloginKeyNotFoundError is raised when requested SSH key is not found."""


class OsloginClient(object):
  """Class for working with oslogin users."""

  def __init__(self, release_track):
    self.version = VERSION_MAP[release_track]
    self.project = properties.VALUES.core.project.Get()
    try:
      self.client = _GetClient(self.version)
      self.messages = self.client.MESSAGES_MODULE
    except apis_util.UnknownVersionError:
      self.client = None
      self.messages = None

  def __nonzero__(self):
    return self.__bool__()

  def __bool__(self):
    return bool(self.client)

  def GetLoginProfile(self, user, project=None, system_id=None,
                      include_security_keys=False):
    """Return the OS Login profile for a user.

    The login profile includes some information about the user, a list of
    Posix accounts with things like home directory location, and public SSH
    keys for logging into instances.

    Args:
      user: str, The email address of the OS Login user.
      project: str, The project ID associated with the desired profile.
      system_id: str, If supplied, only return profiles associated with the
        given system ID.
      include_security_keys: bool, If true, include security key information.

    Returns:
      The login profile for the user.
    """
    # TODO(b/70287338): Update these calls to use Resource references.
    profile_request = self.messages.OsloginUsersGetLoginProfileRequest
    if self.version == 'v1':
      message = profile_request(
          name='users/{0}'.format(user),
          projectId=project,
          systemId=system_id)

    else:
      if include_security_keys:
        view = profile_request.ViewValueValuesEnum.SECURITY_KEY
      else:
        view = None

      message = profile_request(
          name='users/{0}'.format(user),
          projectId=project,
          systemId=system_id,
          view=view)

    res = self.client.users.GetLoginProfile(message)
    return res

  def DeletePosixAccounts(self, project_ref, operating_system=None):
    """Delete the posix accounts for an account in the current project.

    Args:
      project_ref: The oslogin.users.projects resource.
      operating_system: str, 'linux' or 'windows' (case insensitive).
    Returns:
      None
    """
    if operating_system:
      os_value = operating_system.upper()
      os_message = (self.messages.OsloginUsersProjectsDeleteRequest
                    .OperatingSystemTypeValueValuesEnum(os_value))
      message = self.messages.OsloginUsersProjectsDeleteRequest(
          name=project_ref.RelativeName(),
          operatingSystemType=os_message)
    else:
      message = self.messages.OsloginUsersProjectsDeleteRequest(
          name=project_ref.RelativeName())

    self.client.users_projects.Delete(message)

  def ImportSshPublicKey(
      self,
      user,
      public_key,
      expiration_time=None,
      include_security_keys=False,
      region: Optional[str] = None,
  ):
    """Upload an SSH public key to the user's login profile.

    Args:
      user: str, The email address of the OS Login user.
      public_key: str, An SSH public key.
      expiration_time: int, microseconds since epoch.
      include_security_keys: bool, If true, return security key information.
      region: str, The region to which to make sure the key is imported.

    Returns:
      The login profile for the user.
    """
    import_request = self.messages.OsloginUsersImportSshPublicKeyRequest

    public_key_message = self.messages.SshPublicKey(
        key=public_key,
        expirationTimeUsec=expiration_time)

    regions = [region] if region else []

    if self.version == 'v1':
      message = import_request(
          parent='users/{0}'.format(user),
          projectId=self.project,
          sshPublicKey=public_key_message,
          regions=regions,
      )
    else:
      if include_security_keys:
        view = import_request.ViewValueValuesEnum.SECURITY_KEY
      else:
        view = None

      message = import_request(
          parent='users/{0}'.format(user),
          projectId=self.project,
          sshPublicKey=public_key_message,
          regions=regions,
          view=view,
      )

    res = self.client.users.ImportSshPublicKey(message)
    return res

  def DeleteSshPublicKey(self, user, fingerprint):
    """Delete an SSH public key from the user's login profile.

    Args:
      user: str, The email address of the OS Login user.
      fingerprint: str, The fingerprint of the SSH key to delete.
    Returns:
      None
    """
    message = self.messages.OsloginUsersSshPublicKeysDeleteRequest(
        name='users/{0}/sshPublicKeys/{1}'.format(user, fingerprint))
    self.client.users_sshPublicKeys.Delete(message)

  def GetSshPublicKey(self, user, fingerprint):
    """Get an SSH public key from the user's login profile.

    Args:
      user: str, The email address of the OS Login user.
      fingerprint: str, The fingerprint of the SSH key to delete.
    Returns:
      The requested SSH public key.
    """
    message = self.messages.OsloginUsersSshPublicKeysGetRequest(
        name='users/{0}/sshPublicKeys/{1}'.format(user, fingerprint))
    res = self.client.users_sshPublicKeys.Get(message)
    return res

  def UpdateSshPublicKey(self, user, fingerprint, public_key, update_mask,
                         expiration_time=None):
    """Update an existing SSH public key in a user's login profile.

    Args:
      user: str, The email address of the OS Login user.
      fingerprint: str, The fingerprint of the SSH key to update.
      public_key: str, An SSH public key.
      update_mask: str, A mask to control which fields get updated.
      expiration_time: int, microseconds since epoch.

    Returns:
      The login profile for the user.
    """
    public_key_message = self.messages.SshPublicKey(
        key=public_key, expirationTimeUsec=expiration_time
    )
    message = self.messages.OsloginUsersSshPublicKeysPatchRequest(
        name='users/{0}/sshPublicKeys/{1}'.format(user, fingerprint),
        sshPublicKey=public_key_message,
        updateMask=update_mask,
    )
    res = self.client.users_sshPublicKeys.Patch(message)
    return res

  def SignSshPublicKey(self, user, public_key, project_id, region):
    """Sign an SSH public key for a given user.

    Args:
      user: str, The email address of the OS Login user.
      public_key: str, An SSH public key.
      project_id: str, The project ID associated with the VM.
      region: str, The region where the signed SSH public key may be used.

    Returns:
      A signed SSH public key.
    """
    public_key_message = self.messages.SignSshPublicKeyRequest(
        sshPublicKey=public_key
    )
    message = self.messages.OsloginUsersProjectsZonesSignSshPublicKeyRequest(
        parent='users/{0}/projects/{1}/locations/{2}'.format(
            user, project_id, region
        ),
        signSshPublicKeyRequest=public_key_message,
    )
    return self.client.users_projects_zones.SignSshPublicKey(message)

  def SignSshPublicKeyForInstance(
      self,
      public_key,
      project_id,
      region,
      service_account='',
      compute_instance=None,
      app_engine_instance=None,
  ):
    """Sign an SSH public key scoped to a given instance.

    Args:
      public_key: str, An SSH public key.
      project_id: str, The project ID associated with the VM.
      region: str, The region where the signed SSH public key may be used.
      service_account: str, The service account associated with the VM.
      compute_instance: str, The Compute instance to sign the SSH public key
        for. Only one of compute_instance or app_engine_instance should be
        specified. The format for this field is
        'projects/{project}/zones/{zone}/instances/{instance_id}'.
      app_engine_instance: str, The App Engine instance to sign the SSH public
        key for. Only one of compute_instance or app_engine_instance should be
        specified. The format for this field is
        'services/{service}/versions/{version}/instances/{instance}'.

    Raises:
      ValueError: If both or neither compute_instance and
        app_engine_instance are specified.

    Returns:
      A signed SSH public key.
    """
    if (compute_instance and app_engine_instance) or (
        not compute_instance and not app_engine_instance
    ):
      raise ValueError(
          'Exactly one of compute_instance or app_engine_instance must be'
          ' specified.'
      )
    request_kwargs = {
        'sshPublicKey': public_key,
        'serviceAccount': service_account,
        'computeInstance': compute_instance,
        'appEngineInstance': app_engine_instance,
    }
    message_kwargs = {
        'parent': 'projects/{0}/locations/{1}'.format(project_id, region),
    }
    if self.version == 'v1alpha':
      request = self.messages.GoogleCloudOsloginControlplaneRegionalV1alphaSignSshPublicKeyRequest(
          **request_kwargs
      )
      message = self.messages.OsloginProjectsLocationsSignSshPublicKeyRequest(
          **message_kwargs,
          googleCloudOsloginControlplaneRegionalV1alphaSignSshPublicKeyRequest=request,
      )
    else:
      request = self.messages.GoogleCloudOsloginControlplaneRegionalV1betaSignSshPublicKeyRequest(
          **request_kwargs
      )
      message = self.messages.OsloginProjectsLocationsSignSshPublicKeyRequest(
          **message_kwargs,
          googleCloudOsloginControlplaneRegionalV1betaSignSshPublicKeyRequest=request,
      )
    return self.client.projects_locations.SignSshPublicKey(message)

  def ProvisionPosixAccount(
      self, user, project_id, region: Optional[str] = None
  ):
    """Provision a POSIX account for a given user.

    ProvisionPosixAccount is a regional read if the user has the correct
    POSIX account. Otherwise, it is a global write that waits on replication
    to the provided region before returning success.

    Args:
      user: str, The email address of the OS Login user.
      project_id: str, The project ID associated with the VM.
      region: str, The regions to wait to be written to before returning a
        response.

    Returns:
      The user's provisioned POSIX account for the given project.
    """
    regions = [region] if region else []
    provision_body = self.messages.ProvisionPosixAccountRequest(regions=regions)

    name = 'users/{0}/projects/{1}'.format(user, project_id)

    provision_request = (
        self.messages.OsloginUsersProjectsProvisionPosixAccountRequest(
            name=name, provisionPosixAccountRequest=provision_body
        )
    )

    res = self.client.users_projects.ProvisionPosixAccount(provision_request)
    return res
