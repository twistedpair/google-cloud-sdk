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
"""Helpers to interact with the Annotation serivce via the Cloud Datapol API."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.datapol import utils


def _GetService():
  """Gets the data policy annotation service."""
  return utils.GetClientInstance().orgs_policyTaxonomies_annotations


def Create(parent,
           annotation_name,
           description,
           parent_annotation=None,
           child_annotations=None):
  """Makes an API call to create an annotation in the given taxonomy.

  Args:
    parent: Resource name of a taxonomy.
    annotation_name: Name of the annotation.
    description: a short description to the annotation.
    parent_annotation: Name of the parent annotation to this annotation.
    child_annotations: Names of child annotations of this annotaiton.

  Returns:
    An Annotation message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().Create(
      messages.DatapolOrgsPolicyTaxonomiesAnnotationsCreateRequest(
          parent=parent,
          annotation=messages.Annotation(
              annotationName=annotation_name,
              description=description,
              parentAnnotation=parent_annotation,
              childAnnotations=child_annotations
              if child_annotations else [])))


def Delete(name):
  """Makes an API call to delete an annotation.

  Args:
    name: Resource name of the annotation.

  Returns:
    An Operation message which can be used to check on the progress of the
    project creation.
  """
  return _GetService().Delete(
      utils.GetMessagesModule()
      .DatapolOrgsPolicyTaxonomiesAnnotationsDeleteRequest(name=name))


def Get(name):
  """Makes an API call to get the definition of an annotation.

  Args:
    name: Resource name of the annotation.

  Returns:
    An Annotation message.
  """
  return _GetService().Get(
      utils.GetMessagesModule()
      .DatapolOrgsPolicyTaxonomiesAnnotationsGetRequest(name=name))


def List(parent, limit=None):
  """Makes API calls to list annotations under the given taxonomy.

  Args:
    parent: Resource name of a taxonomy.
    limit: The number of taxonomies to limit the resutls to.

  Returns:
    Generator that yields taxonomies
  """
  request = utils.GetMessagesModule(
  ).DatapolOrgsPolicyTaxonomiesAnnotationsListRequest(parent=parent)
  return list_pager.YieldFromList(
      _GetService(),
      request,
      limit=limit,
      field='annotations',
      batch_size_attribute='pageSize')


def Update(name, description):
  """Makes an API call to update an annotation.

  Args:
    name: Resource name of the annotation.
    description: New description to be updated.

  Returns:
    An Annotation message.
  """
  messages = utils.GetMessagesModule()
  return _GetService().Patch(
      messages.DatapolOrgsPolicyTaxonomiesAnnotationsPatchRequest(
          name=name,
          updateAnnotationRequest=messages.UpdateAnnotationRequest(
              description=description)))
