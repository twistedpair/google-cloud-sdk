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


class ConflictingCollection(Error):
  """Raised when collection names conflict and need to be resolved."""


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

  def GetResourceCollections(self, custom_resources, api_version):
    """Returns all resources collections found in this discovery doc.

    Args:
      custom_resources: {str, str}, A mapping of collection name to path that
          have been registered manually in the yaml file.
      api_version: Override api_version for each found resource collection.

    Returns:
      list(resource_util.CollectionInfo).
    """
    collections = _ExtractResources(self.api_name, api_version, self.base_url,
                                    self._discovery_doc_dict['resources'])
    collections.extend(
        self._GenerateMissingParentCollections(
            collections, custom_resources, api_version))
    return collections

  def _GenerateMissingParentCollections(
      self, collections, custom_resources, api_version):
    """Generates parent collections for any existing collection missing one.

    Args:
      collections: [resource.CollectionInfo], The existing collections from
        the discovery doc.
      custom_resources: {str, str}, A mapping of collection name to path that
        have been registered manually in the yaml file.
      api_version: Override api_version for each found resource collection.

    Raises:
      ConflictingCollection: If multiple parent collections have the same name
        but different paths, and a custom resource has not been declared to
        resolve the conflict.

    Returns:
      [resource.CollectionInfo], Additional collections to include in the
      resource module.
    """
    all_names = {c.name: c for c in collections}
    all_paths = {c.GetPath(DEFAULT_PATH_NAME) for c in collections}
    generated = []
    in_progress = list(collections)
    to_process = []
    ignored = {}

    while in_progress:
      # We need to do multiple passes to recursively create all parent
      # collections of generated collections as well.
      for c in in_progress:
        parent_name, parent_path = _GetParentCollection(c)
        if not parent_name:
          continue  # No parent collection.
        if parent_path in all_paths:
          continue  # Parent path is already explicitly registered.
        if parent_name in custom_resources:
          # There is a manual entry to resolve this, don't add this collection.
          ignored.setdefault(parent_name, set()).add(parent_path)
          continue
        if parent_name in all_names:
          # Parent path is not registered, but a collection with the parent name
          # already exists. This conflict needs to be resolved manually.
          raise ConflictingCollection(
              'In API [{api}/{version}], the parent of collection [{c}] is not '
              'registered, but a collection with [{parent_name}] and path '
              '[{existing_path}] already exists. Update the api config file to '
              'manually add the parent collection with a path of '
              '[{parent_path}].'.format(
                  api=c.api_name, version=api_version, c=c.name,
                  parent_name=parent_name, existing_path=
                  all_names[parent_name].GetPath(DEFAULT_PATH_NAME),
                  parent_path=parent_path))
        parent_collection = self.MakeResourceCollection(
            parent_name, parent_path, api_version)
        to_process.append(parent_collection)
        all_names[parent_name] = parent_collection
        all_paths.add(parent_path)

      generated.extend(to_process)
      in_progress = to_process
      to_process = []

    # Print warnings if people have declared custom resources that are
    # unnecessary.
    for name, paths in ignored.iteritems():
      if len(paths) > 1:
        # There are multiple unique paths for this collection name. It is
        # required to be declared to disambiguate.
        continue
      path = paths.pop()
      if path == custom_resources[name]:
        # There is 1 path and it is the same as the custom one registered.
        print ('WARNING: Custom resource [{}] in API [{}/{}] is redundant.'
               .format(name, self.api_name, api_version))
    return generated

  def MakeResourceCollection(self, collection_name, path, api_version):
    return resource_util.CollectionInfo(
        self.api_name, api_version, self.base_url, collection_name, path,
        {}, resource_util.GetParamsFromPath(path))


def _GetParentCollection(collection_info):
  """Generates the name and path for a parent collection.

  Args:
    collection_info: resource.CollectionInfo, The collection to calculate the
      parent of.

  Returns:
    (str, str), A tuple of parent name and path or (None, None) if there is no
    parent.
  """
  params = collection_info.GetParams(DEFAULT_PATH_NAME)
  if len(params) < 2:
    # There is only 1 param, this is the top level.
    return None, None
  path = collection_info.GetPath(DEFAULT_PATH_NAME)
  # Chop off the last segment in the path.
  #   a/{a}/b/{b} --> a/{a}
  #   a/{a}/b --> a/{a}
  #   a/{a}/b/{b}/{c} --> a/{a}
  #   a/{a}/b/c/{b}/{c} --> a/{a}
  parts = path.split('/')
  while parts[-1].startswith('{') and parts[-1].endswith('}'):
    parts.pop()
  while not parts[-1].startswith('{') and not parts[-1].endswith('}'):
    parts.pop()
  parent_path = '/'.join(parts)

  if '.' in collection_info.name:
    # The discovery doc uses dotted paths for collections, chop off the last
    # segment and use that.
    parent_name, _ = collection_info.name.rsplit('.', 1)
  else:
    # The discovery doc uses short names for collections, use the name of the
    # last static part of the path.
    parent_name = parent_path.rsplit('/', 3)[-2]
  return parent_name, parent_path


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
