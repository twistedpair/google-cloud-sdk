# Copyright 2015 Google Inc. All Rights Reserved.
"""Utilities for manipulating GCE instances running an App Engine project."""

from googlecloudsdk.core import exceptions


class InvalidInstanceSpecificationError(exceptions.Error):
  pass


def _GetInstanceMetadata(instance):
  items = instance['metadata'].get('items', [])
  return dict([(item['key'], item['value']) for item in items])


class AppEngineInstance(object):
  """Value class for instances running the current App Engine project."""

  _NUM_PATH_PARTS = 3

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

    A resource path is of the form '<service>/<version>/<instance>'.
    '<service>' and '<version>' can be omitted, in which case they are None in
    the resulting instance.

    >>> (AppEngineInstance.FromResourcePath('a/b/c') ==
         ...  AppEngineInstance('a', 'b', 'c'))
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
      InvalidInstanceSpecificationError: if the instance is over- or
        under-specified
    """
    parts = path.split('/')
    if len(parts) == 1:
      path_service, path_version, instance = None, None, parts[0]
    elif len(parts) == 2:
      path_service, path_version, instance = None, parts[0], parts[1]
    elif len(parts) == 3:
      path_service, path_version, instance = parts
    else:
      raise InvalidInstanceSpecificationError(
          'Instance resource path is incorrectly specified. '
          'Please provide at most one service, version, and instance id, '
          '.\n\n'
          'You provided:\n' + path)

    if path_service and service and path_service != service:
      raise InvalidInstanceSpecificationError(
          'Service [{0}] is inconsistent with specified instance [{1}].'.format(
              service, path))
    service = service or path_service

    if path_version and version and path_version != version:
      raise InvalidInstanceSpecificationError(
          'Version [{0}] is inconsistent with specified instance [{1}].'.format(
              version, path))
    version = version or path_version

    return cls(service, version, instance)

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

  def __str__(self):
    return '/'.join(filter(bool, [self.service, self.version, self.id]))


def FilterInstances(instances, service=None, version=None, instance_path=None):
  """Filter a list of App Engine instances.

  Args:
    instances: list of AppEngineInstance, all App Engine instances
    service: str, the name of the service to filter by or None to match all
      services
    version: str, the name of the version to filter by or None to match all
      versions
    instance_path: str, the name of the instance to filter by or None to match
      all versions. Can be a resource path, in which case it is parsed and the
      components used to filter.

  Returns:
    list of instances matching the given filters

  Raises:
    InvalidInstanceSpecificationError: if an inconsistent instance specification
      was given (ex. service='service1' and instance='service2/v1/abcd').
  """
  if instance_path and '/' in instance_path:
    parsed_instance = AppEngineInstance.FromResourcePath(instance_path,
                                                         service=service,
                                                         version=version)
    if (parsed_instance.service and service and
        parsed_instance.service != service):
      raise InvalidInstanceSpecificationError(
          'Service [{0}] is inconsistent with specified instance '
          '[{1}].'.format(service, instance_path))
    if (parsed_instance.version and version and
        parsed_instance.version != version):
      raise InvalidInstanceSpecificationError(
          'Version [{0}] is inconsistent with specified instance '
          '[{1}].'.format(version, instance_path))
    service = service or parsed_instance.service
    version = version or parsed_instance.version
    instance_id = parsed_instance.id
  else:
    instance_id = instance_path
  matching_instances = []
  for provided_instance in instances:
    if ((not service or provided_instance.service == service) and
        (not version or provided_instance.version == version) and
        (not instance_id or provided_instance.id == instance_id)):
      matching_instances.append(provided_instance)
  return matching_instances
