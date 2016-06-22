# Copyright 2014 Google Inc. All Rights Reserved.
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

"""This module holds exceptions raised by commands."""

from googlecloudsdk.core import exceptions


class NoAppIdentifiedError(exceptions.Error):
  pass


class DeployError(exceptions.Error):
  """Base class for app deploy failures."""


class RepoInfoLoadError(DeployError):
  """Indicates a failure to load a source context file."""

  def __init__(self, filename, inner_exception):
    self.filename = filename
    self.inner_exception = inner_exception

  def __str__(self):
    return 'Could not read repo info file {0}: {1}'.format(
        self.filename, self.inner_exception)


class MultiDeployError(DeployError):
  """Indicates a failed attempt to deploy multiple image urls."""

  def __str__(self):
    return ('No more than one service may be deployed when using the '
            'image-url flag')


class NoRepoInfoWithImageUrlError(DeployError):
  """The user tried to specify a repo info file with a docker image."""

  def __str__(self):
    return 'The --repo-info-file option is not compatible with --image_url.'


class DefaultBucketAccessError(DeployError):
  """Indicates a failed attempt to access a project's default bucket."""

  def __init__(self, project):
    self.project = project

  def __str__(self):
    return (
        'Could not retrieve the default Google Cloud Storage bucket for [{a}]. '
        'Please try again or use the [bucket] argument.').format(a=self.project)


class InvalidVersionIdError(exceptions.Error):
  """Indicates an invalid version ID."""

  def __init__(self, version):
    self.version = version

  def __str__(self):
    return (
        'Invalid version id [{version}].  May only contain lowercase letters, '
        'digits, and hyphens. Must begin and end with a letter or digit. Must '
        'not exceed 63 characters.').format(version=self.version)
