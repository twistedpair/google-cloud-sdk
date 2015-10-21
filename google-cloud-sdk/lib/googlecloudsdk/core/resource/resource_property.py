# Copyright 2015 Google Inc. All Rights Reserved.

"""Resource property Get."""


def _GetMetaData(resource, name, value, default=None):
  """Gets the metadata dict in resource that contains {name: value, ...}.

  A metadata object is a list of dicts of the form:
    [
      {'name': key-name-1, 'field_1': field-1-value-2, ...},
      {'name': key-name-2, 'field_1': field-1-value-2, ...},
      ...
    ]
  Get() on key 'name.foo.field_1' calls _GetMetaData(resource, 'name', 'foo')
  to find the dict in resource with 'name'=='foo' and then looks up 'field_1' in
  that dict.

  Args:
    resource: The metadata resource object.
    name: The metadata key field name.
    value: The metadata key field value.
    default: This value returned if not found or resource is not metadata.

  Returns:
    The metadata dict containing {name: value, ...} or default if not found or
    if resource is not a metadata object.
  """
  try:
    for item in resource:
      if item.get(name) == value:
        return item
  except (IndexError, TypeError):
    pass
  return default


def Get(resource, key, default=None):
  """Gets the value referenced by key in the object resource.

  Since it is common for resource instances to be sparse it is not an error if
  a key is not present in a particular resource instance, or if an index does
  not match the resource type.

  Args:
    resource: The resource object possibly containing a value for key.
    key: Ordered list of key names/indices, applied left to right. Each
      element in the list may be one of:
        str - A resource property name. This could be a class attribute name or
          a dict index.
        int - A list index. Selects one member is the list. Negative indices
          count from the end of the list, starting with -1 for the last element
          in the list. An out of bounds index is not an error; it produces the
          value None.
        None - A list slice. Selects all members of a list or dict like object.
          A slice of an empty dict or list is an empty dict or list.
    default: Get() returns this value if key is not in resource.

  Returns:
    The value, None if any of the given keys are not found. This is
      intentionally not an error. In this context a value can be any data
      object: dict, list, tuple, class, str, int, float, ...
  """
  if isinstance(resource, set):
    resource = sorted(resource)
  metadata = None
  for i, index in enumerate(key):

    # This if-ladder ordering checks builtin object attributes last. For
    # example, with resource = {'items': ...}, Get() treats 'items' as a dict
    # key rather than the builtin 'items' attribute of resource.

    if metadata:
      # MetaData-like
      resource = _GetMetaData(resource, metadata, index)
      metadata = None

    elif resource is None:
      # None is different than an empty dict or list.
      return default

    elif hasattr(resource, 'iteritems'):
      # dict-like
      if index is None:
        if i + 1 < len(key):
          # Inner slice: *.[].*
          return [Get(resource, [k] + key[i + 1:], default) for k in resource]
        else:
          # Trailing slice: *.[]
          return resource
      elif index in resource:
        resource = resource[index]
      else:
        return default

    elif isinstance(index, basestring) and hasattr(resource, index):
      # class-like -- done here to catch metadata
      resource = getattr(resource, index, default)

    elif hasattr(resource, '__iter__') or isinstance(resource, basestring):
      # list-like
      if index is None:
        if i + 1 < len(key):
          # Inner slice: *.[].*
          return [Get(resource, [k] + key[i + 1:], default)
                  for k in range(len(resource))]
        else:
          # Trailing slice: *.[]
          return resource
      elif isinstance(index, basestring):
        # Try _GetMetaData() index lookup on the next iteration.
        metadata = index
      elif not isinstance(index, (int, long)):
        # Index mismatch.
        return default
      elif index in xrange(-len(resource), len(resource)):
        resource = resource[index]
      else:
        return default

    else:
      # Resource or index mismatch.
      return default

    if isinstance(resource, set):
      resource = sorted(resource)

  if metadata:
    return default

  return resource


def IsListLike(resource):
  """Checks if resource is a list-like iterable object.

  Args:
    resource: The object to check.

  Returns:
    True if resource is a list-like iterable object.
  """
  return (isinstance(resource, list) or
          hasattr(resource, '__iter__') and hasattr(resource, 'next'))
