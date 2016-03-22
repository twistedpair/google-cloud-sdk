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

"""Resource property Get."""

import json


def _GetMetaDict(items, key, value):
  """Gets the dict in items that contains key==value.

  A metadict object is a list of dicts of the form:
    [
      {key: value-1, ...},
      {key: value-2, ...},
      ...
    ]

  Args:
    items: A list of dicts.
    key: The dict key name.
    value: The dict key value.

  Returns:
    The dict in items that contains key==value or None if no match.
  """
  try:
    for item in items:
      if item.get(key) == value:
        return item
  except (AttributeError, IndexError, TypeError, ValueError):
    pass
  return None


def _GetMetaDataValue(items, name, deserialize=False):
  """Gets the metadata value for the item in items with key == name.

  A metadata object is a list of dicts of the form:
    [
      {'key': key-name-1, 'value': field-1-value-string},
      {'key': key-name-2, 'value': field-2-value-string},
      ...
    ]

  Examples:
    x.metadata[windows-keys].email
      Deserializes the 'windows-keys' metadata value and gets the email value.
    x.metadata[windows-keys]
      Gets the 'windows-key' metadata string value.
    x.metadata[windows-keys][]
      Gets the deserialized 'windows-key' metadata value.

  Args:
    items: The metadata items list.
    name: The metadata name (which must match one of the 'key' values).
    deserialize: If True then attempt to deserialize a compact JSON string.

  Returns:
    The metadata value for name or None if not found or if items is not a
    metadata dict list.
  """
  item = _GetMetaDict(items, 'key', name)
  if item is None:
    return None
  value = item.get('value', None)
  if deserialize:
    try:
      return json.loads(value)
    except (TypeError, ValueError):
      pass
  return value


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
  meta = None
  for i, index in enumerate(key):
    # This if-ladder ordering checks builtin object attributes last. For
    # example, with resource = {'items': ...}, Get() treats 'items' as a dict
    # key rather than the builtin 'items' attribute of resource.

    if resource is None:
      # None is different than an empty dict or list.
      return default
    elif meta:
      resource = _GetMetaDict(resource, meta, index)
      meta = None
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
      elif 'items' in resource:
        # It would be nice if there were a better metadata indicator.
        # _GetMetaDataValue() returns None if resource['items'] isn't really
        # metadata, so there is a bit more verification than just 'items' in
        # resource.
        resource = _GetMetaDataValue(
            resource['items'], index, deserialize=i + 1 < len(key))
      else:
        return default

    elif isinstance(index, basestring) and hasattr(resource, index):
      # class-like
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
      elif not isinstance(index, (int, long)):
        if (isinstance(index, basestring) and
            isinstance(resource, list) and
            len(resource) and
            isinstance(resource[0], dict)):
          # Let the next iteration check for a meta dict.
          meta = index
          continue
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
