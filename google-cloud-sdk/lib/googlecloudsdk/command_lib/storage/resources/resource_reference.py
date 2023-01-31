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

import abc
import collections
import os

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage.resources import resource_util
from googlecloudsdk.core.util import debug_output

import six


NOT_SUPPORTED_DO_NOT_DISPLAY = '_NOT_SUPPORTED_DO_NOT_DISPLAY'


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
    # Includes generation ("gs://b/o#some-generation"). Warning: Terminal may
    # may think "#" is a comment and ignore it. Be careful using this like:
    # `self.Run('describe {}'.format(resource))`.
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

  Warning: After being run through through output formatter utils (e.g. in
  `shim_format_util.py`), these fields may all be strings.

  Attributes:
    TYPE_STRING (str): String representing the resource's content type.
    storage_url (StorageUrl): A StorageUrl object representing the bucket.
    name (str): Name of bucket.
    scheme (storage_url.ProviderPrefix): Prefix indicating what cloud provider
      hosts the bucket.
    acl (dict|CloudApiError|None): ACLs dict or predefined-ACL string for the
      bucket. If the API call to fetch the data failed, this can be an error
      string.
    cors_config (dict|CloudApiError|None): CORS configuration for the bucket.
      If the API call to fetch the data failed, this can be an error string.
    creation_time (datetime|None): Bucket's creation time in UTC.
    default_event_based_hold (bool|None): Prevents objects in bucket from being
      deleted. Currently GCS-only but needed for generic copy logic.
    default_storage_class (str|None): Default storage class for objects in
      bucket.
    etag (str|None): HTTP version identifier.
    labels (dict|None): Labels for the bucket.
    lifecycle_config (dict|CloudApiError|None): Lifecycle configuration for
      bucket. If the API call to fetch the data failed, this can be an error
      string.
    location (str|None): Represents region bucket was created in.
      If the API call to fetch the data failed, this can be an error string.
    logging_config (dict|CloudApiError|None): Logging configuration for bucket.
      If the API call to fetch the data failed, this can be an error string.
    metadata (object|dict|None): Cloud-provider specific data type for holding
      bucket metadata.
    metageneration (int|None): The generation of the bucket's metadata.
    requester_pays (bool|CloudApiError|None): "Requester pays" status of bucket.
      If the API call to fetch the data failed, this can be an error string.
    retention_period (int|None): Default time to hold items in bucket before
      before deleting in seconds. Generated from retention_policy.
    retention_policy (dict|None): Info about object retention within bucket.
    retention_policy_is_locked (bool|None): True if a retention policy is
      locked.
    update_time (str|None): Bucket's update time.
    versioning_enabled (bool|CloudApiError|None): Whether past object versions
      are saved. If the API call to fetch the data failed, this can be an error
      string.
    website_config (dict|CloudApiError|None): Website configuration for bucket.
      If the API call to fetch the data failed, this can be an error string.
  """
  TYPE_STRING = 'cloud_bucket'

  def __init__(self,
               storage_url_object,
               acl=None,
               cors_config=None,
               creation_time=None,
               default_event_based_hold=None,
               default_storage_class=None,
               etag=None,
               labels=None,
               lifecycle_config=None,
               location=None,
               logging_config=None,
               metageneration=None,
               metadata=None,
               requester_pays=None,
               retention_policy=None,
               update_time=None,
               versioning_enabled=None,
               website_config=None):
    """Initializes resource. Args are a subset of attributes."""
    super(BucketResource, self).__init__(storage_url_object)
    self.acl = acl
    self.cors_config = cors_config
    self.creation_time = creation_time
    self.default_event_based_hold = default_event_based_hold
    self.default_storage_class = default_storage_class
    self.etag = etag
    self.labels = labels
    self.lifecycle_config = lifecycle_config
    self.location = location
    self.logging_config = logging_config
    self.metadata = metadata
    self.metageneration = metageneration
    self.requester_pays = requester_pays
    self.retention_policy = retention_policy
    self.update_time = update_time
    self.versioning_enabled = versioning_enabled
    self.website_config = website_config

  @property
  def name(self):
    return self.storage_url.bucket_name

  @property
  def retention_period(self):
    # Provider-specific subclasses can override.
    return None

  @property
  def retention_policy_is_locked(self):
    # Provider-specific subclasses can override.
    return None

  def __eq__(self, other):
    return (super(BucketResource, self).__eq__(other) and
            self.acl == other.acl and self.cors_config == other.cors_config and
            self.creation_time == other.creation_time and
            self.default_event_based_hold == other.default_event_based_hold and
            self.default_storage_class == other.default_storage_class and
            self.etag == other.etag and self.location == other.location and
            self.labels == other.labels and
            self.lifecycle_config == other.lifecycle_config and
            self.location == other.location and
            self.logging_config == other.logging_config and
            self.metadata == other.metadata and
            self.metageneration == other.metageneration and
            self.requester_pays == other.requester_pays and
            self.retention_policy == other.retention_policy and
            self.update_time == other.update_time and
            self.versioning_enabled == other.versioning_enabled and
            self.website_config == other.website_config)

  def is_container(self):
    return True


class ObjectResource(CloudResource):
  """Class representing a cloud object confirmed to exist.

  Warning: After being run through through output formatter utils (e.g. in
  `shim_format_util.py`), these fields may all be strings.

  Attributes:
    TYPE_STRING (str): String representing the resource's type.
    storage_url (StorageUrl): A StorageUrl object representing the object.
    scheme (storage_url.ProviderPrefix): Prefix indicating what cloud provider
      hosts the object.
    bucket (str): Bucket that contains the object.
    name (str): Name of object.
    generation (str|None): Generation (or "version") of the underlying object.
    acl (dict|str|None): ACLs dict or predefined-ACL string for the objects.
      If the API call to fetch the data failed, this can be an error string.
    cache_control (str|None): Describes the object's cache settings.
    component_count (int|None): Number of components, if any.
    content_disposition (str|None): Whether the object should be displayed or
      downloaded.
    content_encoding (str|None): Encodings that have been applied to the object.
    content_language (str|None): Language used in the object's content.
    content_type (str|None): A MIME type describing the object's content.
    custom_time (str|None): A timestamp in RFC 3339 format specified by the
      user for an object. Currently, GCS-only, but not in provider-specific
      class because generic daisy chain logic uses the field.
    crc32c_hash (str|None): Base64-encoded digest of crc32c hash.
    creation_time (datetime|None): Time the object was created.
    custom_fields (dict|None): Custom key-value pairs set by users.
    decryption_key_hash_sha256 (str|None): Digest of a customer-supplied
      encryption key
    encryption_algorithm (str|None): Encryption algorithm used for encrypting
      the object if CSEK is used.
    etag (str|None): HTTP version identifier.
    event_based_hold (bool|None): Event based hold information for the object.
      Currently, GCS-only, but left generic because can affect copy logic.
    kms_key (str|None): Resource identifier of a Google-managed encryption key.
    md5_hash (str|None): Base64-encoded digest of md5 hash.
    metadata (object|dict|None): Cloud-specific metadata type.
    metageneration (int|None): Generation object's metadata.
    noncurrent_time (datetime|None): Noncurrent time value for the object.
    retention_expiration (datetime|None): Retention expiration information.
    size (int|None): Size of object in bytes (equivalent to content_length).
    storage_class (str|None): Storage class of the bucket.
    temporary_hold (bool|None): Temporary hold information for the object.
    update_time (datetime|None): Time the object was updated.
  """
  TYPE_STRING = 'cloud_object'

  def __init__(self,
               storage_url_object,
               acl=None,
               cache_control=None,
               component_count=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_type=None,
               crc32c_hash=None,
               creation_time=None,
               custom_fields=None,
               custom_time=None,
               decryption_key_hash_sha256=None,
               encryption_algorithm=None,
               etag=None,
               event_based_hold=None,
               kms_key=None,
               md5_hash=None,
               metadata=None,
               metageneration=None,
               noncurrent_time=None,
               retention_expiration=None,
               size=None,
               storage_class=None,
               temporary_hold=None,
               update_time=None):
    """Initializes resource. Args are a subset of attributes."""
    super(ObjectResource, self).__init__(storage_url_object)
    self.acl = acl
    self.cache_control = cache_control
    self.component_count = component_count
    self.content_disposition = content_disposition
    self.content_encoding = content_encoding
    self.content_language = content_language
    self.content_type = content_type
    self.crc32c_hash = crc32c_hash
    self.creation_time = creation_time
    self.custom_fields = custom_fields
    self.custom_time = custom_time
    self.decryption_key_hash_sha256 = decryption_key_hash_sha256
    self.encryption_algorithm = encryption_algorithm
    self.etag = etag
    self.event_based_hold = event_based_hold
    self.kms_key = kms_key
    self.md5_hash = md5_hash
    self.metageneration = metageneration
    self.metadata = metadata
    self.noncurrent_time = noncurrent_time
    self.retention_expiration = retention_expiration
    self.size = size
    self.storage_class = storage_class
    self.temporary_hold = temporary_hold
    self.update_time = update_time

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
    return (
        super(ObjectResource, self).__eq__(other) and self.acl == other.acl and
        self.cache_control == other.cache_control and
        self.component_count == other.component_count and
        self.content_disposition == other.content_disposition and
        self.content_encoding == other.content_encoding and
        self.content_language == other.content_language and
        self.content_type == other.content_type and
        self.crc32c_hash == other.crc32c_hash and
        self.creation_time == other.creation_time and
        self.custom_fields == other.custom_fields and
        self.custom_time == other.custom_time and
        self.decryption_key_hash_sha256 == other.decryption_key_hash_sha256 and
        self.encryption_algorithm == other.encryption_algorithm and
        self.etag == other.etag and
        self.event_based_hold == other.event_based_hold and
        self.kms_key == other.kms_key and self.md5_hash == other.md5_hash and
        self.metadata == other.metadata and
        self.metageneration == other.metageneration and
        self.noncurrent_time == other.noncurrent_time and
        self.retention_expiration == other.retention_expiration and
        self.size == other.size and
        self.storage_class == other.storage_class and
        self.temporary_hold == other.temporary_hold and
        self.update_time == other.update_time)

  def is_container(self):
    return False

  def is_encrypted(self):
    raise NotImplementedError

  def get_displayable_object_data(self):
    """To be overridden by child classes."""
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
    size (int|None): Size of local file in bytes or None if pipe or stream.
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

  @property
  def size(self):
    """Returns file size or None if pipe or stream."""
    if self.storage_url.is_stream:
      return None
    return os.path.getsize(self.storage_url.object_name)


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


class DisplayableResourceData(six.with_metaclass(abc.ABCMeta, object)):
  """Abstract class representing CloudResource for display purpose."""


class DisplayableBucketData(DisplayableResourceData):
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
    satisfies_pzs (bool|None): Zone Separation status.
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
               satisfies_pzs=None,
               storage_class=None,
               update_time=None,
               versioning_enabled=None,
               website_config=None):
    """Initializes DisplayableBucketData."""
    super(DisplayableBucketData, self).__init__()
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
    self.satisfies_pzs = satisfies_pzs
    self.storage_class = storage_class
    self.update_time = (
        resource_util.get_formatted_timestamp_in_utc(update_time)
        if update_time is not None else None)
    self.versioning_enabled = versioning_enabled
    self.website_config = website_config
    # This field is only required for ls -L command.
    # Private members are ignored by list/describe commands.
    self._bucket_policy_only_enabled = (
        bucket_policy_only.get('enabled')
        if bucket_policy_only is not None else None)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    # Using __dict__ should be safe because all the fields in this object
    # are comparable and we do not expect this object to be hashable.
    return self.__dict__ == other.__dict__

  def __repr__(self):
    return debug_output.generic_repr(self)


class DisplayableObjectData(DisplayableResourceData):
  """Class representing an ObjectResource for display purpose.

  All the public attributes in this object will be displayed by
  the list and describe commands. Objects get displayed recursively, e.g.
  if a field represents a datetime object, the display logic in gcloud will
  display each member of the datetime object as well. Hence, it is recommended
  to stringify any member before it gets sent to the gcloud's resource printers.

  Attributes:
    name (str): Name of object.
    bucket (str): Bucket that contains the object.
    url_string (str): The url string representing the object.
    acl (dict|str|None): ACLs for the objects.
      If the API call to fetch the data failed, this can be an error string.
    additional_properties (dict|list|None): Additional metadata.
    cache_control (str|None): Cache control value for the object.
    component_count (int|None): Number of components, if any.
    content_disposition (str|None): Content Disposition value for the object.
    content_encoding (str|None): Content Encoding value for the object.
    content_language (str|None): Content Language value for the object.
    content_length (int|None): Size of the object.
    content_type (str|None): Content Type of the object.
    crc32c_hash (str|None): Base64-encoded digest of crc32c hash.
    creation_time (str|None): Time the object was created.
    custom_time (str|None): Custom time, if present.
    encryption_algorithm (str|None): Encryption algorithm used for encrypting
      the object if CSEK is used.
    encryption_key_sha256 (str|None): The hash of a customer supplied
      encryption key.
    etag (str|None): HTTP version identifier.
    event_based_hold (bool|None): Event based hold information for the object.
    generation (str|None): Generation (or "version") of the underlying object.
    kms_key (str|None): The KMS key used to encrypt the object.
    md5_hash (str|None): Base64-encoded digest of md5 hash.
    metageneration (int|None): Generation object's metadata.
    noncurrent_time (str|None): Noncurrent time value for the object.
    retention_expiration (str|None): Retention expiration information.
    storage_class (str|None): The storage class for the object.
    storage_class_update_time (str|None): Storage class update time.
    temporary_hold (bool|None): Temporary hold information for the object.
    update_time (str|None): Time the object was updated.
  """

  def __init__(self,
               name,
               bucket,
               url_string,
               acl=None,
               additional_properties=None,
               cache_control=None,
               component_count=None,
               content_disposition=None,
               content_encoding=None,
               content_language=None,
               content_length=None,
               content_type=None,
               crc32c_hash=None,
               creation_time=None,
               custom_time=None,
               encryption_algorithm=None,
               encryption_key_sha256=None,
               etag=None,
               event_based_hold=None,
               generation=None,
               kms_key=None,
               md5_hash=None,
               metageneration=None,
               noncurrent_time=None,
               retention_expiration=None,
               storage_class=None,
               storage_class_update_time=None,
               temporary_hold=None,
               update_time=None):
    """Initializes DisplayableObjectData."""
    super(DisplayableObjectData, self).__init__()
    self.name = name
    self.bucket = bucket
    self.url_string = url_string
    self.acl = acl
    self.additional_properties = additional_properties
    self.cache_control = cache_control
    self.component_count = component_count
    self.content_disposition = content_disposition
    self.content_encoding = content_encoding
    self.content_language = content_language
    self.content_length = content_length
    self.content_type = content_type
    self.creation_time = (
        resource_util.get_formatted_timestamp_in_utc(creation_time)
        if creation_time is not None else None)
    self.custom_time = (
        resource_util.get_formatted_timestamp_in_utc(custom_time)
        if custom_time is not None else None)
    self.encryption_algorithm = encryption_algorithm
    self.encryption_key_sha256 = encryption_key_sha256
    self.etag = etag
    self.event_based_hold = event_based_hold
    self.generation = generation
    self.kms_key = kms_key
    self.md5_hash = md5_hash
    self.metageneration = metageneration
    self.noncurrent_time = (
        resource_util.get_formatted_timestamp_in_utc(noncurrent_time)
        if noncurrent_time is not None else None)
    self.retention_expiration = (
        resource_util.get_formatted_timestamp_in_utc(retention_expiration)
        if retention_expiration is not None else None)
    self.storage_class = storage_class
    self.storage_class_update_time = (
        resource_util.get_formatted_timestamp_in_utc(storage_class_update_time)
        if storage_class_update_time is not None else None)
    self.temporary_hold = temporary_hold
    self.update_time = (
        resource_util.get_formatted_timestamp_in_utc(update_time)
        if update_time is not None else None)
    self._crc32c_hash = crc32c_hash

  @property
  def crc32c_hash(self):
    """Returns the crc3c_hash value.

    If the value is NOT_SUPPORTED_DO_NOT_DISPLAY, we return None so that it gets
    ignored by commands like list/describe.
    """
    if self._crc32c_hash == NOT_SUPPORTED_DO_NOT_DISPLAY:
      return None
    return self._crc32c_hash

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    # Using __dict__ should be safe because all the fields in this object
    # are comparable and we do not expect this object to be hashable.
    return self.__dict__ == other.__dict__

  def __repr__(self):
    return debug_output.generic_repr(self)


def is_container_or_has_container_url(resource):
  """Returns if resource is a known or unverified container resource."""
  if isinstance(resource, UnknownResource):
    # May query for objects in bucket, skipping check if the bucket exists.
    return resource.storage_url.is_bucket()
  return resource.is_container()
