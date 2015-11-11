# Copyright 2015 Google Inc. All Rights Reserved.
"""Utilities for manipulating GCE instances running an App Engine project."""

from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties


class ProjectMismatchError(exceptions.Error):
  pass


class InvalidInstanceSpecificationError(exceptions.Error):
  pass


def _GetInstanceMetadata(instance):
  items = instance['metadata'].get('items', [])
  return dict([(item['key'], item['value']) for item in items])


class AppEngineInstance(object):
  """Value class for instances running the current App Engine project."""

  def __init__(self, service, version, id_, instance=None):
    self.service = service
    self.version = version
    self.id = id_
    self.instance = instance

  # TODO(zjn): remove after API support for listing instances (b/24778093).
  @classmethod
  def IsInstance(cls, instance):
    """Return whether instance was created by App Engine.

    Can return false positives, if a user gives their instance a name patterned
    like the automatically created ones.

    Args:
      instance: a Compute Engine instance

    Returns:
      bool, whether instance is an automatically created instance.
    """
    metadata = _GetInstanceMetadata(instance)
    return ('gae_backend_name' in metadata and
            'gae_backend_version' in metadata and
            len(instance['name'].rsplit('-', 1)) > 1)

  # TODO(zjn): remove after API support for listing instances (b/24778093).
  @classmethod
  def FromComputeEngineInstance(cls, instance):
    """Create an AppEngineInstance object from its Compute Engine instance.

    Args:
      instance: dict representing a Compute Engine instance (ex. an entity from
        the output of `gcloud compute instances list`).

    Raises:
      KeyError, if the required metadata is missing (ex. the Compute Engine
        instance is not an App Engine VM)

    Returns:
      AppEngineInstance, instance object wrapping the Compute Engine instance
        with appropriate metadata parsed.
    """
    metadata = _GetInstanceMetadata(instance)
    service = metadata['gae_backend_name']
    version = metadata['gae_backend_version']
    # The name of the instance is the only place that contains the instance id;
    # we have to resort to string manipulation here. (The name will be something
    # like 'gae-service-version-inst', where 'inst' is the instance id.)
    id_ = instance['name'].rsplit('-', 1)[-1]
    return cls(service, version, id_, instance)

  @classmethod
  def FromResourcePath(cls, path, service=None, version=None):
    """Convert a resource path into an AppEngineInstance.

    A resource path is of the form '<project>/<service>/<version>/<instance>'.
    '<project>' can always be omitted; '<service>' and '<version>' can be
    omitted if they are provided as flags (though if service is specified as a
    flag, version must be as well).

    >>> (AppEngineInstance.FromResourcePath('a/b/c') ==
         ...  AppEngineInstance('a', 'b', 'c'))
    True
    >>> (AppEngineInstance.FromResourcePath('project/a/b/c') ==
    ...  AppEngineInstance('a', 'b', 'c'))
    True
    >>> try:
    ...   AppEngineInstance.FromResourcePath('wrong-project/a/b/c')
    ...   print False
    ... except ProjectMismatchError:
    ...   print True
    ...
    True
    >>> (AppEngineInstance.FromResourcePath('b/c', service='a') ==
    ...  AppEngineInstance('a', 'b', 'c'))
    True
    >>> (AppEngineInstance.FromResourcePath('c', service='a', version='b') ==
    ...  AppEngineInstance('a', 'b', 'c'))
    True

    Args:
      path: str, the resource path
      service: the service of the instance (replaces the service from the
        resource path)
      version: the version of the instance (replaces the version from the
        resource path)

    Returns:
      AppEngineInstance, an AppEngineInstance representing the path

    Raises:
      ProjectMismatchError: if the resource path includes a project that doesn't
        match the current one.
      InvalidInstanceSpecificationError: if the instance is over- or
        under-specified
    """
    parts = path.split('/')
    if len(parts) == 4:
      # Project was specified. Validate, then ignore it.
      current_project = properties.VALUES.core.project.Get(required=True)
      specified_project = parts[0]
      if specified_project != current_project:
        raise ProjectMismatchError(
            'Specified instance [{0}] does not belong to the current '
            'project [{1}].'.format(path, current_project))
      parts = parts[1:]
    if version and not service:
      raise InvalidInstanceSpecificationError(
          'If a version is specified, a service must be, too.')
    if version:
      parts.insert(0, version)
    if service:
      parts.insert(0, service)
    if len([p for p in parts if p]) != 3:
      provided_parts = 'Path: [{0}]'.format(path)
      if service:
        provided_parts += '\nService: [{0}]'.format(service)
      if version:
        provided_parts += '\nVersion: [{0}]'.format(version)
      raise InvalidInstanceSpecificationError(
          'Instance resource path is incorrectly specified. '
          'Please provide exactly one service, version, and instance id, '
          'and optionally one project.\n\n'
          'You provided:\n' + provided_parts)
    return cls(*parts)

  def __eq__(self, other):
    return (type(self) is type(other) and
            self.service == other.service and
            self.version == other.version and
            self.id == other.id)

  def __ne__(self, other):
    return not self == other

  # needed for set comparisons in tests
  def __hash__(self):
    return hash((self.service, self.version, self.id))

  def __repr__(self):
    return '/'.join([self.service, self.version, self.id])
