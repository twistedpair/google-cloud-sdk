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

"""File and Cloud URL representation classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions as core_exceptions


class Error(core_exceptions.Error):
  """Base exception for command_lib.storage modules."""


class FatalError(Error):
  """Error raised when future execution should stop."""


class HashMismatchError(Error):
  """Error raised when hashes don't match after operation."""


class InvalidPythonVersionError(Error):
  """Error raised for an invalid Python version."""


class InvalidUrlError(Error):
  """Error raised when the url string is not in the expected format."""


class ValueCannotBeDeterminedError(Error):
  """Error raised when attempting to access unknown information."""


def _raise_error_for_wrong_resource_type(command_list, expected_resource_type,
                                         example, url):
  """Raises error for user input mismatched with command resource type.

  Example message:

  "gcloud storage buckets" create only accepts bucket URLs.
  Example: "gs://bucket"
  Received: "gs://user-bucket/user-object.txt"

  Args:
    command_list (list[str]): The command being run. Can be gotten from an
      argparse object with `args.command_path`.
    expected_resource_type (str): Raise an error because we did not get this.
    example: (str): An example of a URL to a resource with the correct type.
    url (StorageUrl): The erroneous URL received.

  Raises:
    InvalidUrlError: Explains that the user entered a URL for the wrong type
      of resource.
  """

  raise InvalidUrlError(
      '"{}" only accepts {} URLs.\nExample: "{}"\nReceived: "{}"'.format(
          ' '.join(command_list), expected_resource_type, example, url))


def raise_error_if_not_bucket(command_list, url):
  if not url.is_bucket():
    _raise_error_for_wrong_resource_type(command_list, 'bucket', 'gs://bucket',
                                         url)


def raise_error_if_not_cloud_object(command_list, url):
  if not url.is_object():
    _raise_error_for_wrong_resource_type(command_list, 'object',
                                         'gs://bucket/object.txt', url)
