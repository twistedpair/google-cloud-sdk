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

"""Flags for ml products commands."""
from googlecloudsdk.api_lib.ml.products import product_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import resources


# Resource Args
def CatalogAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='catalog',
      help_text='The catalog of the {resource}.')


def ReferenceImageAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='reference_image',
      help_text='The reference-image of the {resource}.')


def GetCatalogResourceSpec():
  return concepts.ResourceSpec(
      'alpha_vision.productSearch.catalogs',
      resource_name='catalog',
      api_version='v1alpha1',
      catalogsId=CatalogAttributeConfig())


def GetReferenceImageResourceSpec():
  return concepts.ResourceSpec(
      'alpha_vision.productSearch.catalogs.referenceImages',
      resource_name='referenceImage',
      api_version='v1alpha1',
      catalogsId=CatalogAttributeConfig(),
      referenceImagesId=ReferenceImageAttributeConfig())


def AddCatalogResourceArg(parser, verb, positional=True, required=True):
  """Add a resource argument for a cloud productsearch image catalog.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the catalog ID is a positional rather
      than a flag.
    required: bool, if True then this resource arg will be required argument
  """
  if positional:
    name = 'catalog'
  else:
    name = '--catalog'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetCatalogResourceSpec(),
      'The catalog {}.'.format(verb),
      required=required).AddToParser(parser)


def AddReferenceImageResourceArg(parser, verb, positional=True, required=True):
  """Add a resource argument for a cloud productsearch reference images.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the referenceimage ID is a positional
      rather than a flag.
    required: bool, if True then this resource arg will be required argument
  """
  if positional:
    name = 'reference_image'
  else:
    name = '--reference-image'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetReferenceImageResourceSpec(),
      'The reference-image {}.'.format(verb),
      required=required).AddToParser(parser)


# Other Args
def AddCatalogImportSourceArg(parser):
  """Import Catalog from CSV File stored in GCS."""
  catalog_id = base.Argument(
      'source',
      help=('The Google Cloud Storage URI of the input CSV file for the '
            'catalog. The URI must start with gs://.'))
  catalog_id.AddToParser(parser)


def AddProductIdFlag(parser, verb, required=False):
  """ReferenceImage Product ID Flag."""
  base.Argument(
      '--product-id',
      help=('The product ID {verb}. {msg}'.format(
          verb=verb, msg=product_util.PRODUCT_ID_VALIDATION)),
      type=arg_parsers.RegexpValidator(product_util.PRODUCT_ID_FORMAT,
                                       product_util.PRODUCT_ID_VALIDATION),
      required=required
  ).AddToParser(parser)


# Image Creation flags: gcs path,
def AddImagePathFlag(parser):
  """ReferenceImage Image Path Flag."""
  base.Argument(
      'image_path',
      help=('The Google Cloud Storage URI of the input image file. '
            'The URI must start with gs://.'),
      type=arg_parsers.RegexpValidator(product_util.GCS_URI_FORMAT,
                                       'Invalid Google Cloud Storage '
                                       'image path.')
  ).AddToParser(parser)


def AddCategoryAndBoundsFlags(parser, verb):
  """Add ArgumentGroup for ReferenceImage category and bounds."""
  cb_group = parser.add_group(
      help=('Both `--category` and `--bounds` should be specified if '
            'either is provided.'))
  cb_group.add_argument(
      '--bounds',
      metavar='x:y',
      help=('A set of vertices defining the bounding polygon around'
            'the area of interest in the image. Should be a list of integer '
            'pairs, separated by commas specifying the vertices '
            '(e.g. [x1:y2, x2:y2,x3:y3...xn:yn]). Defaults to full image '
            'if empty.'),
      type=arg_parsers.ArgList(min_length=3))
  cb_group.add_argument(
      '--category',
      help='String specifying the product category {verb}.'.format(verb=verb))


def AddReferenceImageCreateFlags(parser):
  """Add Reference Image create command flags to parser."""
  AddImagePathFlag(parser)
  AddCatalogResourceArg(parser, verb='to add ReferenceImages to',
                        positional=False)
  AddProductIdFlag(parser, verb='to associate this ReferenceImage to',
                   required=True)
  AddCategoryAndBoundsFlags(parser, verb='to associate this ReferenceImage to')


def VertexType(value):
  """Builds NormalizedVertex messages from command line args."""
  messages = product_util.GetApiMessages(
      version=product_util.PRODUCTS_SEARCH_VERSION)
  x_coord, y_coord = map(int, value.split(':'))
  return messages.NormalizedVertex(x=x_coord, y=y_coord)


def CatalogNameType(value):
  """Returns CatalogName for a given Value."""
  registry = resources.REGISTRY.Clone()
  registry.RegisterApiByName('alpha_vision', 'v1alpha1')
  catalog_ref = registry.Parse(
      value, params=None, collection='alpha_vision.productSearch.catalogs')
  return catalog_ref.RelativeName()
