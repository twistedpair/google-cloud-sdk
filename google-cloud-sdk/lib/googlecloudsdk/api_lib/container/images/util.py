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
"""Utilities for the container images commands."""

from containerregistry.client import docker_creds
from containerregistry.client import docker_name
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker
from googlecloudsdk.core.util import times


class UtilError(exceptions.Error):
  """Base class for util errors."""


class InvalidImageNameError(UtilError):
  """Raised when the user supplies an invalid image name."""


def ValidateRepository(repository):
  """Validates that the repository name is correct.

  Args:
    repository: str, The repository name supplied by a user.

  Returns:
    The parsed docker_name.Repository instance.

  Raises:
    InvalidImageNameError: If the name is invalid.
    docker.UnsupportedRegistryError: If the name is valid, but belongs to a
      registry we don't support.
  """
  try:
    r = docker_name.Repository(repository)
  except docker_name.BadNameException as e:
    # Reraise with the proper base class so the message gets shown.
    raise InvalidImageNameError(e.message)
  if r.registry not in constants.ALL_SUPPORTED_REGISTRIES:
    raise docker.UnsupportedRegistryError(repository)

  return r


def ValidateImage(image):
  """Validates the image name.

  Args:
    image: str, The image name supplied by a user.

  Returns:
    The parsed docker_name.Repository object.

  Raises:
    InvalidImageNameError: If the name is invalid.
  """
  if ':' in image or '@' in image:
    raise InvalidImageNameError(
        'Image names must not be fully-qualified. Remove the tag or digest '
        'and try again.')
  return ValidateRepository(image)


class CredentialProvider(docker_creds.Basic):
  """CredentialProvider is a class to refresh oauth2 creds during requests."""

  _USERNAME = '_token'

  def __init__(self):
    super(CredentialProvider, self).__init__(self._USERNAME, 'does not matter')

  @property
  def password(self):
    cred = c_store.Load()
    return cred.access_token


def _TimeCreatedToDateTime(time_created):
  timestamp = float(time_created) / 1000
  # Drop the microsecond portion.
  timestamp = round(timestamp, 0)
  return times.GetDateTimeFromTimeStamp(timestamp)


def TransformManifests(manifests):
  """Transforms the manifests returned from the server."""
  results = []
  for k, v in manifests.iteritems():
    result = {'digest': k,
              'tags': v.get('tag', []),
              'timestamp': _TimeCreatedToDateTime(v.get('timeCreatedMs'))}
    results.append(result)

  return sorted(results, key=lambda x: x.get('timestamp'))
