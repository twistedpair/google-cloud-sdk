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


class AbandonedReleaseError(exceptions.Error):
  """Error when an activity happens on an abandoned release."""

  def __init__(self, error_msg, release_name):
    error_template = '{} Release {} is abandoned.'.format(
        error_msg, release_name)
    super(AbandonedReleaseError, self).__init__(error_template)


class NoSnappedTargetsError(exceptions.Error):
  """Error when a release doesn't contain any snapped target resource."""

  def __init__(self, release_name):
    super(NoSnappedTargetsError, self).__init__(
        'No snapped targets in the release {}.'.format(release_name))


class InvalidReleaseNameError(exceptions.Error):
  """Error when a release has extra $ signs after expanding template terms."""

  def __init__(self, release_name, error_indices):
    error_msg = ("Invalid character '$'"
                 " for release name '{}' at indices:"
                 ' {}. Did you mean to use $DATE or $TIME?')
    super(InvalidReleaseNameError,
          self).__init__(error_msg.format(release_name, error_indices))


class CloudDeployConfigError(exceptions.Error):
  """Error raised for errors in the cloud deploy yaml config."""


class ListRolloutsError(exceptions.Error):
  """Error when it failed to list the rollouts that belongs to a release."""

  def __init__(self, release_name):
    super(ListRolloutsError,
          self).__init__('Failed to list rollouts for {}.'.format(release_name))


class RolloutIDExhaustedError(exceptions.Error):
  """Error when there are too many rollouts for a given release."""

  def __init__(self, release_name):
    super(RolloutIDExhaustedError, self).__init__(
        'Rollout name space exhausted in release {}. Use --rollout-id to specify rollout ID.'
        .format(release_name))


class RolloutInProgressError(exceptions.Error):
  """Error when there is a rollout in progress, no to-target value is given and a promote is attempted."""

  def __init__(self, release_name, target_name):
    super(RolloutInProgressError, self).__init__(
        'Unable to promote release {} to target {}. A rollout is already in progress.'
        .format(release_name, target_name))


class PipelineSuspendedError(exceptions.Error):
  """Error when a user performs an activity on a suspended pipeline."""

  def __init__(self, pipeline_name, failed_activity_msg):
    error_msg = '{} DeliveryPipeline {} is suspended.'.format(
        failed_activity_msg, pipeline_name)
    super(PipelineSuspendedError, self).__init__(error_msg)
