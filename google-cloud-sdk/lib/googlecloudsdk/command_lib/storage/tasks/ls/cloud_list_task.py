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

"""Task for retrieving a list of resources from the cloud.

Typically executed in a task iterator:
googlecloudsdk.command_lib.storage.tasks.task_executor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import enum

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.tasks import task

import six


class DisplayDetail(enum.Enum):
  """Level of detail to display about items being printed."""
  SHORT = 1
  LONG = 2
  FULL = 3


_DISPLAY_DETAIL_TO_FIELDS_SCOPE = {
    DisplayDetail.SHORT: cloud_api.FieldsScope.SHORT,
    DisplayDetail.LONG: cloud_api.FieldsScope.NO_ACL,
    DisplayDetail.FULL: cloud_api.FieldsScope.FULL
}


class _BaseFormatWrapper(six.with_metaclass(abc.ABCMeta)):
  """For formatting how items are printed when listed."""

  def __init__(self, resource):
    """Initializes wrapper class.

    Args:
      resource (resource_reference.Resource): Item to be formatted for printing.
    """
    self._resource = resource
    super().__init__()


class _ResourceFormatWrapper(_BaseFormatWrapper):
  """For formatting how resources print when listed."""

  def __str__(self):
    # We can be confident versionless_url_string exists because all
    # storage_url's will be CloudUrl's.
    return self._resource.storage_url.versionless_url_string


class _HeaderFormatWrapper(_BaseFormatWrapper):
  """For formatting how containers are printed as headers when listed."""

  def __str__(self):
    # This will print as "gs://bucket:" or "gs://bucket/prefix/:".
    return '\n{}:'.format(str(self._resource.storage_url))


class CloudListTask(task.Task):
  """Represents an ls command operation."""

  def __init__(
      self,
      cloud_url,
      all_versions=False,
      display_detail=DisplayDetail.SHORT,
      recursion_flag=False):
    """Initializes task.

    Args:
      cloud_url (storage_url.CloudUrl): Object for a non-local filesystem URL.
      all_versions (bool): Determine whether or not to return all versions of
          listed objects.
      display_detail (DisplayDetail): Determines level of metadata printed.
      recursion_flag (bool): Recurse through all containers and format all
          container headers.
    """
    super().__init__()

    self._cloud_url = cloud_url
    self._all_versions = all_versions
    self._display_detail = display_detail
    self._recursion_flag = recursion_flag

  def execute(self, callback=None):
    """Recursively create wildcard iterators to print all relevant items."""

    resources = plurality_checkable_iterator.PluralityCheckableIterator(
        wildcard_iterator.CloudWildcardIterator(
            self._cloud_url,
            fields_scope=_DISPLAY_DETAIL_TO_FIELDS_SCOPE[self._display_detail]))

    if resources.is_empty():
      raise errors.InvalidUrlError('One or more URLs matched no objects.')
    if self._cloud_url.is_provider():
      # Received a provider URL ("gs://"). List bucket names with no formatting.
      resources = self._recursion_helper(resources, recursion_level=0)
    # "**" overrides recursive flag.
    elif self._recursion_flag and '**' not in self._cloud_url.url_string:
      resources = self._recursion_helper(resources, float('inf'))
    elif not resources.is_plural() and resources.peek().is_container():
      # One container was returned by the query, in which case we show
      # its contents.
      resources = self._get_container_iterator(
          resources.peek().storage_url, recursion_level=0)
    else:
      resources = self._recursion_helper(resources, recursion_level=1)

    for i, resource in enumerate(resources):
      if i == 0 and resource and str(resource)[0] == '\n':
        # First print should not begin with a line break.
        print(str(resource)[1:])
      else:
        print(resource)

    if callback:
      callback()

  def _get_container_iterator(
      self, cloud_url, recursion_level):
    """For recursing into and retrieving the contents of a container.

    Args:
      cloud_url (storage_url.CloudUrl): Container URL for recursing into.
      recursion_level (int): Determines if iterator should keep recursing.

    Returns:
      _BaseFormatWrapper generator.
    """
    # End URL with '/*', so WildcardIterator won't filter out its contents.
    new_url_string = cloud_url.versionless_url_string
    if cloud_url.versionless_url_string[-1] != cloud_url.delimiter:
      new_url_string += cloud_url.delimiter
    new_cloud_url = storage_url.storage_url_from_string(new_url_string + '*')

    iterator = wildcard_iterator.CloudWildcardIterator(
        new_cloud_url,
        fields_scope=_DISPLAY_DETAIL_TO_FIELDS_SCOPE[self._display_detail])
    return self._recursion_helper(iterator, recursion_level)

  def _recursion_helper(self, iterator, recursion_level):
    """For retrieving resources from URLs that potentially contain wildcards.

    Args:
      iterator (Iterable[resource_reference.Resource]): For recursing through.
      recursion_level (int): Integer controlling how deep the listing
          recursion goes. "1" is the default, mimicking the actual OS ls, which
          lists the contents of the first level of matching subdirectories.
          Call with "float('inf')" for listing everything available.

    Yields:
      _BaseFormatWrapper generator.
    """
    for resource in iterator:
      # Check if we need to display contents of a container.
      if resource.is_container() and recursion_level > 0:
        yield _HeaderFormatWrapper(resource)

        # Get container contents by adding wildcard to URL.
        nested_iterator = self._get_container_iterator(
            resource.storage_url, recursion_level-1)
        for nested_resource in nested_iterator:
          yield nested_resource

      else:
        # Resource wasn't a container we can recurse into, so just yield it.
        yield _ResourceFormatWrapper(resource)
