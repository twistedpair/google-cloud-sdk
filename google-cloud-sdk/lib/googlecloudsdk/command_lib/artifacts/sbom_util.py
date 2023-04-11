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
"""Utility for handling SBOM files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import re
from googlecloudsdk.api_lib.artifacts import exceptions as ar_exceptions
from googlecloudsdk.core.util import files
import six


_SBOM_FORMAT_SPDX = 'spdx'
_SBOM_FORMAT_CYCLONEDX = 'cyclonedx'
_UNSUPPORTED_SBOM_FORMAT_ERROR = (
    'The file is not in a supported SBOM format. ' +
    'Only spdx and cyclonedx are supported.'
    )


def _ParseSpdx(data):
  """Retrieves version from the given SBOM dict.

  Args:
    data: Parsed json content of an SBOM file.

  Raises:
    ar_exceptions.InvalidInputValueError: If the sbom format is not supported.

  Returns:
    A SbomFile object with metadata of the given sbom.
  """
  invalid = True
  spdx_version = data['spdxVersion']

  if isinstance(spdx_version, six.string_types):
    r = re.match(r'^SPDX-([0-9]+[.][0-9]+)$', spdx_version)
    if r is not None:
      version = r.group(1)
      invalid = False
  if invalid:
    raise ar_exceptions.InvalidInputValueError(
        'Unable to read spdxVersion {0}.'.format(spdx_version)
    )

  return SbomFile(sbom_format=_SBOM_FORMAT_SPDX, version=version)


def _ParseCycloneDx(data):
  """Retrieves version from the given SBOM dict.

  Args:
    data: Parsed json content of an SBOM file.

  Raises:
    ar_exceptions.InvalidInputValueError: If the sbom format is not supported.

  Returns:
    A SbomFile object with metadata of the given sbom.
  """
  if 'specVersion' not in data:
    raise ar_exceptions.InvalidInputValueError(
        'Unable to find specVersion in the CycloneDX file.'
    )

  invalid = True
  if isinstance(data['specVersion'], six.string_types):
    r = re.match(r'^[0-9]+[.][0-9]+$', data['specVersion'])
    if r is not None:
      version = r.group()
      invalid = False
  if invalid:
    raise ar_exceptions.InvalidInputValueError(
        'Unable to read specVersion {0}.'.format(data['specVersion'].__str__())
    )

  return SbomFile(sbom_format=_SBOM_FORMAT_CYCLONEDX, version=version)


def ParseJsonSbom(file_path):
  """Retrieves information about a docker image based on the fully-qualified name.

  Args:
    file_path: str, The sbom file location.

  Raises:
    ar_exceptions.InvalidInputValueError: If the sbom format is not supported.

  Returns:
    An SbomFile object with metadata of the given sbom.
  """

  try:
    content = files.ReadFileContents(file_path)
    data = json.loads(content)
  except ValueError as e:
    raise ar_exceptions.InvalidInputValueError(
        'The file is not a valid JSON file', e
    )
  except files.Error as e:
    raise ar_exceptions.InvalidInputValueError(
        'Failed to read the sbom file', e
    )

  # Detect if it's spdx or cyclonedx.
  if 'spdxVersion' in data:
    return _ParseSpdx(data)
  elif data.get('bomFormat') == 'CycloneDX':
    return _ParseCycloneDx(data)
  else:
    raise ar_exceptions.InvalidInputValueError(_UNSUPPORTED_SBOM_FORMAT_ERROR)


class SbomFile(object):
  """Holder for SBOM file's metadata.

  Properties:
    sbom_format: Data format of the SBOM file.
    version: Version of the SBOM format.
  """

  def __init__(self, sbom_format, version):
    self._sbom_format = sbom_format
    self._version = version

  @property
  def sbom_format(self):
    return self._sbom_format

  @property
  def version(self):
    return self._version
