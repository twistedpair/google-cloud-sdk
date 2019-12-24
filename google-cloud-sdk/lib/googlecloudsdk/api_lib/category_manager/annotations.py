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
"""Helpers for annotation related operations in Cloud Category Manager."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.category_manager import utils


def UpdateAnnotation(annotation_resource, description):
  """Updates the description of an annotation.

  Args:
    annotation_resource: A category_manager.taxonomies.annotations
      core.Resource object.
    description: A string representing the new annotation description.

  Returns:
    An Annotation message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesAnnotationsPatchRequest(
      name=annotation_resource.RelativeName(),
      annotation=messages.Annotation(description=description))
  return utils.GetClientInstance().projects_taxonomies_annotations.Patch(
      request=req)


def CreateAnnotation(taxonomy_resource,
                     display_name,
                     description=None,
                     parent_annotation_id=None):
  """Creates an annotation in the specified taxonomy.

  Dy default the annotation is created as a root annotation, but an annotation
  can also be created as a child of another annotation by specifying a
  parent_annotation.

  Args:
    taxonomy_resource: The taxonomy container for the new annotation.
    display_name: The display name given to the annotation.
    description: The annotation description.
    parent_annotation_id: The parent annotation, if any.

  Returns:
    The created Annotation message.
  """
  messages = utils.GetMessagesModule()
  req = messages.CategorymanagerProjectsTaxonomiesAnnotationsCreateRequest(
      parent=taxonomy_resource.RelativeName(),
      annotation=messages.Annotation(
          displayName=display_name,
          description=description,
          parentAnnotationId=parent_annotation_id))
  return utils.GetClientInstance().projects_taxonomies_annotations.Create(
      request=req)
