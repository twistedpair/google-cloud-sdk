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
"""Helpers for taxonomy related operations in Cloud Category Manager."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from googlecloudsdk.api_lib.category_manager import utils


def UpdateTaxonomy(taxonomy_resource, description):
  """Updates the description of a taxonomy.

  Args:
    taxonomy_resource: A category_manager.taxonomies core.Resource object.
    description: A string representing the new taxonomy description.

  Returns:
    A Taxonomy message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesPatchRequest(
      name=taxonomy_resource.RelativeName(),
      taxonomy=messages.Taxonomy(description=description))
  return utils.GetClientInstance().projects_taxonomies.Patch(request=req)
