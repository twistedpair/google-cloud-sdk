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

import datetime
import re

from googlecloudsdk.core import exceptions
from googlecloudsdk.core.util import timezone


class VersionValidationError(exceptions.Error):
  pass


class Version(object):
  """Value class representing a version resource.

  This wrapper around appengine_v1beta4_messages.Version is necessary because
  Versions don't have traffic split, project, or last_deployed_time as a
  datetime object.
  """

  _RESOURCE_PATH_PARTS = 3  # project/service/version

  # This is the name in the Version resource from the API
  _VERSION_NAME_PATTERN = ('apps/(?P<project>.*)/'
                           'modules/(?P<service>.*)/'
                           'versions/(?P<version>.*)')

  def __init__(self, project, service, version, traffic_split=None,
               last_deployed_time=None):
    self.project = project
    self.service = service
    self.version = version
    self.traffic_split = traffic_split
    self.last_deployed_time = last_deployed_time

  @property
  def id(self):
    return self.version.id

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
    project, service_id, version_id = re.match(cls._VERSION_NAME_PATTERN,
                                               version.name).groups()
    traffic_split = service and service.split.get(version_id, 0.0)
    last_deployed = None
    try:
      if version.creationTime:
        last_deployed_utc = datetime.datetime.strptime(
            version.creationTime,
            '%Y-%m-%dT%H:%M:%S.%fZ').replace(microsecond=0,
                                             tzinfo=timezone.GetTimeZone('UTC'))
        last_deployed = last_deployed_utc.astimezone(
            timezone.GetTimeZone('local'))
    except ValueError:
      pass
    return cls(project, service_id, version_id, traffic_split=traffic_split,
               last_deployed_time=last_deployed)

  def __eq__(self, other):
    return (type(other) is Version and
            self.project == other.project and
            self.service == other.service and
            self.version == other.version)

  def __ne__(self, other):
    return not self == other

  def __cmp__(self, other):
    return cmp((self.project, self.service, self.version),
               (other.project, other.service, other.version))

  def __str__(self):
    return '{0}/{1}/{2}'.format(self.project, self.service, self.version)


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
                                                version.version))


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


def _FilterVersions(all_versions, service, versions):
  """Filter all of the project's versions down to just the requested ones.

  Args:
    all_versions: list of Version representing all services in the project.
    service: str or None. If specified, only return versions for the specific
      service.
    versions: list of version names. If given, only return versions with one of
      the given names.

  Returns:
    list of Version

  Raises:
    VersionValidationError: if the specified service was not found
  """
  filtered_versions = all_versions
  if service:
    if service not in [v.service for v in all_versions]:
      raise VersionValidationError('Service [{0}] not found.'.format(service))
    filtered_versions = [v for v in all_versions if v.service == service]

  if versions:
    filtered_versions = [v for v in filtered_versions if v.version in versions]

  return filtered_versions


def GetMatchingVersions(all_versions, args_versions, args_service, project):
  """Return a list of versions to act on based on user arguments.

  Args:
    all_versions: list of Version representing all services in the project.
    args_versions: list of string, version names/resource paths to filter for.
      If empty, match all versions.
    args_service: string or None, service name. If given, only match versions in
      the given service.
    project: the current project ID

  Returns:
    list of matching Version

  Raises:
    VersionValidationError: If an improper combination of arguments is given
      (ex. a service is provided, but args_versions are given as resource
      paths).
  """
  # If resource path(s) are given, use those. Otherwise, filter all available
  # versions based on the given service/version specifiers.
  versions = None
  if any('/' in version for version in args_versions):
    versions = ParseVersionResourcePaths(args_versions, project)
    _ValidateServicesAreSubset(versions, all_versions)
    for version in versions:
      if args_service and version.service != args_service:
        raise VersionValidationError(
            'If you provide a resource path as an argument, it must match the '
            'specified service.')
      version_from_api = all_versions[all_versions.index(version)]
      version.traffic_split = version_from_api.traffic_split
  else:
    versions = _FilterVersions(all_versions, args_service, args_versions)
  return versions
