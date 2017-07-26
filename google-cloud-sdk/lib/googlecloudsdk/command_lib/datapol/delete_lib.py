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

"""CLI implementation for datapol taxonomies delete."""

from googlecloudsdk.api_lib.datapol import taxonomy


def DeleteTaxonomy(taxonomy_id):
  """Delete the named taxonomy.

  Args:
    taxonomy_id: id of the taxonomy.

  Returns:
    An Operation message which can be used to check the progress of taxonomy
    deletion.
  """
  # TODO(b/32858676): wait on API call to finish before returning to surface;
  #   add error handling as well.
  return taxonomy.Delete(taxonomy_id)
