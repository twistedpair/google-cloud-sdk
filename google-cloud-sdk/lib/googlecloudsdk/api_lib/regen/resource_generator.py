# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Resource definition generator."""

import json
import re

from googlecloudsdk.api_lib.util import resource as resource_util


_COLLECTION_SUB_RE = r'[a-zA-Z_]+(?:\.[a-zA-Z0-9_]+)+'
_METHOD_ID_RE = re.compile(r'(?P<collection>{collection})\.get'.format(
    collection=_COLLECTION_SUB_RE))
DEFAULT_PATH_NAME = ''


class Error(Exception):
  """Errors raised by this module."""


class UnsupportedDiscoveryDoc(Error):
  """Raised when some unsupported feature is detected."""


class DiscoveryDoc(object):
  """Encapsulates access to discovery doc."""

  def __init__(self, discovery_doc_dict):
    self._discovery_doc_dict = discovery_doc_dict

  @classmethod
  def FromJson(cls, path):
    with open(path, 'rU') as f:
      return cls(json.load(f))

  @property
  def api_name(self):
    return self._discovery_doc_dict['name']

  @property
  def api_version(self):
    return self._discovery_doc_dict['version']

  @property
  def base_url(self):
    return self._discovery_doc_dict['baseUrl']

  def GetResourceCollections(self, api_version=None):
    """Returns all resources collections found in this discovery doc.

    Args:
      api_version: Override api_version for each found resource collection.
    Returns:
      list(resource_util.CollectionInfo).
    """
    api_version = api_version or self.api_verison
    return _ExtractResources(self.api_name, api_version, self.base_url,
                             self._discovery_doc_dict['resources'])

  def MakeResourceCollection(self, collection_name, path, api_version=None):
    api_version = api_version or self.api_verison
    return resource_util.CollectionInfo(
        self.api_name, api_version, self.base_url, collection_name, path,
        {}, resource_util.GetParamsFromPath(path))


def _ExtractResources(api_name, api_version, base_url, infos):
  """Extract resource definitions from discovery doc."""
  collections = []
  for name, info in infos.iteritems():
    if name == 'methods':
      get_method = info.get('get')
      if get_method:
        collection_info = _GetCollectionFromMethod(
            base_url, api_name, api_version, get_method)
        collections.append(collection_info)
    else:
      subresource_collections = _ExtractResources(
          api_name, api_version, base_url, info)
      collections.extend(subresource_collections)
  return collections


def _GetCollectionFromMethod(base_url, api_name, api_version, get_method):
  """Created collection_info object given discovery doc get_method."""
  method_id = get_method['id']
  match = _METHOD_ID_RE.match(method_id)
  if match:
    collection_name = match.group('collection')
    # Remove api name from collection. It might not match passed in, or
    # even api name in url. We choose to use api name as defined by url.
    collection_name = collection_name.split('.', 1)[1]
    flat_path = get_method.get('flatPath')
    path = get_method.get('path')
    return _MakeResourceCollection(base_url, api_name, api_version,
                                   collection_name, path, flat_path)


def _MakeResourceCollection(base_url, api_name, api_version,
                            collection_name, path, flat_path=None):
  """Make resource collection object given its name and path."""
  if flat_path == path:
    flat_path = None
  # Normalize base url so it includes api_version.
  url = base_url + path
  url_api_name, url_api_vesion, path = (
      resource_util.SplitDefaultEndpointUrl(url))
  if url_api_vesion != api_version:
    raise UnsupportedDiscoveryDoc(
        'Collection {0} for version {1}/{2} is using url {3} '
        'with version {4}'.format(
            collection_name, api_name, api_version, url, url_api_vesion))
  if flat_path:
    _, _, flat_path = resource_util.SplitDefaultEndpointUrl(
        base_url + flat_path)
  # Use url_api_name instead as it is assumed to be source of truth.
  # Also note that api_version not always equal to url_api_version,
  # this is the case where api_version is an alias.
  url = url[:-len(path)]
  return resource_util.CollectionInfo(
      url_api_name, api_version, url, collection_name, path,
      {DEFAULT_PATH_NAME: flat_path} if flat_path else {},
      resource_util.GetParamsFromPath(path))
