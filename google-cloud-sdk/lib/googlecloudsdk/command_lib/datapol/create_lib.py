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

"""CLI implementation for datapol taxonomies create."""

from googlecloudsdk.api_lib.datapol import taxonomy


def CreateTaxonomy(name, administrators, users, load, description):
  """Create the named taxonomy, with specified administrators & users.

  Args:
    name: name of the taxonomy.
    administrators: comma-separated list of users as administrators of the
        taxonomy.
    users: comma-separated list of users who can use this taxonomy to annotate
        data assets.
    load: load annotations from a file.
    description: description of this taxonomy.

  Returns:
    A PolicyTaxonomy object as defined in API.
  """
  pol_taxonomy = taxonomy.Create(name, description)
  # TODO(b/32858676): set admin / user permissions properly.

  if(load):
    # TODO(b/32858676): populate annotations from the file.
    pass

  return pol_taxonomy
