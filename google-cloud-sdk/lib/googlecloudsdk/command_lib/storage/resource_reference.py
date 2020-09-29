# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Classes for cloud/file references yielded by storage iterators."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import cloud_api


class Resource(object):
  """Base class for a reference to one fully expanded iterator result.

  This allows polymorphic iteration over wildcard-iterated URLs.  The
  reference contains a fully expanded URL string containing no wildcards and
  referring to exactly one entity (if a wildcard is contained, it is assumed
  this is part of the raw string and should never be treated as a wildcard).

  Each reference represents a Bucket, Object, or Prefix.  For filesystem URLs,
  Objects represent files and Prefixes represent directories.

  The metadata_object member contains the underlying object as it was retrieved.
  It is populated by the calling iterator, which may only request certain
  fields to reduce the number of server requests.

  For filesystem and prefix URLs, metadata_object is not populated.

  Attributes:
    storage_url (StorageUrl): A StorageUrl object representing the resource
  """

  def __init__(self, storage_url):
    """Initialize the Resource object.

    Args:
      storage_url (StorageUrl): A StorageUrl object representing the resource.
    """
    self.storage_url = storage_url

  def __str__(self):
    return self.storage_url.url_string

  def __eq__(self, other):
    return (
        isinstance(other, self.__class__) and
        self.storage_url == other.storage_url
    )

  def is_container(self):
    raise NotImplementedError('is_container must be overridden.')


class CloudResource(Resource):
  """For Resource classes with CloudUrl's.

  Attributes:
    scheme (cloud_api.ProviderPrefix): Prefix indicating what cloud provider
        hosts the bucket.
  """

  @property
  def scheme(self):
    # TODO(b/168690302): Stop using string scheme in storage_url.py.
    return cloud_api.ProviderPrefix(self.storage_url.scheme)


class BucketResource(CloudResource):
  """Class representing a bucket.

  Attributes:
    storage_url (StorageUrl): A StorageUrl object representing the bucket.
    name (str): Name of bucket.
    scheme (cloud_api.ProviderPrefix): Prefix indicating what cloud provider
        hosts the bucket.
    etag (str): HTTP version identifier.
    metadata (object | dict): Cloud-provider specific data type for holding
        bucket metadata.
  """

  def __init__(self, storage_url, etag=None, metadata=None):
    """Initializes resource. Args are a subset of attributes."""
    super(BucketResource, self).__init__(storage_url)
    self.etag = etag
    self.metadata = metadata

  @property
  def name(self):
    return self.storage_url.bucket_name

  def __eq__(self, other):
    return (
        super(BucketResource, self).__eq__(other) and
        self.etag == other.etag and
        self.metadata == other.metadata
    )

  def is_container(self):
    return True


class ObjectResource(Resource):
  """Class representing a  cloud object.

  Attributes:
    storage_url (StorageUrl): A StorageUrl object representing the object.
    creation_time (datetime|None): Time the object was created.
    scheme (cloud_api.ProviderPrefix): Prefix indicating what cloud provider
        hosts the object.
    name (str): Name of object.
    etag (str|None): HTTP version identifier.
    generation (str|None): Generation (or "version") of the underlying object.
    metageneration (int|None): Generation object's metadata.
    metadata (object|dict|None): Cloud-specific metadata type.
    size (int|None): Size of object in bytes.
  """

  def __init__(self, storage_url, creation_time=None, etag=None, metadata=None,
               metageneration=None, size=None):
    """Initializes resource. Args are a subset of attributes."""
    super(ObjectResource, self).__init__(storage_url)
    self.creation_time = creation_time
    self.etag = etag
    self.metageneration = metageneration
    self.metadata = metadata
    self.size = size

  @property
  def name(self):
    return self.storage_url.object_name

  @property
  def generation(self):
    return self.storage_url.generation

  def __eq__(self, other):
    return (
        super().__eq__(other) and
        self.etag == other.etag and
        self.generation == other.generation and
        self.metadata == other.metadata
    )

  def is_container(self):
    return False


class PrefixResource(Resource):
  """Class representing a  cloud object.

  Attributes:
    storage_url (StorageUrl): A StorageUrl object representing the prefix
    prefix (str): A string representing the prefix.
  """

  def __init__(self, storage_url, prefix):
    """Initialize the PrefixResource object.

    Args:
      storage_url (StorageUrl): A StorageUrl object representing the prefix
      prefix (str): A string representing the prefix.
    """
    super(PrefixResource, self).__init__(storage_url)
    self.prefix = prefix

  def is_container(self):
    return True


class FileObjectResource(Resource):
  """Wrapper for a filesystem file."""

  def is_container(self):
    return False


class FileDirectoryResource(Resource):
  """Wrapper for a File system directory."""

  def is_container(self):
    return True


class UnknownResource(Resource):
  """Represents a resource that may or may not exist."""
