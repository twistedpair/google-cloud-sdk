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

"""Utilities for expanding wildcarded GCS pathnames."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import collections
import fnmatch
import glob
import itertools
import os
import re

from googlecloudsdk.api_lib.storage import api_factory
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors as api_errors
from googlecloudsdk.api_lib.storage import request_config_factory
from googlecloudsdk.command_lib.storage import errors as command_errors
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core import log
from googlecloudsdk.core.util import debug_output

import six


COMPRESS_WILDCARDS_REGEX = re.compile(r'\*{3,}')
WILDCARD_REGEX = re.compile(r'[*?\[\]]')


def contains_wildcard(url_string):
  """Checks whether url_string contains a wildcard.

  Args:
    url_string: URL string to check.

  Returns:
    bool indicator.
  """
  return bool(WILDCARD_REGEX.search(url_string))


def get_wildcard_iterator(url_str,
                          all_versions=False,
                          error_on_missing_key=True,
                          fetch_encrypted_object_hashes=False,
                          fields_scope=cloud_api.FieldsScope.NO_ACL,
                          get_bucket_metadata=False,
                          ignore_symlinks=False):
  """Instantiate a WildcardIterator for the given URL string.

  Args:
    url_str (str): URL string which may contain wildcard characters.
    all_versions (bool): If true, the iterator yields all versions of objects
        matching the wildcard.  If false, yields just the live object version.
    error_on_missing_key (bool): If true, and the encryption key needed to
        decrypt an object is missing, the iterator raises an error for that
        object.
    fetch_encrypted_object_hashes (bool): Fall back to GET requests for
        encrypted cloud objects in order to fetch their hash values.
    fields_scope (cloud_api.FieldsScope): Determines amount of metadata
        returned by API.
    get_bucket_metadata (bool): If true, perform a bucket GET request when
        fetching bucket resources
    ignore_symlinks (bool): Skip over symlinks instead of following them.

  Returns:
    A WildcardIterator object.
  """
  url = storage_url.storage_url_from_string(url_str)
  if isinstance(url, storage_url.CloudUrl):
    return CloudWildcardIterator(
        url,
        all_versions=all_versions,
        error_on_missing_key=error_on_missing_key,
        fetch_encrypted_object_hashes=fetch_encrypted_object_hashes,
        fields_scope=fields_scope,
        get_bucket_metadata=get_bucket_metadata)
  elif isinstance(url, storage_url.FileUrl):
    return FileWildcardIterator(url, ignore_symlinks=ignore_symlinks)
  else:
    raise command_errors.InvalidUrlError('Unknown url type %s.' % url)


def _compress_url_wildcards(url):
  """Asterisk counts greater than two treated as single * to mimic globs.

  Args:
    url (StorageUrl): Url to compress wildcards in.

  Returns:
    StorageUrl built from string with compressed wildcards.
  """
  compressed_url_string = re.sub(COMPRESS_WILDCARDS_REGEX, '*',
                                 url.versionless_url_string)
  if url.generation is not None:
    compressed_url_string += '#' + url.generation
  return storage_url.storage_url_from_string(compressed_url_string)


class WildcardIterator(six.with_metaclass(abc.ABCMeta)):
  """Class for iterating over Google Cloud Storage strings containing wildcards.

  The base class is abstract; you should instantiate using the
  wildcard_iterator() static factory method, which chooses the right
  implementation depending on the base string.
  """
  _url = None

  def __repr__(self):
    """Returns string representation of WildcardIterator."""
    return 'WildcardIterator(%s)' % getattr(self._url, 'url_string', None)


class FileWildcardIterator(WildcardIterator):
  """Class to iterate over files and directories."""

  def __init__(self, url, ignore_symlinks=False):
    """Initialize FileWildcardIterator instance.

    Args:
      url (FileUrl): A FileUrl instance representing a file path.
      ignore_symlinks (bool): Skip over symlinks instead of following them.
    """
    super(FileWildcardIterator, self).__init__()
    self._url = _compress_url_wildcards(url)
    self._path = self._url.object_name
    self._ignore_symlinks = ignore_symlinks

  def __iter__(self):
    # Files named '-' will not be copied, as that string makes is_stdio true.
    if self._url.is_stdio:
      yield resource_reference.FileObjectResource(self._url)

    recursion_needed = '**' in self._path
    normal_file_iterator = glob.iglob(self._path, recursive=recursion_needed)
    if recursion_needed:
      hidden_file_iterator = glob.iglob(
          os.path.join(self._path, '**', '.*'), recursive=recursion_needed)
    else:
      hidden_file_iterator = []
    for path in itertools.chain(normal_file_iterator, hidden_file_iterator):
      # Follow symlinks unless pointing to directory or exclude flag is present.
      if os.path.islink(path) and (os.path.isdir(path) or
                                   self._ignore_symlinks):
        log.warning('Skipping symlink {}'.format(path))
        continue

      # For pattern like foo/bar/**, glob returns first path as 'foo/bar/'
      # even when foo/bar does not exist. So we skip non-existing paths.
      # Glob also returns intermediate directories if called with **. We skip
      # them to be consistent with CloudWildcardIterator.
      if self._path.endswith('**') and (not os.path.exists(path)
                                        or os.path.isdir(path)):
        continue

      file_url = storage_url.FileUrl(path)
      if os.path.isdir(path):
        yield resource_reference.FileDirectoryResource(file_url)
      else:
        yield resource_reference.FileObjectResource(file_url)


class CloudWildcardIterator(WildcardIterator):
  """Class to iterate over Cloud Storage strings containing wildcards."""

  def __init__(self,
               url,
               all_versions=False,
               error_on_missing_key=True,
               fetch_encrypted_object_hashes=False,
               fields_scope=cloud_api.FieldsScope.NO_ACL,
               get_bucket_metadata=False):
    """Instantiates an iterator that matches the wildcard URL.

    Args:
      url (CloudUrl): CloudUrl that may contain wildcard that needs expansion.
      all_versions (bool): If true, the iterator yields all versions of objects
          matching the wildcard.  If false, yields just the live object version.
      error_on_missing_key (bool): If true, and the encryption key needed to
          decrypt an object is missing, the iterator raises an error for that
          object.
      fetch_encrypted_object_hashes (bool): Fall back to GET requests for
        encrypted objects in order to fetch their hash values.
      fields_scope (cloud_api.FieldsScope): Determines amount of metadata
          returned by API.
      get_bucket_metadata (bool): If true, perform a bucket GET request when
          fetching bucket resources. Otherwise, bucket URLs without wildcards
          may be returned without verifying the buckets exist.
    """
    super(CloudWildcardIterator, self).__init__()
    self._url = _compress_url_wildcards(url)
    self._client = api_factory.get_api(self._url.scheme)

    self._all_versions = all_versions
    self._error_on_missing_key = error_on_missing_key
    self._fetch_encrypted_object_hashes = fetch_encrypted_object_hashes
    self._fields_scope = fields_scope
    self._get_bucket_metadata = get_bucket_metadata

    if url.url_string.endswith(url.delimiter):
      # Forces the API to return prefixes instead of their contents.
      url = storage_url.storage_url_from_string(
          storage_url.rstrip_one_delimiter(url.url_string))

  def __iter__(self):
    if self._url.is_provider():
      for bucket_resource in self._client.list_buckets(self._fields_scope):
        yield bucket_resource
    else:
      for bucket_or_unknown_resource in self._fetch_buckets():
        if self._url.is_bucket():
          yield bucket_or_unknown_resource
        else:  # URL is an object or prefix.
          for obj_resource in self._fetch_objects(
              bucket_or_unknown_resource.storage_url.bucket_name):
            yield obj_resource

  def _decrypt_resource_if_necessary(self, resource):
    if (self._fetch_encrypted_object_hashes and
        cloud_api.Capability.ENCRYPTION in self._client.capabilities and
        self._fields_scope != cloud_api.FieldsScope.SHORT and
        isinstance(resource, resource_reference.ObjectResource)):
      # LIST won't return GCS hash fields. Need to GET.
      if resource.kms_key:
        # Backend will reject if user does not have KMS encryption permissions.
        return self._client.get_object_metadata(resource.bucket, resource.name)
      if resource.decryption_key_hash_sha256:
        request_config = request_config_factory.get_request_config(
            resource.storage_url,
            decryption_key_hash_sha256=resource.decryption_key_hash_sha256,
            error_on_missing_key=self._error_on_missing_key)
        if getattr(request_config.resource_args, 'decryption_key', None):
          # Don't GET unless we have a key that will decrypt object.
          return self._client.get_object_metadata(resource.bucket,
                                                  resource.name, request_config)
    # No decryption necessary or don't have proper key.
    return resource

  def _try_getting_object_directly(self, bucket_name):
    """Matches user input that doesn't need expansion."""
    try:
      resource = self._client.get_object_metadata(
          bucket_name,
          self._url.object_name,
          # TODO(b/197754758): add user request args from surface.
          request_config_factory.get_request_config(self._url),
          self._url.generation,
          self._fields_scope)

      return self._decrypt_resource_if_necessary(resource)
    except api_errors.NotFoundError:
      # Object does not exist. Could be a prefix.
      pass
    return None

  def _fetch_objects(self, bucket_name):
    """Fetch all objects for the given bucket that match the URL."""
    needs_further_expansion = (
        contains_wildcard(self._url.object_name) or self._all_versions or
        self._url.url_string.endswith(self._url.delimiter))
    if not needs_further_expansion:
      # Assume that the URL represents a single object.
      direct_query_result = self._try_getting_object_directly(bucket_name)
      if direct_query_result:
        return [direct_query_result]
    # Will run if direct check found no result.
    return self._expand_object_path(bucket_name)

  def _expand_object_path(self, bucket_name):
    """Expands object names.

    Args:
      bucket_name (str): Name of the bucket.

    Yields:
      resource_reference.Resource objects where each resource can be
      an ObjectResource object or a PrefixResource object.
    """
    original_object_name = self._url.object_name
    if original_object_name.endswith(self._url.delimiter):
      if not contains_wildcard(self._url.object_name):
        # Get object with trailing slash in addition to prefix check below.
        direct_query_result = self._try_getting_object_directly(bucket_name)
        if direct_query_result:
          yield direct_query_result
      # Force API to return prefix resource not the prefix's contents.
      object_name = storage_url.rstrip_one_delimiter(original_object_name)
    else:
      object_name = original_object_name

    names_needing_expansion = collections.deque([object_name])
    error = None
    while names_needing_expansion:
      name = names_needing_expansion.popleft()

      # Parse out the prefix, delimiter, filter_pattern and suffix.
      # Given a string 'a/b*c/d/e*f/g.txt', this will return
      # CloudWildcardParts(prefix='a/b', filter_pattern='*c',
      #                    delimiter='/', suffix='d/e*f/g.txt')
      wildcard_parts = CloudWildcardParts.from_string(name, self._url.delimiter)
      # Fetch all the objects and prefixes.
      resource_iterator = self._client.list_objects(
          all_versions=self._all_versions or bool(self._url.generation),
          bucket_name=bucket_name,
          delimiter=wildcard_parts.delimiter,
          fields_scope=self._fields_scope,
          prefix=wildcard_parts.prefix or None)

      # We have all the objects and prefixes that matched wildcard_parts.prefix.
      # Use filter_pattern to eliminate non-matching objects and prefixes.
      filtered_resources = self._filter_resources(
          resource_iterator,
          wildcard_parts.prefix + wildcard_parts.filter_pattern)

      for resource in filtered_resources:
        resource_path = resource.storage_url.object_name
        if wildcard_parts.suffix:
          if isinstance(resource, resource_reference.PrefixResource):
            # Suffix is present, which indicates that we have more wildcards to
            # expand. Let's say object_name is a/b1c. Then the new string that
            # we want to expand will be a/b1c/d/e*f/g.txt
            if WILDCARD_REGEX.search(resource_path):
              error = command_errors.InvalidUrlError(
                  'Cloud folders named with wildcards are not supported.'
                  ' API returned {}'.format(resource))
            else:
              names_needing_expansion.append(resource_path +
                                             wildcard_parts.suffix)
        else:
          # Make sure regular object not returned if the original query was for
          # a prefix or object with a trailing delimiter.
          # Needed for gs://b/f*/ to filter out gs://b/f.txt.
          if (not resource_path.endswith(self._url.delimiter) and
              original_object_name.endswith(self._url.delimiter)):
            continue

          yield self._decrypt_resource_if_necessary(resource)

    if error:
      raise error

  def _get_regex_patterns(self, wildcard_pattern):
    """Returns list of regex patterns derived from the wildcard patterns.

    Args:
      wildcard_pattern (str): A wilcard_pattern to filter the resources.

    Returns:
      List of compiled regex patterns.

    This translates the wildcard_pattern and also creates some additional
    patterns so that we can treat ** in a/b/c/**/d.txt as zero or more folders.
    This means, a/b/c/d.txt will also be returned along with a/b/c/e/f/d.txt.
    """
    # Case 1: The original pattern should always be present.
    wildcard_patterns = [wildcard_pattern]
    if not wildcard_pattern.endswith(storage_url.CLOUD_URL_DELIMITER):
      # Case 2: Allow matching both objects and prefixes with same name.
      wildcard_patterns.append(wildcard_pattern +
                               storage_url.CLOUD_URL_DELIMITER)

    if '/**/' in wildcard_pattern:
      # Case 3: Will fetch object gs://bucket/dir1/a.txt if pattern is
      # gs://bucket/dir1/**/a.txt
      updated_pattern = wildcard_pattern.replace('/**/', '/')
      wildcard_patterns.append(updated_pattern)
    else:
      updated_pattern = wildcard_pattern

    for pattern in (wildcard_pattern, updated_pattern):
      if pattern.startswith('**/'):
        # Case 4 (using wildcard_pattern): Will fetch object gs://bucket/a.txt
        # if pattern is gs://bucket/**/a.txt. Note that '/**/' will match
        # '/a.txt' not 'a.txt'.
        # Case 5 (using updated_pattern): Will fetch gs://bucket/dir1/dir2/a.txt
        # if the pattern is gs://bucket/**/dir1/**/a.txt
        wildcard_patterns.append(pattern[3:])
    return [re.compile(fnmatch.translate(p)) for p in wildcard_patterns]

  def _filter_resources(self, resource_iterator, wildcard_pattern):
    """Filter out resources that do not match the wildcard_pattern.

    Args:
      resource_iterator (iterable): An iterable resource_reference.Resource
        objects.
      wildcard_pattern (str): The wildcard_pattern to filter the resources.

    Yields:
      resource_reference.Resource objects matching the wildcard_pattern
    """
    regex_patterns = self._get_regex_patterns(wildcard_pattern)
    for resource in resource_iterator:
      if (self._url.generation and
          resource.storage_url.generation != self._url.generation):
        # Filter based on generation, if generation is present in the request.
        continue
      for regex_pattern in regex_patterns:
        if regex_pattern.match(resource.storage_url.object_name):
          yield resource
          break

  def _fetch_buckets(self):
    """Fetch the bucket(s) corresponding to the url.

    Returns:
      An iterable of BucketResource or UnknownResource objects.
    """
    if contains_wildcard(self._url.bucket_name):
      return self._expand_bucket_wildcards(self._url.bucket_name)
    elif self._url.is_bucket() and self._get_bucket_metadata:
      return [
          self._client.get_bucket(self._url.bucket_name, self._fields_scope)
      ]
    else:
      # Avoids API call.
      return [resource_reference.UnknownResource(self._url)]

  def _expand_bucket_wildcards(self, bucket_name):
    """Expand bucket names with wildcard.

    Args:
      bucket_name (str): Bucket name with wildcard.

    Yields:
      BucketResource objects.
    """
    regex = fnmatch.translate(bucket_name)
    bucket_pattern = re.compile(regex)
    for bucket_resource in self._client.list_buckets(self._fields_scope):
      if bucket_pattern.match(bucket_resource.name):
        yield bucket_resource


class CloudWildcardParts:
  """Different parts of the wildcard string used for querying and filtering."""

  def __init__(self, prefix, filter_pattern, delimiter, suffix):
    """Initialize the CloudWildcardParts object.

    Args:
      prefix (str): The prefix string to be passed to the API request.
        This is the substring before the first occurrance of the wildcard.
      filter_pattern (str): The pattern to be used to filter out the results
        returned by the list_objects call. This is a substring starting from
        the first occurance of the wildcard upto the first delimiter.
      delimiter (str): The delimiter to be passed to the api request.
      suffix (str): The substirng after the first delimiter in the wildcard.
    """
    self.prefix = prefix
    self.filter_pattern = filter_pattern
    self.delimiter = delimiter
    self.suffix = suffix

  @classmethod
  def from_string(cls, string, delimiter=storage_url.CloudUrl.CLOUD_URL_DELIM):
    """Create a CloudWildcardParts instance from a string.

    Args:
      string (str): String that needs to be splitted into different parts.
      delimiter (str): The delimiter to be used for splitting the string.

    Returns:
      WildcardParts object.
    """
    # Let's assume name => "a/b/c/d*e/f/g*.txt".
    # prefix => "a/b/c/d", wildcard_string => "*e/f/g*.txt".
    prefix, wildcard_string = _split_on_wildcard(string)
    # We expand one level at a time. Hence, spliting on delimiter.
    # filter_pattern => "*e", suffix = "f/g*.txt".
    filter_pattern, _, suffix = wildcard_string.partition(delimiter)

    if '**' in filter_pattern:
      # Fetch all objects for ** pattern. No delimiter is required since we
      # want to fetch all the objects here.
      delimiter = None
      filter_pattern = wildcard_string
      # Since we have fetched all the objects, suffix is no longer required.
      suffix = None

    return cls(prefix, filter_pattern, delimiter, suffix)

  def __repr__(self):
    return debug_output.generic_repr(self)


def _split_on_wildcard(string):
  """Split the string into two such that first part does not have any wildcard.

  Args:
    string (str): The string to be split.

  Returns:
    A 2-tuple where first part doesn't have any wildcard, and second part does
    have a wildcard. If wildcard is not found, the second part is empty.
    If string starts with a wildcard then first part is empty.
    For example:
      _split_on_wildcard('a/b/c/d*e/f/*.txt') => ('a/b/c/d', '*e/f/*.txt')
      _split_on_wildcard('*e/f/*.txt') => ('', '*e/f/*.txt')
      _split_on_wildcard('a/b/c/d') => ('a/b/c/d', '')
  """
  match = WILDCARD_REGEX.search(string)
  if match is None:
    return string, ''
  first_wildcard_idx = match.start()
  prefix = string[:first_wildcard_idx]
  wildcard_str = string[first_wildcard_idx:]
  return prefix, wildcard_str
