# -*- coding: utf-8 -*- #
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
from __future__ import unicode_literals

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


def ListTaxonomies(project_resource):
  """Lists all taxonomies in a project resource.

  Args:
    project_resource: The project resource container of the taxonomies to list.

  Returns:
    A list of taxonomy messages.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesListRequest(
      parent=project_resource.RelativeName())
  return utils.GetClientInstance().projects_taxonomies.List(request=req)


def CreateTaxonomy(project_resource, display_name, description=None):
  """Creates a taxonomy in the project resource container.

  Args:
    project_resource: The project resource representing the project to create
      the taxonomy in.
    display_name: The display name given to the taxonomy.
    description: The taxonomy description.

  Returns:
    The created Taxonomy message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesCreateRequest(
      parent=project_resource.RelativeName(),
      taxonomy=messages.Taxonomy(
          displayName=display_name, description=description))
  return utils.GetClientInstance().projects_taxonomies.Create(request=req)


def DeleteTaxonomy(taxonomy_resource):
  """Deletes a taxonomy resource.

  Args:
    taxonomy_resource: The resource path of the taxonomy to delete.

  Returns:
    An empty message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesDeleteRequest(
      name=taxonomy_resource.RelativeName())
  return utils.GetClientInstance().projects_taxonomies.Delete(request=req)
