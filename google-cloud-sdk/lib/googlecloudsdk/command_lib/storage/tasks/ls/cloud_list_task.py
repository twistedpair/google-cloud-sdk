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

from googlecloudsdk.command_lib.storage import errors
from googlecloudsdk.command_lib.storage import plurality_checkable_iterator
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.command_lib.storage import wildcard_iterator
from googlecloudsdk.command_lib.storage.tasks import task


class CloudListTask(task.Task):
  """Represents an ls command operation."""

  def __init__(self, cloud_url, all_versions=False):
    """Initializes task.

    Args:
      cloud_url (storage_url.CloudUrl): Object for a non-local filesystem URL.
      all_versions (bool): Determine whether or not to return all versions of
          listed objects.
    """
    super().__init__()

    self._cloud_url = cloud_url
    self._all_versions = all_versions

  def execute(self, callback=None):
    """Recursively create wildcard iterators to print all relevant items."""

    resources = []
    if self._cloud_url.is_provider():
      # Received a provider URL ("gs://"). List bucket names with no formatting.
      resources = wildcard_iterator.CloudWildcardIterator(self._cloud_url)
    else:
      resources = plurality_checkable_iterator.PluralityCheckableIterator(
          iter(wildcard_iterator.CloudWildcardIterator(self._cloud_url)))

      if resources.is_empty():
        raise errors.InvalidUrlError('One or more URLs matched no objects.')
      elif not resources.is_plural() and resources.peek().is_container():
        # One container was returned by the query, in which case we show
        # its contents.
        resources = self._get_container_iterator(resources.peek().storage_url,
                                                 recursion_level=0)
      else:
        resources = self._recursion_helper(resources, recursion_level=1)

    for resource in resources:
      if isinstance(resource, resource_reference.Resource):
        # All Resource objects have cloud urls because ls does not work locally.
        print(resource.storage_url.versionless_url_string)
      else:
        # May be a formatted string.
        print(resource)

    if callback:
      callback()

  def _get_container_iterator(self, cloud_url, recursion_level):
    """For recursing into and retrieving the contents of a container.

    Args:
      cloud_url (storage_url.CloudUrl): Container URL for recursing into.
      recursion_level (int): Determines if iterator should keep recursing.

    Returns:
      An iterator of resource_reference.Resource objects.
    """

    # End URL with '/*', so WildcardIterator won't filter out its contents.
    new_url_string = cloud_url.url_string
    if cloud_url.url_string[-1] != cloud_url.delimiter:
      new_url_string += cloud_url.delimiter
    new_cloud_url = storage_url.storage_url_from_string(new_url_string + '*')

    iterator = wildcard_iterator.CloudWildcardIterator(new_cloud_url)
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
      resource_reference.Resource objects.
    """
    # If we're showing the contents of containers at this level and not going
    # deeper, then we need a new line before every container and colon after:
    #
    # gs://bucket1/dir1/object2
    #
    # gs://bucket1/dir1/subdir1/:
    # gs://bucket1/dir1/subdir1/object3
    #
    # The exception is that a new line is not needed if the first item displayed
    # is a container.
    new_line_before_container = ''

    for resource in iterator:
      # Check if we need to display contents of a container.
      if resource.is_container() and recursion_level > 0:

        # Container header formatting. Voided by ** unless gs://**.
        yield '{}{}:'.format(new_line_before_container,
                             str(resource.storage_url))

        # Get container contents by adding wildcard to URL.
        nested_iterator = self._get_container_iterator(
            resource.storage_url, recursion_level-1)
        for nested_resource in nested_iterator:
          yield nested_resource

      # Resource wasn't a container we can recurse into, so just yield it.
      else:
        yield resource
      # We've passed the first item. Any new containers need a line break.
      new_line_before_container = '\n'
