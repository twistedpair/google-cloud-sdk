# Copyright 2017 Google Inc. All Rights Reserved.
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
"""CLI implementation for datapol taxonomies list."""

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.datapol import taxonomy
from googlecloudsdk.api_lib.util import exceptions


def ListTaxonomies(limit=None):
  """List all taxonomies visible to the current project.

  Args:
    limit: The number of taxonomies to limit the results to.

  Returns:
    A list of DataTaxonomy object as defined in API.
  """
  try:
    return taxonomy.List(limit)
  except apitools_exceptions.HttpError as e:
    exc = exceptions.HttpException(e)
    if exc.payload.status_code == 404:
      # status_code specific error message
      exc.error_format = '{api_name}: {resource_name} not found.'
    else:
      # override default error message
      exc.error_format = 'Unknown error. Status code {status_code}.'
    raise exc
