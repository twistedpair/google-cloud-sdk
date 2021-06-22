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
"""Exceptions for cloud deploy libraries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions


class ParserError(exceptions.Error):
  """Error parsing JSON into a dictionary."""

  def __init__(self, path, msg):
    """Initialize a exceptions.ParserError.

    Args:
      path: str, build artifacts file path.
      msg: str, error message.
    """
    msg = 'parsing {path}: {msg}'.format(
        path=path,
        msg=msg,
    )
    super(ParserError, self).__init__(msg)


class ReleaseInactiveError(exceptions.Error):
  """Error when a release is not deployed to any target."""

  def __init__(self):
    super(ReleaseInactiveError, self).__init__(
        'This release is not deployed to a target in the active delivery pipeline. '
        'Include the --to-target parameter to indicate which target to promote to.'
    )


class NoSnappedTargets(exceptions.Error):
  """Error when a release doesn't contain any snapped target resource."""

  def __init__(self, release_name):
    super(NoSnappedTargets, self).__init__(
        'No snapped targets in the release {}.'.format(release_name))


class CloudDeployConfigError(exceptions.Error):
  """Error raised for errors in the cloud deploy yaml config."""


class TargetNotFound(exceptions.Error):
  """Error when a give target ID can't be found in either targets or shared targets."""

  def __init__(self, target_id):
    super(TargetNotFound,
          self).__init__('Target {} not found.'.format(target_id))
