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
"""Module for handling recursive expansion."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.core import log
from googlecloudsdk.core.util import debug_output


class NameExpansionIterator:
  """Expand all urls passed as arguments, and yield NameExpansionResult.

  For each url, expands wildcards, object-less bucket names,
  subdir bucket names, and directory names, and generates a flat listing of
  all the matching objects/files.
  The resulting objects/files are wrapped within a NameExpansionResult instance.
  See NameExpansionResult docstring for more info.
  """

  def __init__(self,
               urls_iterable,
               all_versions=False,
               fields_scope=cloud_api.FieldsScope.NO_ACL,
               ignore_symlinks=False,
               include_buckets=False,
               recursion_requested=False):
    """Instantiates NameExpansionIterator.

    Args:
      urls_iterable (Iterable[str]): The URLs to expand.
      all_versions (bool): True if all versions of objects should be fetched,
        else False.
      fields_scope (cloud_api.FieldsScope): Determines amount of metadata
        returned by API.
      ignore_symlinks (bool): Skip over symlinks instead of following them.
      include_buckets (bool): True if buckets should be fetched.
      recursion_requested (bool): True if recursion is requested, else False.
    """
    self.all_versions = all_versions

    self._urls_iterator = (
        plurality_checkable_iterator.PluralityCheckableIterator(urls_iterable))
    self._fields_scope = fields_scope
    self._ignore_symlinks = ignore_symlinks
    self._include_buckets = include_buckets
    self._recursion_requested = recursion_requested

    self._top_level_iterator = (
        plurality_checkable_iterator.PluralityCheckableIterator(
            self._get_top_level_iterator()))
    self._has_multiple_top_level_resources = None
    self._url_found_match_tracker = collections.OrderedDict()

  def _get_wildcard_iterator(self, url):
    """Returns get_wildcard_iterator with instance variables as args."""
    return wildcard_iterator.get_wildcard_iterator(
        url,
        all_versions=self.all_versions,
        fields_scope=self._fields_scope,
        ignore_symlinks=self._ignore_symlinks)

  @property
  def has_multiple_top_level_resources(self):
    """Returns if the iterator yields plural items without recursing.

    Also returns True if the iterator was created with multiple URLs.
    This may not be true if one URL doesn't return anything, but it's
    consistent with gsutil and the user's probable intentions.

    Returns:
      Boolean indicating if iterator contains multiple top-level sources.
    """
    if self._has_multiple_top_level_resources is None:
      self._has_multiple_top_level_resources = (
          self._urls_iterator.is_plural() or
          self._top_level_iterator.is_plural())
    return self._has_multiple_top_level_resources

  def _get_top_level_iterator(self):
    for url in self._urls_iterator:
      # Set to True if associated Cloud resource found in __iter__.
      self._url_found_match_tracker[url] = False
      for resource in self._get_wildcard_iterator(url):
        original_storage_url = storage_url.storage_url_from_string(url)
        yield url, self._get_name_expansion_result(resource,
                                                   resource.storage_url,
                                                   original_storage_url)

  def _get_nested_objects_iterator(self, parent_name_expansion_result):
    new_storage_url = parent_name_expansion_result.resource.storage_url.join(
        '**')
    child_resources = self._get_wildcard_iterator(new_storage_url.url_string)
    for child_resource in child_resources:
      yield self._get_name_expansion_result(
          child_resource, parent_name_expansion_result.resource.storage_url,
          parent_name_expansion_result.original_url)

  def _get_name_expansion_result(self, resource, expanded_url, original_url):
    """Returns a NameExpansionResult, removing generations when appropriate."""
    keep_generation_in_url = (
        self.all_versions or
        original_url.generation  # User requested a specific generation.
    )
    if not keep_generation_in_url:
      new_storage_url = storage_url.storage_url_from_string(
          resource.storage_url.versionless_url_string)
      resource.storage_url = new_storage_url
    return NameExpansionResult(resource, expanded_url, original_url)

  def _raise_no_url_match_error_if_necessary(self):
    non_matching_urls = [
        url for url, found_match in self._url_found_match_tracker.items()
        if not found_match
    ]
    if non_matching_urls:
      raise errors.InvalidUrlError(
          'The following URLs matched no objects or files:\n-{}'.format(
              '\n-'.join(non_matching_urls)))

  def __iter__(self):
    """Iterates over each URL in self._urls_iterator and yield the expanded result.

    Yields:
      NameExpansionResult instance.

    Raises:
      InvalidUrlError: No matching objects found.
    """
    self._has_multiple_top_level_resources = self._top_level_iterator.is_plural(
    )
    for input_url, name_expansion_result in self._top_level_iterator:
      should_return_bucket = self._include_buckets and isinstance(
          name_expansion_result.resource, resource_reference.BucketResource)
      if not name_expansion_result.resource.is_container() or (
          should_return_bucket):
        self._url_found_match_tracker[input_url] = True
        yield name_expansion_result

      if name_expansion_result.resource.is_container():
        if self._recursion_requested:
          for nested_name_expansion_result in self._get_nested_objects_iterator(
              name_expansion_result):
            self._url_found_match_tracker[input_url] = True
            yield nested_name_expansion_result

        elif not should_return_bucket:
          # Does not warn about buckets processed above because it's confusing
          # to warn about something that was successfully processed.
          log.warning('Omitting {} because it is a container, and recursion'
                      ' is not enabled.'.format(name_expansion_result.resource))

    self._raise_no_url_match_error_if_necessary()


class NameExpansionResult:
  """Holds one fully expanded result from iterating over NameExpansionIterator.

  This class is required to pass the expanded_url information to the caller.
  This information is required for cp and rsync command, where the destination
  name is determined based on the expanded source url.
  For example, let's say we have the following objects:
  gs://bucket/dir1/a.txt
  gs://bucket/dir1/b/c.txt

  If we run the following command:
  cp -r gs://bucket/dir* foo

  We would need to know that gs://bucket/dir* was expanded to gs://bucket/dir1
  so that we can determine destination paths (foo/a.txt, foo/b/c.txt) assuming
  that foo does not exist.

  Attributes:
    resource (Resource): Yielded by the WildcardIterator.
    expanded_url (StorageUrl): The expanded wildcard url.
    original_url (StorageUrl): Pre-expanded URL.
  """

  def __init__(self, resource, expanded_url, original_url):
    """Initialize NameExpansionResult.

    Args:
      resource (resource_reference.Resource): Yielded by the WildcardIterator.
      expanded_url (StorageUrl): The expanded url string without any wildcard.
        This value should preserve generation even if not available in
        resource.storage_url. The versionless version of this should be same
        as resource.storage_url if recursion was not requested. This field is
        intended for only the cp and rsync commands.
      original_url (StorageUrl): Pre-expanded URL. Useful for knowing intention.
    """
    self.resource = resource
    self.expanded_url = expanded_url
    self.original_url = original_url

  def __repr__(self):
    return debug_output.generic_repr(self)

  def __str__(self):
    return self.resource.storage_url.url_string

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    # Leave out original_url because two different URLs can expand to the same
    # result. This is a "results" class.
    return (self.resource == other.resource
            and self.expanded_url == other.expanded_url)
