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
from __future__ import print_function
from __future__ import unicode_literals

import abc
import enum

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.resources import gcloud_full_resource_formatter
from googlecloudsdk.command_lib.storage.resources import gsutil_full_resource_formatter
from googlecloudsdk.command_lib.storage.resources import resource_reference
from googlecloudsdk.command_lib.storage.resources import resource_util
from googlecloudsdk.command_lib.storage.resources import shim_format_util
from googlecloudsdk.command_lib.storage.tasks import task

import six


LONG_LIST_ROW_FORMAT = ('{size:>10}  {creation_time:>20}  {url}{metageneration}'
                        '{etag}')


class DisplayDetail(enum.Enum):
  """Level of detail to display about items being printed."""
  SHORT = 1
  LONG = 2
  FULL = 3
  JSON = 4


def _translate_display_detail_to_fields_scope(
    display_detail, is_bucket_listing):
  """Translates display details to fields scope equivalent.

  Args:
    display_detail (DisplayDetail): Argument to translate.
    is_bucket_listing (bool): Buckets require special handling.

  Returns:
    cloud_api.FieldsScope appropriate for the resources and display detail.
  """
  # Long listing is the same as normal listing for buckets.
  if display_detail == DisplayDetail.LONG and is_bucket_listing:
    return cloud_api.FieldsScope.SHORT

  display_detail_to_fields_scope = {
      DisplayDetail.SHORT: cloud_api.FieldsScope.SHORT,
      DisplayDetail.LONG: cloud_api.FieldsScope.NO_ACL,
      DisplayDetail.FULL: cloud_api.FieldsScope.FULL,
      DisplayDetail.JSON: cloud_api.FieldsScope.FULL,
  }
  return display_detail_to_fields_scope[display_detail]


class _BaseFormatWrapper(six.with_metaclass(abc.ABCMeta)):
  """For formatting how items are printed when listed.

  Attributes:
    resource (resource_reference.Resource): Item to be formatted for printing.
  """

  def __init__(self,
               resource,
               display_detail=DisplayDetail.SHORT,
               use_gsutil_style=False):
    """Initializes wrapper instance.

    Args:
      resource (resource_reference.Resource): Item to be formatted for printing.
      display_detail (DisplayDetail): Level of metadata detail for printing.
      use_gsutil_style (bool): Outputs closer to the style of the gsutil CLI.
    """
    self.resource = resource
    self._display_detail = display_detail
    self._use_gsutil_style = use_gsutil_style


class _HeaderFormatWrapper(_BaseFormatWrapper):
  """For formatting how containers are printed as headers when listed."""

  def __str__(self):
    if self._use_gsutil_style and isinstance(self.resource,
                                             resource_reference.BucketResource):
      # Gsutil does not show header lines for buckets.
      return ''

    url = self.resource.storage_url.versionless_url_string
    if self._display_detail == DisplayDetail.JSON:
      return self.resource.get_json_dump()
    # This will print as "gs://bucket:" or "gs://bucket/prefix/:".
    return '\n{}:'.format(url)


class _ResourceFormatWrapper(_BaseFormatWrapper):
  """For formatting how resources print when listed."""

  def __init__(self,
               resource,
               all_versions=False,
               display_detail=DisplayDetail.SHORT,
               include_etag=False,
               readable_sizes=False,
               full_formatter=None,
               use_gsutil_style=False):
    """Initializes wrapper instance.

    Args:
      resource (resource_reference.Resource): Item to be formatted for printing.
      all_versions (bool): Display information about all versions of resource.
      display_detail (DisplayDetail): Level of metadata detail for printing.
      include_etag (bool): Display etag string of resource.
      readable_sizes (bool): Convert bytes to a more human readable format for
        long lising. For example, print 1024B as 1KiB.
      full_formatter (FullResourceFormatter): A formatter to format the resource
        if display_detail == DisplayDetail.FULL
      use_gsutil_style (bool): Outputs closer to the style of the gsutil CLI.
    """
    self._all_versions = all_versions
    self._include_etag = include_etag
    self._readable_sizes = readable_sizes
    self._full_formatter = full_formatter
    super(_ResourceFormatWrapper, self).__init__(resource, display_detail,
                                                 use_gsutil_style)

  def _format_for_list_long(self):
    """Returns string of select properties from resource."""
    if isinstance(self.resource, resource_reference.PrefixResource):
      # Align PrefixResource URLs with ObjectResource URLs.
      return LONG_LIST_ROW_FORMAT.format(
          size='', creation_time='',
          url=self.resource.storage_url.url_string, metageneration='',
          etag='')

    creation_time = resource_util.get_formatted_timestamp_in_utc(
        self.resource.creation_time)

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

    if self._readable_sizes and self.resource.size is not None:
      size = shim_format_util.get_human_readable_byte_value(
          self.resource.size, use_gsutil_style=self._use_gsutil_style)
    else:
      # Also handles None values.
      size = str(self.resource.size)

    # Full example (add 9 spaces of padding to the left):
    # 8  2020-07-27T20:58:25Z  gs://b/o  metageneration=4  etag=CJqt6aup7uoCEAQ=
    return LONG_LIST_ROW_FORMAT.format(
        size=size,
        creation_time=creation_time,
        url=url_string,
        metageneration=metageneration_string,
        etag=etag_string)

  def __str__(self):
    if self._display_detail == DisplayDetail.LONG and (
        isinstance(self.resource, resource_reference.ObjectResource) or
        isinstance(self.resource, resource_reference.PrefixResource)):
      return self._format_for_list_long()
    if self._display_detail == DisplayDetail.FULL and (
        isinstance(self.resource, resource_reference.BucketResource) or
        isinstance(self.resource, resource_reference.ObjectResource)):
      return self.resource.get_full_metadata_string(
          self._full_formatter, show_version_in_url=self._all_versions)
    if self._display_detail == DisplayDetail.JSON:
      return self.resource.get_json_dump()
    if self._all_versions:
      # Include generation in URL.
      return self.resource.storage_url.url_string
    return self.resource.storage_url.versionless_url_string


class CloudListTask(task.Task):
  """Represents an ls command operation."""

  def __init__(self,
               cloud_url,
               all_versions=False,
               buckets_flag=False,
               display_detail=DisplayDetail.SHORT,
               include_etag=False,
               readable_sizes=False,
               recursion_flag=False,
               use_gsutil_style=False):
    """Initializes task.

    Args:
      cloud_url (storage_url.CloudUrl): Object for a non-local filesystem URL.
      all_versions (bool): Determine whether or not to return all versions of
        listed objects.
      buckets_flag (bool): If given a bucket URL, only return matching buckets
        ignoring normal recursion rules.
      display_detail (DisplayDetail): Determines level of metadata printed.
      include_etag (bool): Print etag string of resource, depending on other
        settings.
      readable_sizes (bool): Convert bytes to a more human readable format for
        long lising. For example, print 1024B as 1KiB.
      recursion_flag (bool): Recurse through all containers and format all
        container headers.
      use_gsutil_style (bool): Outputs closer to the style of the gsutil CLI.
    """
    super(CloudListTask, self).__init__()

    self._cloud_url = cloud_url
    self._all_versions = all_versions
    self._buckets_flag = buckets_flag
    self._display_detail = display_detail
    self._include_etag = include_etag
    self._readable_sizes = readable_sizes
    self._recursion_flag = recursion_flag
    self._use_gsutil_style = use_gsutil_style

    if use_gsutil_style:
      self._full_formatter = (
          gsutil_full_resource_formatter.GsutilFullResourceFormatter())
    else:
      self._full_formatter = (
          gcloud_full_resource_formatter.GcloudFullResourceFormatter())

    self._only_display_buckets = self._cloud_url.is_provider() or (
        self._buckets_flag and self._cloud_url.is_bucket())

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

    fields_scope = _translate_display_detail_to_fields_scope(
        self._display_detail, is_bucket_listing=False)
    iterator = wildcard_iterator.CloudWildcardIterator(
        new_cloud_url,
        all_versions=self._all_versions,
        error_on_missing_key=False,
        fields_scope=fields_scope)
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
        yield _HeaderFormatWrapper(
            resource,
            display_detail=self._display_detail,
            use_gsutil_style=self._use_gsutil_style)

        # Get container contents by adding wildcard to URL.
        nested_iterator = self._get_container_iterator(
            resource.storage_url, recursion_level-1)
        for nested_resource in nested_iterator:
          yield nested_resource

      else:
        # Resource wasn't a container we can recurse into, so just yield it.
        yield _ResourceFormatWrapper(
            resource,
            all_versions=self._all_versions,
            display_detail=self._display_detail,
            include_etag=self._include_etag,
            readable_sizes=self._readable_sizes,
            full_formatter=self._full_formatter)

  def _print_json_list(self, resource_wrappers):
    """Prints ResourceWrapper objects as JSON list."""
    is_empty_list = True
    for i, resource_wrapper in enumerate(resource_wrappers):
      is_empty_list = False
      if i == 0:
        # Start of JSON list for long long listing.
        print('[')
        print(resource_wrapper, end='')
      else:
        # Print resource without newline at end to allow list formatting for
        # unknown number of items in generator.
        print(',\n{}'.format(resource_wrapper), end='')

    # New line because we were removing it from previous prints to give us
    # the ability to do a trailing comma for JSON list printing.
    print()
    if not is_empty_list:
      # Close long long listing JSON list. Prints nothing if no items.
      print(']')

  def _print_row_list(self, resource_wrappers):
    """Prints ResourceWrapper objects in list with custom row formatting."""
    object_count = total_bytes = 0
    for i, resource_wrapper in enumerate(resource_wrappers):
      resource_wrapper_string = str(resource_wrapper)
      if not resource_wrapper_string:
        continue
      if i == 0 and resource_wrapper and resource_wrapper_string[0] == '\n':
        # First print should not begin with a line break, which can happen
        # for headers.
        print(resource_wrapper_string[1:])
      else:
        print(resource_wrapper_string)

      if isinstance(resource_wrapper.resource,
                    resource_reference.ObjectResource):
        # For printing long listing data summary.
        object_count += 1
        total_bytes += resource_wrapper.resource.size or 0

    if (self._display_detail in (DisplayDetail.LONG, DisplayDetail.FULL) and
        not self._only_display_buckets):
      # Long listing needs summary line.
      print('TOTAL: {} objects, {} bytes ({})'.format(
          object_count, int(total_bytes),
          shim_format_util.get_human_readable_byte_value(
              total_bytes, self._use_gsutil_style)))

  def execute(self, task_status_queue=None):
    """Recursively create wildcard iterators to print all relevant items."""
    # List task does not need to report status information.
    del task_status_queue

    fields_scope = _translate_display_detail_to_fields_scope(
        self._display_detail, is_bucket_listing=self._cloud_url.is_provider())
    resources = plurality_checkable_iterator.PluralityCheckableIterator(
        wildcard_iterator.CloudWildcardIterator(
            self._cloud_url,
            all_versions=self._all_versions,
            error_on_missing_key=False,
            fields_scope=fields_scope,
            get_bucket_metadata=self._buckets_flag))

    if resources.is_empty():
      raise errors.InvalidUrlError('One or more URLs matched no objects.')
    if self._only_display_buckets:
      # Received a provider URL ("gs://") -> List all buckets.
      # Received buckets flag and bucket URL -> List matching buckets, ignoring
      #   recursion.
      resources_wrappers = self._recursion_helper(resources, recursion_level=0)
    elif self._recursion_flag and '**' not in self._cloud_url.url_string:
      # "**" overrides recursive flag.
      resources_wrappers = self._recursion_helper(resources, float('inf'))
    elif not resources.is_plural() and resources.peek().is_container():
      # One container was returned by the query, in which case we show
      # its contents.
      resources_wrappers = self._get_container_iterator(
          resources.peek().storage_url, recursion_level=0)
    else:
      resources_wrappers = self._recursion_helper(resources, recursion_level=1)

    if self._display_detail == DisplayDetail.JSON:
      self._print_json_list(resources_wrappers)
    else:
      self._print_row_list(resources_wrappers)
