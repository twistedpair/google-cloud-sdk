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
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.tasks import task
from googlecloudsdk.core.util import scaled_integer

import six


LONG_LIST_ROW_FORMAT = ('{size:>10}  {creation_time:>19}  {url}{metageneration}'
                        '{etag}')


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
  """For formatting how items are printed when listed.

  Attributes:
    resource (resource_reference.Resource): Item to be formatted for printing.
  """

  def __init__(self, resource):
    """Initializes wrapper instance."""
    self.resource = resource


class _HeaderFormatWrapper(_BaseFormatWrapper):
  """For formatting how containers are printed as headers when listed."""

  def __str__(self):
    # This will print as "gs://bucket:" or "gs://bucket/prefix/:".
    return '\n{}:'.format(self.resource.storage_url.versionless_url_string)


class _ResourceFormatWrapper(_BaseFormatWrapper):
  """For formatting how resources print when listed."""

  def __init__(self, resource, all_versions=False,
               display_detail=DisplayDetail.SHORT, include_etag=False):
    """Initializes wrapper instance.

    Args:
      resource (resource_reference.Resource): Item to be formatted for printing.
      all_versions (bool): Display information about all versions of resource.
      display_detail (DisplayDetail): Level of metadata detail for printing.
      include_etag (bool): Display etag string of resource.
    """
    self._all_versions = all_versions
    self._display_detail = display_detail
    self._include_etag = include_etag
    super().__init__(resource)

  def _format_for_list_long(self):
    """Returns string of select properties from resource."""
    if isinstance(self.resource, resource_reference.PrefixResource):
      # Align PrefixResource URLs with ObjectResource URLs.
      return LONG_LIST_ROW_FORMAT.format(
          size='', creation_time='',
          url=self.resource.storage_url.url_string, metageneration='',
          etag='')

    creation_time = ('None' if not self.resource.creation_time else
                     self.resource.creation_time.strftime('%Y-%m-%d %H:%M:%S'))

    if self._all_versions:
      url_string = self.resource.storage_url.url_string
      metageneration_string = '  metageneration={}'.format(
          str(self.resource.metageneration))
    else:
      url_string = self.resource.storage_url.versionless_url_string
      metageneration_string = ''

    if self._include_etag:
      etag_string = '  etag={}'.format(str(self.resource.etag))
    else:
      etag_string = ''

    # Full example (add 9 spaces of padding to the left):
    # 8  2020-07-27T20:58:25Z  gs://b/o  metageneration=4  etag=CJqt6aup7uoCEAQ=
    return LONG_LIST_ROW_FORMAT.format(
        size=str(self.resource.size), creation_time=creation_time,
        url=url_string, metageneration=metageneration_string, etag=etag_string)

  def __str__(self):
    if self._display_detail == DisplayDetail.LONG and (
        isinstance(self.resource, resource_reference.ObjectResource) or
        isinstance(self.resource, resource_reference.PrefixResource)):
      return self._format_for_list_long()
    if self._all_versions:
      # Include generation in URL.
      return self.resource.storage_url.url_string
    return self.resource.storage_url.versionless_url_string


class CloudListTask(task.Task):
  """Represents an ls command operation."""

  def __init__(
      self,
      cloud_url,
      all_versions=False,
      display_detail=DisplayDetail.SHORT,
      include_etag=False,
      recursion_flag=False):
    """Initializes task.

    Args:
      cloud_url (storage_url.CloudUrl): Object for a non-local filesystem URL.
      all_versions (bool): Determine whether or not to return all versions of
          listed objects.
      display_detail (DisplayDetail): Determines level of metadata printed.
      include_etag (bool): Print etag string of resource, depending on other
          settings.
      recursion_flag (bool): Recurse through all containers and format all
          container headers.
    """
    super().__init__()

    self._cloud_url = cloud_url
    self._all_versions = all_versions
    self._display_detail = display_detail
    self._include_etag = include_etag
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
      resources_wrappers = self._recursion_helper(resources, recursion_level=0)
    # "**" overrides recursive flag.
    elif self._recursion_flag and '**' not in self._cloud_url.url_string:
      resources_wrappers = self._recursion_helper(resources, float('inf'))
    elif not resources.is_plural() and resources.peek().is_container():
      # One container was returned by the query, in which case we show
      # its contents.
      resources_wrappers = self._get_container_iterator(
          resources.peek().storage_url, recursion_level=0)
    else:
      resources_wrappers = self._recursion_helper(resources, recursion_level=1)

    object_count = total_bytes = 0
    for i, resource_wrapper in enumerate(resources_wrappers):
      if i == 0 and resource_wrapper and str(resource_wrapper)[0] == '\n':
        # First print should not begin with a line break.
        print(str(resource_wrapper)[1:])
      else:
        print(resource_wrapper)
      # For printing long listing data summary.
      if isinstance(resource_wrapper.resource,
                    resource_reference.ObjectResource):
        object_count += 1
        total_bytes += resource_wrapper.resource.size or 0
    if self._display_detail == DisplayDetail.LONG:
      print('TOTAL: {} objects, {} bytes ({})'.format(
          object_count, int(total_bytes),
          scaled_integer.FormatBinaryNumber(total_bytes, decimal_places=2)))

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
        yield _ResourceFormatWrapper(resource,
                                     all_versions=self._all_versions,
                                     display_detail=self._display_detail,
                                     include_etag=self._include_etag)
