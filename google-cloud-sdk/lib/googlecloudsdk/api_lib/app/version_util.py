# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for dealing with version resources."""

import re

from googlecloudsdk.api_lib.app.api import operations
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import text
from googlecloudsdk.core.util import times


class VersionValidationError(exceptions.Error):
  pass


class VersionsDeleteError(exceptions.Error):
  pass


class Version(object):
  """Value class representing a version resource.

  This wrapper around appengine_v1beta4_messages.Version is necessary because
  Versions don't have traffic split, project, or last_deployed_time as a
  datetime object.
  """

  # The smallest allowed traffic split is 1e-3. Because of floating point
  # peculiarities, we use 1e-4 as our max allowed epsilon when testing whether a
  # version is receiving all traffic.
  _ALL_TRAFFIC_EPSILON = 1e-4

  _RESOURCE_PATH_PARTS = 3  # project/service/version

  # This is the name in the Version resource from the API
  _VERSION_NAME_PATTERN = ('apps/(?P<project>.*)/'
                           'modules/(?P<service>.*)/'
                           'versions/(?P<version>.*)')

  def __init__(self, project, service, version_id, traffic_split=None,
               last_deployed_time=None, version_resource=None):
    self.project = project
    self.service = service
    self.id = version_id
    self.version = version_resource
    self.traffic_split = traffic_split
    self.last_deployed_time = last_deployed_time

  @classmethod
  def FromResourcePath(cls, path):
    parts = path.split('/')
    if not 0 < len(parts) <= cls._RESOURCE_PATH_PARTS:
      raise VersionValidationError('[{0}] is not a valid resource path. '
                                   'Expected <project>/<service>/<version>')

    parts = [None] * (cls._RESOURCE_PATH_PARTS - len(parts)) + parts
    return cls(*parts)

  @classmethod
  def FromVersionResource(cls, version, service):
    """Convert a appengine_v1beta4_messages.Version into a wrapped Version."""
    project, service_id, _ = re.match(cls._VERSION_NAME_PATTERN,
                                      version.name).groups()
    traffic_split = service and service.split.get(version.id, 0.0)
    last_deployed = None
    try:
      if version.creationTime:
        last_deployed_dt = times.ParseDateTime(version.creationTime).replace(
            microsecond=0)
        last_deployed = times.LocalizeDateTime(last_deployed_dt)
    except ValueError:
      pass
    return cls(project, service_id, version.id, traffic_split=traffic_split,
               last_deployed_time=last_deployed, version_resource=version)

  def IsReceivingAllTraffic(self):
    return abs(self.traffic_split - 1.0) < self._ALL_TRAFFIC_EPSILON

  def __eq__(self, other):
    return (type(other) is Version and
            self.project == other.project and
            self.service == other.service and
            self.id == other.id)

  def __ne__(self, other):
    return not self == other

  def __cmp__(self, other):
    return cmp((self.project, self.service, self.id),
               (other.project, other.service, other.id))

  def __str__(self):
    return '{0}/{1}/{2}'.format(self.project, self.service, self.id)


def _ValidateServicesAreSubset(filtered_versions, all_versions):
  """Validate that each version in filtered_versions is also in all_versions.

  Args:
    filtered_versions: list of Version representing a filtered subset of
      all_versions.
    all_versions: list of Version representing all versions in the current
      project.

  Raises:
    VersionValidationError: If a service or version is not found.
  """
  for version in filtered_versions:
    if version.service not in [v.service for v in all_versions]:
      raise VersionValidationError(
          'Service [{0}] not found.'.format(version.service))
    if version not in all_versions:
      raise VersionValidationError(
          'Version [{0}/{1}] not found.'.format(version.service,
                                                version.id))


def ParseVersionResourcePaths(paths, project):
  """Parse the list of resource paths specifying versions.

  Args:
    paths: The list of resource paths by which to filter.
    project: The current project. Used for validation.

  Returns:
    list of Version

  Raises:
    VersionValidationError: If not all versions are valid resource paths for the
      current project.
  """
  versions = map(Version.FromResourcePath, paths)

  for version in versions:
    if not (version.project or version.service):
      raise VersionValidationError('If you provide a resource path as an '
                                   'argument, all arguments must be resource '
                                   'paths.')
    if version.project and version.project != project:
      raise VersionValidationError(
          'All versions must be in the current project.')
    version.project = project
  return versions


def GetMatchingVersions(all_versions, versions, service):
  """Return a list of versions to act on based on user arguments.

  Args:
    all_versions: list of Version representing all services in the project.
    versions: list of string, version names to filter for.
      If empty, match all versions.
    service: string or None, service name. If given, only match versions in the
      given service.

  Returns:
    list of matching Version

  Raises:
    VersionValidationError: If an improper combination of arguments is given.
  """
  filtered_versions = all_versions
  if service:
    if service not in [v.service for v in all_versions]:
      raise VersionValidationError('Service [{0}] not found.'.format(service))
    filtered_versions = [v for v in all_versions if v.service == service]

  if versions:
    filtered_versions = [v for v in filtered_versions if v.id in versions]

  return filtered_versions


def DeleteVersions(api_client, versions):
  """Delete the given version of the given services."""
  errors = {}
  for version in versions:
    version_path = '{0}/{1}'.format(version.service, version.id)
    try:
      with console_io.ProgressTracker('Deleting [{0}]'.format(version_path)):
        api_client.DeleteVersion(version.service, version.id)
    except (calliope_exceptions.HttpException, operations.OperationError,
            operations.OperationTimeoutError) as err:
      errors[version_path] = str(err)

  if errors:
    printable_errors = {}
    for version_path, error_msg in errors.items():
      printable_errors[version_path] = '[{0}]: {1}'.format(version_path,
                                                           error_msg)
    raise VersionsDeleteError(
        'Issue deleting {0}: [{1}]\n\n'.format(
            text.Pluralize(len(printable_errors), 'version'),
            ', '.join(printable_errors.keys())) +
        '\n\n'.join(printable_errors.values()))
