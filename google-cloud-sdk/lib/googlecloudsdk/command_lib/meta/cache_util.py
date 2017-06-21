# Copyright 2017 Google Inc. All Rights Reserved.
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

"""The meta cache command library support."""

from googlecloudsdk.core import exceptions
from googlecloudsdk.core.cache import exceptions as cache_exceptions
from googlecloudsdk.core.cache import file_cache
from googlecloudsdk.core.cache import resource_cache


_CACHE_RI_DEFAULT = 'resource://'


class Error(exceptions.Error):
  """Base cache exception."""


class NoTablesMatched(Error):
  """No table names matched the patterns."""


def GetCache(name, create=False):
  """Returns the cache given a cache indentfier name.

  Args:
    name: The cache name to operate on. May be prefixed by "resource://" for
      resource cache names or "file://" for persistent file cache names. If
      only the prefix is specified then the default cache name for that prefix
      is used.
    create: Creates the persistent cache if it exists if True.

  Raises:
    CacheNotFound: If the cache does not exist.

  Returns:
    The cache object.
  """

  types = {
      'file': file_cache.Cache,
      'resource': resource_cache.ResourceCache,
  }

  def _OpenCache(cache_class, name):
    try:
      return cache_class(name, create=create)
    except cache_exceptions.Error as e:
      raise Error(e)

  if name:
    for cache_id, cache_class in types.iteritems():
      if name.startswith(cache_id + '://'):
        name = name[len(cache_id) + 3:]
        if not name:
          name = None
        return _OpenCache(cache_class, name)
  return _OpenCache(resource_cache.Cache, name)


def AddCacheFlag(parser):
  """Adds the persistent cache flag to the parser."""
  parser.add_argument(
      '--cache',
      metavar='CACHE_NAME',
      default='resource://',
      help=('The cache name to operate on. May be prefixed by '
            '"resource://" for resource cache names. If only the prefix is '
            'specified then the default cache name for that prefix is used.'))
