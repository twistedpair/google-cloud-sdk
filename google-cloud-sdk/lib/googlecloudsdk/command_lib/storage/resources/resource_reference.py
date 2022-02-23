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

import collections

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.resources import resource_util


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
    TYPE_STRING (str): String representing the resource's content type.
    storage_url (StorageUrl): A StorageUrl object representing the resource.
  """
  TYPE_STRING = 'resource'

  def __init__(self, storage_url_object):
    """Initialize the Resource object.

    Args:
      storage_url_object (StorageUrl): A StorageUrl object representing the
          resource.
    """
    self.storage_url = storage_url_object

  def get_json_dump(self):
    """Formats resource for printing as JSON."""
    return resource_util.configured_json_dumps(
        collections.OrderedDict([
            ('url', self.storage_url.url_string),
            ('type', self.TYPE_STRING),
        ]))

  def __repr__(self):
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
    TYPE_STRING (str): String representing the resource's content type.
    scheme (storage_url.ProviderPrefix): Prefix indicating what cloud provider
        hosts the bucket.
    storage_url (StorageUrl): A StorageUrl object representing the resource.
  """
  TYPE_STRING = 'cloud_resource'

  @property
  def scheme(self):
    # TODO(b/168690302): Stop using string scheme in storage_url.py.
    return self.storage_url.scheme


class BucketResource(CloudResource):
  """Class representing a bucket.

  Attributes:
    TYPE_STRING (str): String representing the resource's content type.
    storage_url (StorageUrl): A StorageUrl object representing the bucket.
    name (str): Name of bucket.
    scheme (storage_url.ProviderPrefix): Prefix indicating what cloud provider
      hosts the bucket.
    etag (str|None): HTTP version identifier.
    location (str|None): Represents region bucket was created in.
    metadata (object|dict|None): Cloud-provider specific data type for holding
      bucket metadata.
    retention_period (int|None): Default time to hold items in bucket before
      before deleting in seconds.
    default_storage_class (str|None): Default storage class for objects in
      bucket.
    uniform_bucket_level_access (bool): True if all objects in the bucket share
      ACLs rather than the default, fine-grain ACL control.
  """
  TYPE_STRING = 'cloud_bucket'

  def __init__(self,
               storage_url_object,
               etag=None,
               location=None,
               metadata=None,
               retention_period=None,
               default_storage_class=None,
               uniform_bucket_level_access=False):
    """Initializes resource. Args are a subset of attributes."""
    super(BucketResource, self).__init__(storage_url_object)
    self.etag = etag
    self.location = location
    self.metadata = metadata
    self.retention_period = retention_period
    self.default_storage_class = default_storage_class
    self.uniform_bucket_level_access = uniform_bucket_level_access

  @property
  def name(self):
    return self.storage_url.bucket_name

  def __eq__(self, other):
    return (super(BucketResource, self).__eq__(other) and
            self.etag == other.etag and self.location == other.location and
            self.metadata == other.metadata and
            self.retention_period == other.retention_period and
            self.default_storage_class == other.default_storage_class and
            self.uniform_bucket_level_access
            == other.uniform_bucket_level_access)

  def is_container(self):
    return True


class ObjectResource(CloudResource):
  """Class representing a cloud object confirmed to exist.

  Attributes:
    TYPE_STRING (str): String representing the resource's type.
    storage_url (StorageUrl): A StorageUrl object representing the object.
    content_type (str|None): A MIME type describing the object's content.
    creation_time (datetime|None): Time the object was created.
    decryption_key_hash (str): The hash of a customer supplied encryption key.
    etag (str|None): HTTP version identifier.
    crc32c_hash (str|None): Base64-encoded digest of crc32c hash.
    md5_hash (str|None): Base64-encoded digest of md5 hash.
    metageneration (int|None): Generation object's metadata.
    metadata (object|dict|None): Cloud-specific metadata type.
    size (int|None): Size of object in bytes.
    scheme (storage_url.ProviderPrefix): Prefix indicating what cloud provider
        hosts the object.
    bucket (str): Bucket that contains the object.
    name (str): Name of object.
    generation (str|None): Generation (or "version") of the underlying object.
  """
  TYPE_STRING = 'cloud_object'

  def __init__(self,
               storage_url_object,
               content_type=None,
               creation_time=None,
               decryption_key_hash=None,
               etag=None,
               crc32c_hash=None,
               md5_hash=None,
               metadata=None,
               metageneration=None,
               size=None):
    """Initializes resource. Args are a subset of attributes."""
    super(ObjectResource, self).__init__(storage_url_object)
    self.content_type = content_type
    self.creation_time = creation_time
    self.decryption_key_hash = decryption_key_hash
    self.etag = etag
    self.crc32c_hash = crc32c_hash
    self.md5_hash = md5_hash
    self.metageneration = metageneration
    self.metadata = metadata
    self.size = size

  @property
  def bucket(self):
    return self.storage_url.bucket_name

  @property
  def name(self):
    return self.storage_url.object_name

  @property
  def generation(self):
    return self.storage_url.generation

  def __eq__(self, other):
    return (super(ObjectResource, self).__eq__(other) and
            self.content_type == other.content_type and
            self.decryption_key_hash == other.decryption_key_hash and
            self.etag == other.etag and self.generation == other.generation and
            self.crc32c_hash == other.crc32c_hash and
            self.md5_hash == other.md5_hash and self.metadata == other.metadata)

  def is_container(self):
    return False

  def is_encrypted(self):
    raise NotImplementedError


class PrefixResource(Resource):
  """Class representing a  cloud object.

  Attributes:
    TYPE_STRING (str): String representing the resource's content type.
    storage_url (StorageUrl): A StorageUrl object representing the prefix.
    prefix (str): A string representing the prefix.
  """
  TYPE_STRING = 'prefix'

  def __init__(self, storage_url_object, prefix):
    """Initialize the PrefixResource object.

    Args:
      storage_url_object (StorageUrl): A StorageUrl object representing the
          prefix.
      prefix (str): A string representing the prefix.
    """
    super(PrefixResource, self).__init__(storage_url_object)
    self.prefix = prefix

  def is_container(self):
    return True


class FileObjectResource(Resource):
  """Wrapper for a filesystem file.

  Attributes:
    TYPE_STRING (str): String representing the resource's content type.
    storage_url (StorageUrl): A StorageUrl object representing the resource.
    md5_hash (bytes): Base64-encoded digest of md5 hash.
  """
  TYPE_STRING = 'file_object'

  def __init__(self, storage_url_object, md5_hash=None):
    """Initializes resource. Args are a subset of attributes."""
    super(FileObjectResource, self).__init__(storage_url_object)
    self.md5_hash = md5_hash

  def is_container(self):
    return False


class FileDirectoryResource(Resource):
  """Wrapper for a File system directory."""
  TYPE_STRING = 'file_directory'

  def is_container(self):
    return True


class UnknownResource(Resource):
  """Represents a resource that may or may not exist."""
  TYPE_STRING = 'unknown'

  def is_container(self):
    raise errors.ValueCannotBeDeterminedError(
        'Unknown whether or not UnknownResource is a container.')


class DisplayableBucketData(object):
  """Class representing a BucketResource for display purpose.

  All the public attributes in this object will be displayed by
  the list and describe commands. Objects get displayed recursively, e.g.
  if a field represents a datetime object, the display logic in gcloud will
  display each member of the datetime object as well. Hence, it is recommended
  to stringify any member before it gets sent to the gcloud's resource printers.

  Attributes:
    name (str): Name of bucket.
    url_string (str): The url string representing the bucket.
    acl (dict|str|None): ACLs for the bucket.
      If the API call to fetch the data failed, this can be an error string.
    bucket_policy_only (dict|None): Bucket policy only settings.
    cors_config (dict|str|None): The CORS configuration for the bucket.
      If the API call to fetch the data failed, this can be an error string.
    creation_time (str|None): Bucket's creation time.
    default_acl (dict|None): Default ACLs for the bucket.
    default_event_based_hold (bool|None): Default Event Based Hold status.
    default_kms_key (str|None): The default KMS key for the bucket.
    encryption_config (dict|str|None): The encryption configuration of the
      bucket. Applies to S3 buckets only.
    etag (str|None): ETag for the bucket.
    labels (dict|None): Labels for the bucket.
    lifecycle_config (dict|str|None): The lifecycle configuration for the
      bucket. For S3, the value can be an error string.
    location (str|None): Represents region bucket was created in.
    location_type (str|None): Location type of the bucket.
    logging_config (dict|str|None): The logging configuration for the bucket.
      If the API call to fetch the data failed, this can be an error string.
    metageneration (int|None): Bucket's metageneration.
    project_number (int|None): The project number to which the bucket belongs.
    public_access_prevention (str|None): Public access prevention status.
    requester_pays (bool|str|None): The "requester pays" status of the bucket.
      For S3, the value can be an error string.
    retention_policy (dict|None): Default time to hold items in bucket in
      seconds.
    rpo (str|None): Recovery Point Objective status.
    satisifes_pzs (bool|None): Zone Separation status.
    storage_class (str|None): Storage class of the bucket.
    update_time (str|None): Bucket's update time.
    versioning_enabled (bool|str|None): If True, versioning is enabled.
      If the API call to fetch the data failed, this can be an error string.
    website_config (dict|str|None): The website configuration for the bucket.
      If the API call to fetch the data failed, this can be an error string.
  """

  def __init__(self,
               name,
               url_string,
               acl=None,
               bucket_policy_only=None,
               cors_config=None,
               creation_time=None,
               default_acl=None,
               default_event_based_hold=None,
               default_kms_key=None,
               encryption_config=None,
               etag=None,
               labels=None,
               lifecycle_config=None,
               location=None,
               location_type=None,
               logging_config=None,
               metageneration=None,
               project_number=None,
               public_access_prevention=None,
               requester_pays=None,
               retention_policy=None,
               rpo=None,
               satisifes_pzs=None,
               storage_class=None,
               update_time=None,
               versioning_enabled=None,
               website_config=None):
    """Initializes DisplayableBucketData."""
    self.name = name
    self.url_string = url_string
    self.acl = acl
    self.bucket_policy_only = bucket_policy_only
    self.cors_config = cors_config
    self.creation_time = (
        resource_util.get_formatted_timestamp_in_utc(creation_time)
        if creation_time is not None else None)
    self.default_acl = default_acl
    self.default_event_based_hold = default_event_based_hold
    self.default_kms_key = default_kms_key
    self.encryption_config = encryption_config
    self.etag = etag
    self.labels = labels
    self.lifecycle_config = lifecycle_config
    self.location = location
    self.location_type = location_type
    self.logging_config = logging_config
    self.metageneration = metageneration
    self.project_number = project_number
    self.public_access_prevention = public_access_prevention
    self.requester_pays = requester_pays
    self.retention_policy = retention_policy
    self.rpo = rpo
    self.satisifes_pzs = satisifes_pzs
    self.storage_class = storage_class
    self.update_time = (
        resource_util.get_formatted_timestamp_in_utc(update_time)
        if update_time is not None else None)
    self.versioning_enabled = versioning_enabled
    self.website_config = website_config

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    # Using __dict__ should be safe because all the fields in this object
    # are comparable and we do not expect this object to be hashable.
    return self.__dict__ == other.__dict__
