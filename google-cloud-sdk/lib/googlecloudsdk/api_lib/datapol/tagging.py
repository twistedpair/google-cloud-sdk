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

from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.datapol import utils
from googlecloudsdk.core import resources


# TODO(b/36551117) Use parsed resource objects instead of resource name.
def Apply(data, taxonomy_id, annotation_id):
  """Applies an annotation to a data asset.

  Args:
    data: Name of the data to be annotated.
    taxonomy_id: Id of the policy taxonomy.
    annotation_id: Id of the annotation. This annotation must belong to
      the policy taxonomy specified in taxonomy_name.

  Returns:
    An AnnotationTag message.
  """
  client = utils.GetClientInstance().data_taxonomyStores_dataTaxonomies
  messages = utils.GetMessagesModule()
  name = resources.REGISTRY.Create(
      'datapol.data.taxonomy',
      data=data,
      taxonomyStoresId=utils.GetTaxonomyStoresId(),
      dataTaxonomiesId=taxonomy_id).RelativeName()
  try:
    return client.ApplyAnnotationTag(
        messages.
        DatapolDataTaxonomyStoresDataTaxonomiesApplyAnnotationTagRequest(
            name=name,
            applyAnnotationTagRequest=messages.ApplyAnnotationTagRequest(
                annotationId=annotation_id)))
  except apitools_exceptions.HttpError as e:
    raise utils.ErrorWrapper(e, name)


def Delete(data, taxonomy_id):
  """Deletes an annotation on a data asset.

  Args:
    data: Name of the data to be annotated.
    taxonomy_id: Id of the policy taxonomy.

  Returns:
    An Empty message.
  """
  client = utils.GetClientInstance().data_taxonomyStores_dataTaxonomies
  name = resources.REGISTRY.Create(
      'datapol.data.tag',
      data=data,
      taxonomyStoresId=utils.GetTaxonomyStoresId(),
      dataTaxonomiesId=taxonomy_id).RelativeName()
  try:
    return client.DeleteAnnotationTag(
        utils.GetMessagesModule()
        .DatapolDataTaxonomyStoresDataTaxonomiesDeleteAnnotationTagRequest(
            name=name))
  except apitools_exceptions.HttpError as e:
    raise utils.ErrorWrapper(e, name)


def ListTags(data, limit=None):
  """Lists all annotation tags on a data asset.

  Args:
    data: Name of the data.
    limit: The number of annotation tags to limit the resutls to.

  Returns:
    Generator that yields annnotation tags.
  """
  request = utils.GetMessagesModule(
  ).DatapolDataTaxonomyStoresAnnotationTagsListRequest(
      parent='data/{data}'.format(data=data))
  return list_pager.YieldFromList(
      utils.GetClientInstance().data_taxonomyStores_annotationTags,
      request,
      limit=limit,
      field='tags',
      batch_size_attribute='pageSize')


def ListDataAssets(annotations=None,
                   include_annotated_by_group=False,
                   annotatable_only=True,
                   filter_exp='',
                   limit=None):
  """Lists resource names of all data assets with the given annotations.

  Args:
    annotations: A list of annotations. Each returned data asset will be tagged
      with at one of those annotations.
    include_annotated_by_group: If true, and a given annotation has child
      annotations, also returns data assets that are annotated with those child
      annotations.
    annotatable_only: If true, only returns data assets that are annotatable by
      the caller.
    filter_exp: A expression to further filter data assets
    limit: The number of resource names to limit the resutls to.

  Returns:
    Generator that yields resource names of data assets.
  """
  request = utils.GetMessagesModule().DatapolDataAssetsListResourceNamesRequest(
      annotations=annotations or [],
      includeAnnotatedByGroup=include_annotated_by_group,
      annotatableOnly=annotatable_only,
      filter=filter_exp)
  return list_pager.YieldFromList(
      utils.GetClientInstance().dataAssets,
      request,
      limit=limit,
      method='ListResourceNames',
      field='dataAssets',
      batch_size_attribute='pageSize')
