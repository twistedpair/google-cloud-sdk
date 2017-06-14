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

"""CLI implementation for datapol taxonomies describe."""

from apitools.base.py import exceptions as apitools_exceptions
from googlecloudsdk.api_lib.datapol import taxonomy
from googlecloudsdk.api_lib.util import exceptions


def DescribeTaxonomy(taxonomy_id):
  """Show the contents of the named taxonomy.

  Args:
    taxonomy_id: id of the taxonomy.

  Raises:
    exceptions.HttpException: on unknown errors.

  Returns:
    It always returns 0 if no exceptions raised.
  """

  try:
    pol_taxonomy = taxonomy.Get(taxonomy_id)
    print '{0}: {1}'.format(pol_taxonomy.name, pol_taxonomy.description)
    # TODO(b/32858676): Print ACL and (annotations, descriptions) in the
    # taxonomy.
  except apitools_exceptions.HttpError as e:
    exc = exceptions.HttpException(e)
    if exc.payload.status_code == 404:
      # status_code specific error message
      exc.error_format = '{api_name}: {resource_name} not found.'
    else:
      # override default error message
      exc.error_format = 'Unknown error. Status code {status_code}.'
    raise exc

  return 0
