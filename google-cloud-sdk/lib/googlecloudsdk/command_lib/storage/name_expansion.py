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

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.core import log


class NameExpansionIterator:
  """Expand all urls passed as arguments, and yield NameExpansionResult.

  For each url, expands wildcards, object-less bucket names,
  subdir bucket names, and directory names, and generates a flat listing of
  all the matching objects/files.
  The resulting objects/files are wrapped within a NameExpansionResult instance.
  See NameExpansionResult docstring for more info.
  """

  def __init__(self,
               urls,
               all_versions=False,
               include_buckets=False,
               recursion_requested=False):
    """Instantiates NameExpansionIterator.

    Args:
      urls (Iterable[str]): The URLs to expand.
      all_versions (bool): True if all versions of objects should be fetched,
        else False.
      include_buckets (bool): True if buckets should be fetched.
      recursion_requested (bool): True if recursion is requested, else False.
    """
    self._urls = urls
    self._all_versions = all_versions
    self._include_buckets = include_buckets
    self._recursion_requested = recursion_requested

  def __iter__(self):
    """Iterates over each URL in self._urls and yield the expanded result.

    Yields:
      NameExpansionResult instance.

    Raises:
      InvalidUrlError: No matching objects found.
    """
    found_match = False
    one_url_had_no_match = False

    for url in self._urls:
      resources = plurality_checkable_iterator.PluralityCheckableIterator(
          wildcard_iterator.get_wildcard_iterator(
              url, all_versions=self._all_versions))
      is_name_expansion_iterator_empty = True
      original_storage_url = storage_url.storage_url_from_string(url)

      # Iterate over all the resource_reference.Resource objects.
      for resource in resources:
        # TODO(b/191479587): Explore refactoring these branches.
        if not resource.is_container():
          yield NameExpansionResult(resource, resource.storage_url,
                                    original_storage_url)
          is_name_expansion_iterator_empty = False
          continue

        if self._include_buckets and resource.storage_url.is_bucket():
          yield NameExpansionResult(resource, resource.storage_url,
                                    original_storage_url)
          is_name_expansion_iterator_empty = False
          if not self._recursion_requested:
            continue

        if not self._recursion_requested:
          log.warning('Omitting {} because it is a container, and recursion'
                      ' is not enabled.'.format(resource))
          continue

        # Append '**' to fetch all objects under this container.
        new_storage_url = resource.storage_url.join('**')
        child_resources = wildcard_iterator.get_wildcard_iterator(
            new_storage_url.url_string, all_versions=self._all_versions)
        for child_resource in child_resources:
          yield NameExpansionResult(child_resource, resource.storage_url,
                                    original_storage_url)
          is_name_expansion_iterator_empty = False

      if is_name_expansion_iterator_empty:
        log.warning('URL matched no objects or files: {}'.format(url))
        one_url_had_no_match = True
      else:
        found_match = True

    if not found_match:
      raise errors.InvalidUrlError('Source URLs matched no objects or files.')
    if one_url_had_no_match:
      raise errors.InvalidUrlError(
          'At least one source URL matched no objects or files.')


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
          This should be same as the resource.storage_url if recursion was not
          requested. This field is only used for cp and rsync commands.
          For everything else, this field can be ignored.
      original_url (StorageUrl): Pre-expanded URL. Useful for knowing intention.
    """
    self.resource = resource
    self.expanded_url = expanded_url
    self.original_url = original_url

  def __str__(self):
    return self.resource.storage_url.url_string

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return NotImplemented
    # Leave out original_url because two different URLs can expand to the same
    # result. This is a "results" class.
    return (self.resource == other.resource
            and self.expanded_url == other.expanded_url)
