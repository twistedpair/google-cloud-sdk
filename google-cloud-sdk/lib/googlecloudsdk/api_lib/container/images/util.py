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

import itertools

from apitools.base.py import list_pager
from containerregistry.client import docker_creds
from containerregistry.client import docker_name
# We use distinct versions of the library for v2 and v2.2 because
# the schema of the JSON data returned is fairly different, and
# images addressed by digest must be accessed via the API version
# corresponding to how they are stored.
from containerregistry.client.v2 import docker_image as v2_image
from containerregistry.client.v2 import util as v2_util
from containerregistry.client.v2_2 import docker_image as v2_2_image
from containerregistry.client.v2_2 import util as v2_2_util
from googlecloudsdk.api_lib.container.images import container_analysis_data_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import http
from googlecloudsdk.core import resources
from googlecloudsdk.core.credentials import store as c_store
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker
from googlecloudsdk.core.util import times


# The maximum number of resource URLs by which to filter when showing
# occurrences. This is required since filtering by too many causes the
# API request to be too large. Instead, the requests are chunkified.
_MAXIMUM_RESOURCE_URL_CHUNK_SIZE = 5


class UtilError(exceptions.Error):
  """Base class for util errors."""


class InvalidImageNameError(UtilError):
  """Raised when the user supplies an invalid image name."""


class UserRecoverableV2Error(UtilError):
  """Raised when a user-recoverable V2 API error is encountered."""


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
    if repository_path in constants.MIRROR_REGISTRIES:
      repository = docker_name.Registry(repository_path)
    else:
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
    cred = c_store.LoadIfEnabled()
    return cred.access_token if cred else None


def _TimeCreatedToDateTime(time_created):
  timestamp = float(time_created) / 1000
  # Drop the microsecond portion.
  timestamp = round(timestamp, 0)
  return times.GetDateTimeFromTimeStamp(timestamp)


def RecoverProjectId(repository):
  """Recovers the project-id from a GCR repository."""
  if repository.registry in constants.MIRROR_REGISTRIES:
    return constants.MIRROR_PROJECT
  if repository.registry in constants.LAUNCHER_REGISTRIES:
    return constants.LAUNCHER_PROJECT
  parts = repository.repository.split('/')
  if '.' not in parts[0]:
    return parts[0]
  elif len(parts) > 1:
    return parts[0] + ':' + parts[1]
  else:
    raise ValueError('Domain-scoped app missing project name: %s', parts[0])


def _UnqualifiedResourceUrl(repo):
  return 'https://{repo}@'.format(repo=str(repo))


def _ResourceUrl(repo, digest):
  return 'https://{repo}@{digest}'.format(repo=str(repo), digest=digest)


def _FullyqualifiedDigest(digest):
  return 'https://{digest}'.format(digest=digest)


def _MakeOccurrenceRequest(
    project_id, resource_filter, occurrence_filter=None, resource_urls=None):
  """Helper function to make Fetch Occurrence Request."""
  client = apis.GetClientInstance('containeranalysis', 'v1alpha1')
  messages = apis.GetMessagesModule('containeranalysis', 'v1alpha1')
  base_filter = resource_filter
  if occurrence_filter:
    base_filter = (
        '({occurrence_filter}) AND ({base_filter})'.format(
            occurrence_filter=occurrence_filter,
            base_filter=base_filter))
  project_ref = resources.REGISTRY.Parse(
      project_id, collection='cloudresourcemanager.projects')

  if not resource_urls:
    # When there are no resource_urls to filter don't need to do chunkifying
    # logic or add anything to the base filter.
    return list_pager.YieldFromList(
        client.projects_occurrences,
        request=messages.ContaineranalysisProjectsOccurrencesListRequest(
            parent=project_ref.RelativeName(), filter=base_filter),
        field='occurrences',
        batch_size=1000,
        batch_size_attribute='pageSize')

  # Occurrences are filtered by resource URLs. If there are more than roughly
  # _MAXIMUM_RESOURCE_URL_CHUNK_SIZE resource urls in the API request, the
  # request becomes too big and will be rejected. This block chunkifies the
  # resource URLs list and issues multiple API requests to circumvent this
  # limit. The resulting generators (from YieldFromList) are chained together in
  # the final output.
  occurrence_generators = []
  for index in range(0, len(resource_urls), _MAXIMUM_RESOURCE_URL_CHUNK_SIZE):
    chunk = resource_urls[index : (index + _MAXIMUM_RESOURCE_URL_CHUNK_SIZE)]
    url_filter = '%s AND (%s)' % (
        base_filter,
        ' OR '.join(['resource_url="%s"' % url for url in chunk]))
    occurrence_generators.append(
        list_pager.YieldFromList(
            client.projects_occurrences,
            request=messages.ContaineranalysisProjectsOccurrencesListRequest(
                parent=project_ref.RelativeName(), filter=url_filter),
            field='occurrences',
            batch_size=1000,
            batch_size_attribute='pageSize'))
  return itertools.chain(*occurrence_generators)


def FetchOccurrencesForResource(digest, occurrence_filter=None):
  """Fetches the occurrences attached to this image."""
  project_id = RecoverProjectId(digest)
  resource_filter = 'resource_url="{resource_url}"'.format(
      resource_url=_FullyqualifiedDigest(digest))
  return _MakeOccurrenceRequest(project_id, resource_filter, occurrence_filter)


def TransformContainerAnalysisData(image_name, occurrence_filter=None):
  """Transforms the occurrence data from Container Analysis API."""
  occurrences = FetchOccurrencesForResource(image_name, occurrence_filter)
  analysis_obj = container_analysis_data_util.ContainerAnalysisData(image_name)
  for occurrence in occurrences:
    analysis_obj.add_record(occurrence)
  return analysis_obj


def FetchOccurrences(repository, occurrence_filter=None, resource_urls=None):
  """Fetches the occurrences attached to the list of manifests."""
  project_id = RecoverProjectId(repository)

  # Retrieve all resource urls prefixed with the image path
  resource_filter = 'has_prefix(resource_url, "{repo}")'.format(
      repo=_UnqualifiedResourceUrl(repository))

  occurrences = _MakeOccurrenceRequest(project_id, resource_filter,
                                       occurrence_filter, resource_urls)
  occurrences_by_resources = {}
  for occ in occurrences:
    if occ.resourceUrl not in occurrences_by_resources:
      occurrences_by_resources[occ.resourceUrl] = []
    occurrences_by_resources[occ.resourceUrl].append(occ)
  return occurrences_by_resources


def TransformManifests(
    manifests, repository, show_occurrences=True, occurrence_filter=None,
    resource_urls=None):
  """Transforms the manifests returned from the server."""
  if not manifests:
    return []

  # Map from resource url to the occurrence.
  occurrences = {}
  if show_occurrences:
    occurrences = FetchOccurrences(
        repository, occurrence_filter=occurrence_filter,
        resource_urls=resource_urls)

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
  with v2_2_image.FromRegistry(basic_creds=CredentialProvider(),
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


def ValidateImagePathAndReturn(digest_or_tag):
  # Repository should contain project/image_path.
  if '/' not in digest_or_tag.repository:
    raise InvalidImageNameError('Image name should start with '
                                '*.gcr.io/project_id/image_path. ')
  return digest_or_tag


def GetDockerImageFromTagOrDigest(image_name):
  """Gets an image object given either a tag or a digest.

  Args:
    image_name: Either a fully qualified tag or a fully qualified digest.
      Defaults to latest if no tag specified.

  Returns:
    Either a docker_name.Tag or a docker_name.Digest object.

  Raises:
    InvalidImageNameError: Given digest could not be resolved to a full digest.
  """
  if not IsFullySpecified(image_name):
    image_name += ':latest'

  try:
    return ValidateImagePathAndReturn(docker_name.Tag(image_name))
  except docker_name.BadNameException:
    pass

  parts = image_name.split('@', 1)
  if len(parts) == 2:
    if not parts[1].startswith('sha256:'):
      raise InvalidImageNameError(
          '[{0}] digest must be of the form "sha256:<digest>".'.format(
              image_name))

    # If the full digest wasn't specified, check if what was passed
    # in is a valid digest prefix.
    # 7 for 'sha256:' and 64 for the full digest
    if len(parts[1]) < 7 + 64:
      resolved = GetDockerDigestFromPrefix(image_name)
      if resolved == image_name:
        raise InvalidImageNameError(
            '[{0}] could not be resolved to a full digest.'.format(image_name))
      image_name = resolved
  return ValidateImagePathAndReturn(docker_name.Digest(image_name))


def GetDigestFromName(image_name):
  """Gets a digest object given a repository, tag or digest.

  Args:
    image_name: A docker image reference, possibly underqualified.

  Returns:
    a docker_name.Digest object.

  Raises:
    InvalidImageNameError: If no digest can be resolved.
  """
  tag_or_digest = GetDockerImageFromTagOrDigest(image_name)
  # If we got a digest, then just return it.
  if isinstance(tag_or_digest, docker_name.Digest):
    return tag_or_digest

  # If we got a tag, resolve it to a digest.
  def ResolveV2Tag(tag):
    with v2_image.FromRegistry(
        basic_creds=CredentialProvider(), name=tag,
        transport=http.Http()) as v2_img:
      if v2_img.exists():
        return v2_util.Digest(v2_img.manifest())
      return None

  def ResolveV22Tag(tag):
    with v2_2_image.FromRegistry(
        basic_creds=CredentialProvider(), name=tag,
        transport=http.Http()) as v2_2_img:
      if v2_2_img.exists():
        return v2_2_util.Digest(v2_2_img.manifest())
      return None

  # Resolve v2.2 first because we will exist via a compatibility layer.
  sha256 = ResolveV22Tag(tag_or_digest) or ResolveV2Tag(tag_or_digest)
  if not sha256:
    raise InvalidImageNameError('[{0}] is not a valid name.'.format(image_name))

  return docker_name.Digest('{registry}/{repository}@{sha256}'.format(
      registry=tag_or_digest.registry,
      repository=tag_or_digest.repository,
      sha256=sha256))


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
  with v2_2_image.FromRegistry(basic_creds=CredentialProvider(),
                               name=repository,
                               transport=http.Http()) as image:
    matches = [d for d in image.manifests() if d.startswith(prefix)]

    if len(matches) == 1:
      return repository_path + '@' + matches.pop()
    elif len(matches) > 1:
      raise InvalidImageNameError(
          '{0} is not a unique digest prefix. Options are {1}.]'
          .format(prefix, ', '.join(map(str, matches))))
    return digest


def GcloudifyRecoverableV2Errors(err, err_str_for_status):
  """Filters err based on the existence of err.status in err_str_for_status.

  Args:
    err: The V2DiagnotsticException to filter based on .status.
    err_str_for_status: a dict(int) -> string which maps HTTP status codes to a
      helpful error string to display to the user.

  Returns:
    A googlecloudsdk.core.exceptions.Error with the helpful error string
    specified in err_str_for_status, otherwise err. This prevents the gcloudSDK
    from 'crashing' and helps the user recover.
  """
  err_str = err_str_for_status.get(err.status, None)
  if err_str:
    return UserRecoverableV2Error(err_str)
  return err
