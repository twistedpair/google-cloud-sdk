# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import re

from containerregistry.client import docker_name
from googlecloudsdk.core.exceptions import Error
import six
from six.moves import urllib

# The patterns below are translatated from the back-end code, which is based on
# https://github.com/distribution/distribution/blob/4bf3547399eb8a27ee2ec463333c8c456d801345/reference/regexp.go
# Except for the following changes due to lack of support in the "re" library:
# [:alnum:] replaced by A-Za-z0-09
# [:digit:] replaced by \d
# [:lower:] replaced by a-z
_LOWER_ALPHA_NUMERIC_PATTERN = r'[a-z0-9]+'
_SEPARATOR_PATTERN = r'[_.]|__|[-]*'
_DOMAIN_COMPONENT_PATTERN = (
    r'(?:[A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9-]*[A-Za-z0-9])'
)
_TAG_PATTERN = r'[\w][\w.-]{0,127}'
_DIGEST_ALGORITHM_COMPONENT_PATTERN = r'sha256'

_PATH_COMPONENT_PATTERN = (
    _LOWER_ALPHA_NUMERIC_PATTERN
    + r'(?:'
    + _SEPARATOR_PATTERN
    + _LOWER_ALPHA_NUMERIC_PATTERN
    + r')*'
)

_DOMAIN_PATTERN = (
    _DOMAIN_COMPONENT_PATTERN
    + r'(?:\.'
    + _DOMAIN_COMPONENT_PATTERN
    + r')*'
    + r'(?::[\d]+)?'
)

_NAME_PATTERN = (
    r'(?:'
    + _DOMAIN_PATTERN
    + r'/)?'
    + _PATH_COMPONENT_PATTERN
    + r'(?:/'
    + _PATH_COMPONENT_PATTERN
    + r')*'
)

_ALGORITHM_PATTERN = (
    _DIGEST_ALGORITHM_COMPONENT_PATTERN
    + r'(?:[+.-_]'
    + _DIGEST_ALGORITHM_COMPONENT_PATTERN
    + r')*'
)

_DIGEST_PATTERN = (
    r'(?P<algorithm>'
    + _ALGORITHM_PATTERN
    + r')'
    + r':'
    + _LOWER_ALPHA_NUMERIC_PATTERN
)

# Tag-and-digest reference only (not the full URL).
_TAG_AND_DIGEST_PATTERN = (
    r'(?P<tag>'
    + _TAG_PATTERN
    + r')@'
    + r'(?P<digest>'
    + _DIGEST_PATTERN
    + r')'
)

# Full image URL including tag and digest.
_TAG_AND_DIGEST_REFERENCE_PATTERN = (
    r'(?P<name>'
    + _NAME_PATTERN
    + r')'
    + r':'
    + r'(?P<tag_and_digest>'
    + _TAG_AND_DIGEST_PATTERN
    + r')'
)


class BadImageUrlError(Error):
  """Raised when a container image URL cannot be parsed successfully."""


def _ReplaceImageUrlScheme(image_url, scheme):
  """Returns the passed `image_url` with the scheme replaced.

  Args:
    image_url: The URL to replace (or strip) the scheme from. (string)
    scheme: The scheme of the returned URL.  If this is an empty string or
      `None`, the scheme is stripped and the leading `//` of the resulting URL
      will be stripped off.
  Raises:
    BadImageUrlError: `image_url` isn't valid.
  """
  scheme = scheme or ''
  parsed_url = urllib.parse.urlparse(image_url)

  # If the URL has a scheme but not a netloc, then it must have looked like
  # 'scheme:///foo/bar', which is invalid for the purpose of attestation.
  if parsed_url.scheme and not parsed_url.netloc:
    # TODO(b/315328649): This error is also triggered by a URL with no scheme
    # and a port number, e.g., 'example.com:443/foo'.
    raise BadImageUrlError(
        "Image URL '{image_url}' is invalid because it does not have a host "
        'component.'.format(image_url=image_url))

  # If there is neither a scheme nor a netloc, this means that an unqualified
  # URL was passed, like 'gcr.io/foo/bar'.  In this case we canonicalize the URL
  # by prefixing '//', which will cause urlparse to correctly pick up the
  # netloc.
  if not parsed_url.netloc:
    parsed_url = urllib.parse.urlparse('//{}'.format(image_url))

  # Finally, we replace the scheme and generate the URL.  If we were stripping
  # the scheme, the result will be prefixed with '//', which we strip off.  If
  # the scheme is non-empty, the lstrip is a no-op.
  return parsed_url._replace(scheme=scheme).geturl().lstrip('/')


def MakeSignaturePayloadDict(container_image_url):
  """Creates a dict representing a JSON signature object to sign.

  Args:
    container_image_url: See `containerregistry.client.docker_name.Digest` for
      artifact URL validation and parsing details.  `container_image_url` must
      be a fully qualified image URL with a valid sha256 digest.

  Returns:
    Dictionary of nested dictionaries and strings, suitable for passing to
    `json.dumps` or similar.
  """
  # These functions allow the URL to have a scheme. GetImageName doesn't include
  # the scheme in the name.
  digest = GetImageDigest(container_image_url)
  name = GetImageName(container_image_url)

  return {
      'critical': {
          'identity': {
              'docker-reference': name,
          },
          'image': {
              'docker-manifest-digest': digest,
          },
          'type': 'Google cloud binauthz container signature',
      },
  }


def MakeSignaturePayload(container_image_url):
  """Creates a JSON bytestring representing a signature object to sign.

  Args:
    container_image_url: See `containerregistry.client.docker_name.Digest` for
      artifact URL validation and parsing details.  `container_image_url` must
      be a fully qualified image URL with a valid sha256 digest.

  Returns:
    A bytestring representing a JSON-encoded structure of nested dictionaries
    and strings.
  """
  payload_dict = MakeSignaturePayloadDict(container_image_url)
  # `separators` is specified as a workaround to the native `json` module's
  # https://bugs.python.org/issue16333 which results in inconsistent
  # serialization in older versions of Python.
  payload = json.dumps(
      payload_dict,
      ensure_ascii=True,
      indent=2,
      separators=(',', ': '),
      sort_keys=True,
  )
  # NOTE: A newline is appended for backwards compatibility with the previous
  # payload serialization which relied on gcloud's default JSON serialization.
  return '{}\n'.format(payload).encode('utf-8')


def _ValidateUrl(artifact_url):
  # Effectively a valid URL is either anything that
  # containerregistry.client.docker_name accepts, or a tag-and-digest URL
  # defined by this pattern.
  match = re.fullmatch(_TAG_AND_DIGEST_REFERENCE_PATTERN, artifact_url)
  if match and match.group('digest'):
    return
  try:
    docker_name.Digest(artifact_url)
  except docker_name.BadNameException as e:
    raise BadImageUrlError(e)


def RemoveArtifactUrlScheme(artifact_url):
  """Ensures the given URL has no scheme.

  E.g., replaces "https://gcr.io/foo/bar" with "gcr.io/foo/bar" and leaves
  "gcr.io/foo/bar" unchanged).

  Args:
    artifact_url: A URL string.
  Returns:
    The URL with the scheme removed.
  """
  url_without_scheme = _ReplaceImageUrlScheme(artifact_url, scheme='')
  _ValidateUrl(url_without_scheme)
  return url_without_scheme


def _GetImageNameFromTagAndDigestUrl(artifact_url):
  """Returns the name of an image URL that has both a tag and digest.

  Args:
    artifact_url: An image url, e.g., "gcr.io/foo/bar@sha256:123". This should
    not include a scheme (e.g., "https://")

  Returns:
    The name part of the URL, e.g., "gcr.io/foo/bar"
  """
  match = re.fullmatch(_TAG_AND_DIGEST_REFERENCE_PATTERN, artifact_url)
  if not match or not match.group('name'):
    return None
  return match.group('name')


def GetImageName(artifact_url):
  """Returns the name of an image given its URL.

  This means the part without the reference (tag and/or digest). This also does
  not include the URL scheme, if any.

  Args:
    artifact_url: An image url, e.g., "https://gcr.io/foo/bar@sha256:123"

  Returns:
    The image name, e.g., "gcr.io/foo/bar"
  """
  url_without_scheme = _ReplaceImageUrlScheme(artifact_url, scheme='')

  # TODO(b/268691285): Temporary workaround for the fact that
  # containerregistry.client doesn't support tag-and-digest URLs. Replace this
  # when upgraded containerregistry library is available.
  name = _GetImageNameFromTagAndDigestUrl(url_without_scheme)
  if name:
    return name

  # For URLs without tag-and-digest, rely on containerregistry.client.
  try:
    # The validation logic in `docker_name` silently produces incorrect results
    # if the passed URL has a scheme.
    digest = docker_name.Digest(url_without_scheme)
  except docker_name.BadNameException as e:
    raise BadImageUrlError(e)
  return six.text_type(digest.as_repository())


def _GetImageDigestFromTagAndDigestUrl(artifact_url):
  """Returns the digest of an image URL that has both a tag and digest.

  Args:
    artifact_url: An image url, e.g., "https://gcr.io/foo/bar:latest@sha256:123"

  Returns:
    If the URL is well-formed and has both a tag and a digest, returns the
    digest, e.g., "sha256:123". Otherwise, returns None.
  """
  match = re.fullmatch(_TAG_AND_DIGEST_REFERENCE_PATTERN, artifact_url)
  if not match or not match.group('digest'):
    return None
  return match.group('digest')


def GetImageDigest(artifact_url):
  """Returns the digest of an image given its url.

  Args:
    artifact_url: An image url, e.g., "https://gcr.io/foo/bar@sha256:123"

  Returns:
    The image digest, e.g., "sha256:123"
  """
  url_without_scheme = _ReplaceImageUrlScheme(artifact_url, scheme='')

  # TODO(b/268691285): Temporary workaround for the fact that
  # containerregistry.client doesn't support tag-and-digest URLs. Replace this
  # when upgraded containerregistry library is available.
  digest = _GetImageDigestFromTagAndDigestUrl(url_without_scheme)
  if digest:
    return digest

  # For URLs without tag-and-digest, rely on containerregistry.client.
  try:
    # The validation logic in `docker_name` silently produces incorrect results
    # if the passed URL has a scheme.
    digest = docker_name.Digest(url_without_scheme)
  except docker_name.BadNameException as e:
    raise BadImageUrlError(e)
  return digest.digest


def PaeEncode(dsse_type, body):
  """Pae encode input using the specified dsse type.

  Args:
    dsse_type: DSSE envelope type.
    body: payload string.

  Returns:
    Pae-encoded payload byte string.
  """
  dsse_type_bytes = dsse_type.encode('utf-8')
  body_bytes = body.encode('utf-8')
  return b' '.join([
      b'DSSEv1',
      b'%d' % len(dsse_type_bytes),
      dsse_type_bytes,
      b'%d' % len(body_bytes),
      body_bytes,
  ])
