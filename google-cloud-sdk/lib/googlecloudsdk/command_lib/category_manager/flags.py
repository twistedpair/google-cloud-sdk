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
"""Helpers for commandline flags in Cloud Category Manager."""

from googlecloudsdk.api_lib.category_manager import store
from googlecloudsdk.api_lib.category_manager import utils
from googlecloudsdk.core import resources


def AddStoreResourceFlags(parser):
  """Add taxonomy resource flags to the parser."""
  parser.add_argument(
      'store_resource',
      metavar='STORE',
      nargs='?',
      help='Resource name of a taxonomy store')


def AddTaxonomyResourceFlags(parser):
  """Add taxonomy resource flags to the parser."""
  parser.add_argument(
      '--store_id',
      default=None,
      required=False,
      metavar='store_id',
      help='Id of the taxonomy store. Will use the store associated with the'
      ' organization of the currently active project by default.')
  parser.add_argument(
      'taxonomy_resource',
      metavar='TAXONOMY_RESOURCE',
      nargs='?',
      help='Resource name of a taxonomy')


def GetStoreResourceFromArgs(args):
  """Parse a store resource. Need to call AddStoreResourceFlags first."""
  return resources.REGISTRY.Parse(
      args.store_resource,
      params={
          'taxonomyStoresId':
              args.store_resource
              or store.GetDefaultStoreId(utils.GetProjectRef())
      },
      collection='categorymanager.taxonomyStores')


def GetTaxonomyResourceFromArgs(args):
  """Parse a taxonomy resource. Need to call AddTaxonomyResourceFlags first."""
  return resources.REGISTRY.Parse(
      args.taxonomy_resource,
      params={
          'taxonomyStoresId':
              args.taxonomy_resource or store.GetDefaultStoreId(),
          'taxonomiesId':
              args.taxonomy_id,
      },
      collection='categorymanager.taxonomies')
