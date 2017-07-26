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
      [u'annotationId']
  )
  ANNOTATIONSETS = (
      'annotationsets',
      'annotationsets/{annotationSetId}',
      {},
      [u'annotationSetId']
  )
  CALLSETS = (
      'callsets',
      'callsets/{callSetId}',
      {},
      [u'callSetId']
  )
  DATASETS = (
      'datasets',
      'datasets/{datasetId}',
      {},
      [u'datasetId']
  )
  OPERATIONS = (
      'operations',
      '{+name}',
      {
          '':
              'operations/{operationsId}',
      },
      [u'name']
  )
  READGROUPSETS = (
      'readgroupsets',
      'readgroupsets/{readGroupSetId}',
      {},
      [u'readGroupSetId']
  )
  REFERENCES = (
      'references',
      'references/{referenceId}',
      {},
      [u'referenceId']
  )
  REFERENCESETS = (
      'referencesets',
      'referencesets/{referenceSetId}',
      {},
      [u'referenceSetId']
  )
  VARIANTS = (
      'variants',
      'variants/{variantId}',
      {},
      [u'variantId']
  )
  VARIANTSETS = (
      'variantsets',
      'variantsets/{variantSetId}',
      {},
      [u'variantSetId']
  )

  def __init__(self, collection_name, path, flat_paths, params):
    self.collection_name = collection_name
    self.path = path
    self.flat_paths = flat_paths
    self.params = params
