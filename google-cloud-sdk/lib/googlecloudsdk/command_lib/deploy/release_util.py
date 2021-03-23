# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for the cloud deploy release commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

import six


class ParserError(exceptions.Error):
  """Error parsing JSON into a dictionary."""

  def __init__(self, path, msg):
    """Initialize a release_util.ParserError.

    Args:
      path: build artifacts file path.
      msg: error message.
    """
    msg = 'parsing {path}: {msg}'.format(
        path=path,
        msg=msg,
    )
    super(ParserError, self).__init__(msg)


def SetBuildArtifacts(images, messages, release_config):
  """Set build_artifacts field of the release message.

  Args:
    images: docker image name and tag dictionary.
    messages: Module containing the Cloud Deploy messages.
    release_config: Cloud Deploy release message.

  Returns:
    Cloud Deploy release message.
  """
  if not images:
    return release_config
  build_artifacts = []
  for key, value in sorted(six.iteritems(images)):  # Sort for tests
    build_artifacts.append(messages.BuildArtifact(imageName=key, tag=value))
  release_config.buildArtifacts = build_artifacts

  return release_config


def LoadBuildArtifactFile(path):
  """Load images from a file containing JSON build data.

  Args:
    path: build artifacts file path.

  Returns:
    Docker image name and tag dictionary.
  """
  with files.FileReader(path) as f:  # Returns user-friendly error messages
    try:
      structured_data = yaml.load(f, file_hint=path)
    except yaml.Error as e:
      raise ParserError(path, e.inner_error)
    images = {}
    for build in structured_data['builds']:
      images[build['imageName']] = build['tag']

    return images
