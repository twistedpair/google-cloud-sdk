# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""This module holds exceptions raised by Cloud Run commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
from googlecloudsdk.api_lib.util import exceptions as exceptions_util
from googlecloudsdk.core import exceptions


class BucketAccessError(exceptions.Error):
  """Indicates a failed attempt to access a GCS bucket."""
  pass


class ConfigurationError(exceptions.Error):
  """Indicates an error in configuration."""
  pass


class ServiceNotFoundError(exceptions.Error):
  """Indicates that a provided service name was not found."""
  pass


class RevisionNotFoundError(exceptions.Error):
  """Indicates that a provided revision name was not found."""
  pass


class DockerVersionError(exceptions.Error):
  """Indicates an error in determining the docker version."""
  pass


class AmbiguousContainerError(exceptions.Error):
  """More than one container fits our criteria, we do not know which to run."""
  pass


class CloudSQLError(exceptions.Error):
  """Malformed instances string for CloudSQL."""
  pass


class ContainerIdError(exceptions.Error):
  """Container Id cannot be found by docker."""
  pass


class NoActiveRevisionsError(exceptions.Error):
  """Active revisions were expected but not found."""
  pass


class SourceNotSupportedError(exceptions.Error):
  """Your Cloud Run install does not support source deployment."""
  pass


class NoConfigurationChangeError(exceptions.Error):
  """No configuration changes were requested."""
  pass


class UnknownDeployableError(exceptions.Error):
  """Could not identify the deployable app, function, or container."""
  pass


class AppNotReadyError(exceptions.InternalError):
  """The application must be uploaded before it can be deployed."""
  pass


class DeploymentFailedError(exceptions.Error):
  """An error was encountered during deployment."""
  pass


class DomainMappingCreationError(exceptions.Error):
  """An error was encountered during the creation of a domain mapping."""


class BadImageError(exceptions_util.HttpException):
  """Invalid image provided in the revision template."""

  # The relevant field that'll have a violation.
  IMAGE_ERROR_FIELD = 'spec.revisionTemplate.spec.container.image'

  def __init__(self, http_exception):
    super(BadImageError, self).__init__(
        http_exception,
        '{{field_violations.{}}}'.format(self.IMAGE_ERROR_FIELD))


class NoTLSError(exceptions.Error):
  """TLS 1.2 support is required to connect to GKE.

  Your Python installation does not support TLS 1.2. For Python2, please upgrade
  to version 2.7.9 or greater; for Python3, please upgrade to version 3.4 or
  greater.
  """


class MalformedLabelError(exceptions_util.HttpException):
  """Invalid label key or value provided in the service metadata."""

  # The relevant field that'll have a violation.
  LABEL_ERROR_FIELD = 'label'

  def __init__(self, http_exception):
    super(MalformedLabelError, self).__init__(
        http_exception,
        '{{field_violations.{}}}'.format(self.LABEL_ERROR_FIELD))


class KubernetesError(exceptions.Error):
  """A generic kubernetes error was encountered."""


class UnsupportedOperationError(exceptions.Error):
  """The requested operation is not supported."""
  pass


class KubernetesExceptionParser(object):
  """Converts a kubernetes exception to an object."""

  def __init__(self, http_error):
    """Wraps a generic http error returned by kubernetes.

    Args:
      http_error: apitools.base.py.exceptions.HttpError, The error to wrap.
    """
    self._wrapped_error = http_error
    self._content = json.loads(http_error.content)

  @property
  def status_code(self):
    return self._wrapped_error.status_code

  @property
  def url(self):
    return self._wrapped_error.url

  @property
  def api_version(self):
    return self._content['apiVersion']

  @property
  def api_name(self):
    return self._content['details']['group']

  @property
  def resource_name(self):
    return self._content['details']['name']

  @property
  def resource_kind(self):
    return self._content['details']['kind']

  @property
  def default_message(self):
    return self._content['messsage']

  @property
  def causes(self):
    """Returns list of causes uniqued by the message."""
    return {c['message']: c for c in self._content['details']['causes']
           }.values()
