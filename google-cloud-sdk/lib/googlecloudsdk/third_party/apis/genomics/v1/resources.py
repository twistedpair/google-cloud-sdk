# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Resource definitions for cloud platform apis."""

import enum


BASE_URL = 'https://genomics.googleapis.com/v1/'


class Collections(enum.Enum):
  """Collections for all supported apis."""

  ANNOTATIONS = (
      'annotations',
      'annotations/{annotationId}',
      {},
      [u'annotationId'],
      'GenomicsAnnotationsGetRequest',)
  ANNOTATIONSETS = (
      'annotationsets',
      'annotationsets/{annotationSetId}',
      {},
      [u'annotationSetId'],
      'GenomicsAnnotationsetsGetRequest',)
  CALLSETS = (
      'callsets',
      'callsets/{callSetId}',
      {},
      [u'callSetId'],
      'GenomicsCallsetsGetRequest',)
  DATASETS = (
      'datasets',
      'datasets/{datasetId}',
      {},
      [u'datasetId'],
      'GenomicsDatasetsGetRequest',)
  OPERATIONS = (
      'operations',
      '{+name}',
      {
          '':
              'operations/{operationsId}',
      },
      [u'name'],
      'GenomicsOperationsGetRequest',)
  READGROUPSETS = (
      'readgroupsets',
      'readgroupsets/{readGroupSetId}',
      {},
      [u'readGroupSetId'],
      'GenomicsReadgroupsetsGetRequest',)
  REFERENCES = (
      'references',
      'references/{referenceId}',
      {},
      [u'referenceId'],
      'GenomicsReferencesGetRequest',)
  REFERENCESETS = (
      'referencesets',
      'referencesets/{referenceSetId}',
      {},
      [u'referenceSetId'],
      'GenomicsReferencesetsGetRequest',)
  VARIANTS = (
      'variants',
      'variants/{variantId}',
      {},
      [u'variantId'],
      'GenomicsVariantsGetRequest',)
  VARIANTSETS = (
      'variantsets',
      'variantsets/{variantSetId}',
      {},
      [u'variantSetId'],
      'GenomicsVariantsetsGetRequest',)

  def __init__(self, collection_name, path, flat_paths, params, request_type):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
    self.request_type = request_type
