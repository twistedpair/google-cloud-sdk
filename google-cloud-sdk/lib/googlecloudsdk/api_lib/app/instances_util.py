# Copyright 2015 Google Inc. All Rights Reserved.
"""Utilities for manipulating GCE instances running an App Engine project."""


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
