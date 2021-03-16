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
"""Operations on secret names and the run.google.com/secrets annotation."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import platforms


class MountAll(object):
  """A token for ReachableSecret.secret_version.

  MountAll means the mount path shall become a directory with all the secret
  versions in it, as opposed to being a file with one secret version.
  """
  pass


class ReachableSecret(object):
  """A named secret+version that we can use in an env var or volume mount.

  See CL notes for references to the syntax being parsed here.
  """

  def __init__(self, flag_value, connector_name):
    """Parse flag value to make a ReachableSecret.

    Args:
      flag_value: str. A secret identifier like 'sec1:latest'. See tests for
        other supported formats.
      connector_name: Optional[str]. An env var ("ENV1") or a mount point
        ("/a/b") for use in error messages. Also used in validation since you
        can only use MountAll mode with a mount path. Ok to leave this as None
        if you're in managed mode and you don't care about the error string
        text.
    """

    self._for_env = connector_name is None or not connector_name.startswith('/')
    self._InitWithLocalSecret(flag_value, connector_name)

  def _InitWithLocalSecret(self, flag_value, connector_name):
    parts = flag_value.split(':')
    if len(parts) == 1:
      self.secret_name, = parts
      self.secret_version = self._OmittedSecretKeyDefault(connector_name)
    elif len(parts) == 2:
      self.secret_name, self.secret_version = parts
    else:
      raise ValueError('Invalid secret spec %r' % flag_value)
    self._AssertValidSecretKey(self.secret_version)

  def __repr__(self):
    # Used in testing.
    version_display = self.secret_version
    if self.secret_version is MountAll:
      version_display = 'MountAll'

    return ('<ReachableSecret '
            'name={secret_name} '
            'version={version_display}>'.format(
                version_display=version_display, **self.__dict__))

  def __eq__(self, other):
    return (self.secret_name == other.secret_name and
            self.secret_version == other.secret_version)

  def __ne__(self, other):
    return not self == other

  def _OmittedSecretKeyDefault(self, name):
    """The key/version value to use for a secret flag that has no version.

    Args:
      name: The env var or mount point, for use in an error message.

    Returns:
      str value to use as the secret version.

    Raises:
      ConfigurationError: If the key is required on this platform.
    """
    if platforms.GetPlatform() == platforms.PLATFORM_MANAGED:
      if self._for_env:
        return 'latest'
      else:  # for a mount point
        return MountAll
    else:  # for GKE+K8S
      if self._for_env:
        raise exceptions.ConfigurationError(
            'Missing required item key for [{}].'.format(name))
      else:  # for a mount point
        return MountAll

  def _AssertValidSecretKey(self, key):
    if platforms.GetPlatform() == platforms.PLATFORM_MANAGED:
      if not (key is MountAll or key.isdigit() or key == 'latest'):
        raise exceptions.ConfigurationError(
            "Secret key must be an integer or 'latest'.")

  def AsSecretVolumeSource(self, resource):
    """Build message for adding to revision.template.volumes.secrets.

    Args:
      resource: RevisionSpec that may get modified with new aliases.

    Returns:
      messages.SecretVolumeSource
    """
    messages = resource.MessagesModule()
    out = messages.SecretVolumeSource(secretName=self.secret_name)
    if self.secret_version is not MountAll:
      out.items.append(
          messages.KeyToPath(key=self.secret_version, path=self.secret_version))
    return out

  def AsEnvVarSource(self, resource):
    """Build message for adding to revision.template.env_vars.secrets.

    Args:
      resource: RevisionSpec that may get modified with new aliases.

    Returns:
      messages.EnvVarSource
    """
    messages = resource.MessagesModule()
    return messages.EnvVarSource(
        secretKeyRef=messages.SecretKeySelector(
            name=self.secret_name, key=self.secret_version))
