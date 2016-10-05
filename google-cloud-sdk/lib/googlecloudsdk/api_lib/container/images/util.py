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
from containerregistry.client.v2_2 import docker_image
from googlecloudsdk.core import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker
from googlecloudsdk.core.util import times


class UtilError(exceptions.Error):
  """Base class for util errors."""


class InvalidImageNameError(UtilError):
  """Raised when the user supplies an invalid image name."""


def IsFullySpecified(image_name):
  return ':' in image_name or '@' in image_name


def ValidateRepositoryPath(repository_path):
  """Validates the repository path.

  Args:
    repository_path: str, The repository path supplied by a user.

  Returns:
    The parsed docker_name.Repository object.

  Raises:
    InvalidImageNameError: If the image name is invalid.
    docker.UnsupportedRegistryError: If the path is valid, but belongs to a
      registry we don't support.
  """
  if IsFullySpecified(repository_path):
    raise InvalidImageNameError(
        'Image names must not be fully-qualified. Remove the tag or digest '
        'and try again.')
  if repository_path.endswith('/'):
    raise InvalidImageNameError(
        'Image name cannot end with \'/\'. '
        'Remove the trailing \'/\' and try again.')
  try:
    repository = docker_name.Repository(repository_path)
    if repository.registry not in constants.ALL_SUPPORTED_REGISTRIES:
      raise docker.UnsupportedRegistryError(repository_path)
    return repository
  except docker_name.BadNameException as e:
    # Reraise with the proper base class so the message gets shown.
    raise InvalidImageNameError(e.message)


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


def RecoverProjectId(repository):
  """Recovers the project-id from a GCR repository."""
  parts = repository.repository.split('/')
  if '.' not in parts[0]:
    return parts[0]
  elif len(parts) > 1:
    return parts[1] + ':' + parts[0]
  else:
    raise ValueError('Domain-scoped app missing project name: %s', parts[0])


def _UnqualifiedResourceUrl(repo):
  return 'https://{repo}@'.format(repo=str(repo))


def _ResourceUrl(repo, digest):
  return 'https://{repo}@{digest}'.format(repo=str(repo), digest=digest)


def FetchOccurrences(repository):
  """Fetches the occurrences attached to the list of manifests."""
  project_id = RecoverProjectId(repository)

  # Construct a filter of all of the resource urls we are displaying
  filters = []

  # Retrieve all resource urls prefixed with the image path
  filters.append('has_prefix(resource_url, "{repo}"'.format(
      repo=_UnqualifiedResourceUrl(repository)))

  client = apis.GetClientInstance('containeranalysis', 'v1alpha1')
  messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')

  request = messages.ContaineranalysisProjectsOccurrencesListRequest(
      projectsId=project_id,
      filter=' OR '.join(filters))
  response = client.projects_occurrences.List(request)

  occurrences = {}
  for occ in response.occurrences:
    if occ.resourceUrl not in occurrences:
      occurrences[occ.resourceUrl] = []
    occurrences[occ.resourceUrl].append(occ)
  return occurrences


def TransformManifests(manifests, repository, show_occurrences=True):
  """Transforms the manifests returned from the server."""
  if not manifests:
    return []

  # Map from resource url to the occurrence.
  occurrences = FetchOccurrences(repository) if show_occurrences else {}

  # Attach each occurrence to the resource to which it applies.
  results = []
  for k, v in manifests.iteritems():
    result = {'digest': k,
              'tags': v.get('tag', []),
              'timestamp': _TimeCreatedToDateTime(v.get('timeCreatedMs'))}

    # Partition occurrences into different columns by kind.
    for occ in occurrences.get(_ResourceUrl(repository, k), []):
      if occ.kind not in result:
        result[occ.kind] = []
      result[occ.kind].append(occ)

    results.append(result)

  return sorted(results, key=lambda x: x.get('timestamp'))


def GetTagNamesForDigest(digest, http_obj):
  """Gets all of the tags for a given digest.

  Args:
    digest: docker_name.Digest, The digest supplied by a user.
    http_obj: http.Http(), The http transport.

  Returns:
    A list of all of the tags associated with the input digest.
  """
  repository_path = digest.registry + '/' + digest.repository
  repository = ValidateRepositoryPath(repository_path)
  with docker_image.FromRegistry(basic_creds=CredentialProvider(),
                                 name=repository,
                                 transport=http_obj) as image:
    if digest.digest not in image.manifests():
      return []
    manifest_value = image.manifests().get(digest.digest, {})
    return manifest_value.get('tag', [])  # digest tags


def GetDockerTagsForDigest(digest, http_obj):
  """Gets all of the tags for a given digest.

  Args:
    digest: docker_name.Digest, The digest supplied by a user.
    http_obj: http.Http(), The http transport.

  Returns:
    A list of all of the tags associated with the input digest.
  """
  repository_path = digest.registry + '/' + digest.repository
  repository = ValidateRepositoryPath(repository_path)
  tags = []
  tag_names = GetTagNamesForDigest(digest, http_obj)
  for tag_name in tag_names:  # iterate over digest tags
    tags.append(docker_name.Tag(str(repository) + ':' + tag_name))
  return tags


def GetDockerImageFromTagOrDigest(image_name):
  """Gets an image object given either a tag or a digest.

  Args:
    image_name: Either a fully qualified tag or a fully qualified digest.
      Defaults to latest if no tag specified.

  Returns:
    Either a docker_name.Tag or a docker_name.Digest object.
  """
  if not IsFullySpecified(image_name):
    image_name += ':latest'

  try:
    return docker_name.Tag(image_name)
  except docker_name.BadNameException:
    pass
  # If the full digest wasn't specified, check if what was passed
  # in is a valid digest prefix.
  # 7 for 'sha256:' and 64 for the full digest
  parts = image_name.split('@', 1)
  if len(parts) == 2 and len(parts[1]) < 7 + 64:
    image_name = GetDockerDigestFromPrefix(image_name)
  return docker_name.Digest(image_name)


def GetDockerDigestFromPrefix(digest):
  """Gets a full digest string given a potential prefix.

  Args:
    digest: The digest prefix

  Returns:
    The full digest, or the same prefix if no full digest is found.

  Raises:
    InvalidImageNameError: if the prefix supplied isn't unique.
  """
  repository_path, prefix = digest.split('@', 1)
  repository = ValidateRepositoryPath(repository_path)
  with docker_image.FromRegistry(basic_creds=CredentialProvider(),
                                 name=repository,
                                 transport=http.Http()) as image:
    matches = [d for d in image.manifests() if d.startswith(prefix)]

    if len(matches) == 1:
      return repository_path + '@' +  matches.pop()
    elif len(matches) > 1:
      raise InvalidImageNameError(
          '{0} is not a unique digest prefix. Options are {1}.]'
          .format(prefix, ', '.join(map(str, matches))))
    return digest
