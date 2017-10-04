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
"""Utilities for Binary Authorization commands."""

import base64
import md5
import urlparse

from containerregistry.client import docker_name
from googlecloudsdk.core import resources
from googlecloudsdk.core.exceptions import Error


class BadImageUrlError(Error):
  """Raised when a container image URL cannot be parsed successfully."""


def CreateProviderRefFromProjectRef(project_ref):
  """Given a project ref, create a Container Analysis `providers` ref."""
  provider_name = project_ref.Name()
  return resources.REGISTRY.Create(
      'containeranalysis.providers', providersId=provider_name)


def ParseProviderNote(note_id, provider_ref):
  """Create a provider Note ref, suitable for attaching an Occurrence to."""
  provider_name = provider_ref.Name()
  return resources.REGISTRY.Parse(
      note_id, {'providersId': provider_name},
      collection='containeranalysis.providers.notes')


def NoteId(artifact_url, public_key, signature):
  """Returns Note id determined by supplied arguments."""
  digest = md5.new()
  digest.update(artifact_url)
  digest.update(public_key)
  digest.update(signature)
  artifact_url_md5 = base64.urlsafe_b64encode(digest.digest())
  return 'signature_test_{}'.format(artifact_url_md5)


def MakeSignaturePayload(container_image_url):
  """Creates a dict representing a JSON signature object to sign.

  Args:
    container_image_url: See `containerregistry.client.docker_name.Digest` for
      artifact URL validation and parsing details.  `container_image_url` must
      be a fully qualified image URL with a valid sha256 digest.

  Returns:
    Dictionary of nested dictionaries and strings, suitable for passing to
    `json.dumps` or similar.
  """
  try:
    repo_digest = docker_name.Digest(container_image_url)
  except docker_name.BadNameException as e:
    raise BadImageUrlError(e)
  return {
      'critical': {
          'identity': {
              'docker-reference': repo_digest.repository
          },
          'image': {
              'docker-manifest-digest': repo_digest.digest
          },
          'type': 'Google cloud binauthz container signature'
      }
  }


def NormalizeArtifactUrl(artifact_url):
  """Normalizes given URL by ensuring the scheme is https."""
  if '//' not in artifact_url:
    artifact_url = '//' + artifact_url
  parsed_url = urlparse.urlparse(artifact_url)
  url = urlparse.ParseResult('https', *parsed_url[1:]).geturl()
  try:
    docker_name.Digest(url)  # Just check over the URL.
  except docker_name.BadNameException as e:
    raise BadImageUrlError(e)
  return url
