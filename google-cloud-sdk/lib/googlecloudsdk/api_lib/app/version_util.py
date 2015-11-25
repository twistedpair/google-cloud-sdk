# Copyright 2015 Google Inc. All Rights Reserved.

"""Utilities for dealing with version resources."""

from googlecloudsdk.core import exceptions


class VersionValidationError(exceptions.Error):
  pass


class Version(object):
  """Value class representing a version resource."""

  _RESOURCE_PATH_PARTS = 3  # project/service/version

  def __init__(self, project, service, version, traffic_allocation=None):
    self.project = project
    self.service = service
    self.version = version
    self.traffic_allocation = traffic_allocation

  @classmethod
  def FromResourcePath(cls, path):
    parts = path.split('/')
    if not 0 < len(parts) <= cls._RESOURCE_PATH_PARTS:
      raise VersionValidationError('[{0}] is not a valid resource path. '
                                   'Expected <project>/<service>/<version>')

    parts = [None] * (cls._RESOURCE_PATH_PARTS - len(parts)) + parts
    return cls(*parts)

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


def _ParseVersionResourcePaths(paths, project):
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
    if args_service:
      raise VersionValidationError('If you provide a resource path as an '
                                   'argument, you must not specify a service.')
    versions = _ParseVersionResourcePaths(args_versions, project)
    _ValidateServicesAreSubset(versions, all_versions)
    for version in versions:
      version_from_api = all_versions[all_versions.index(version)]
      version.traffic_allocation = version_from_api.traffic_allocation
  else:
    versions = _FilterVersions(all_versions, args_service, args_versions)
  return versions
