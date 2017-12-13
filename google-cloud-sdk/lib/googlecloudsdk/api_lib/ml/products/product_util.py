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
"""Utilities for gcloud ml products commands."""

import os
import re

from apitools.base.py import encoding
from apitools.base.py import list_pager
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import resources

PRODUCTS_API = 'alpha_vision'
PRODUCTS_SEARCH_VERSION = 'v1'
PRODUCTS_VERSION = 'v1alpha1'

GCS_URI_FORMAT = r'^gs://.+'
PRODUCT_ID_FORMAT = r'^[a-zA-Z0-9_-]+$'
PRODUCT_ID_VALIDATION = ('Product Id is restricted to 255 characters '
                         'including letters, numbers, underscore ( _ ) and '
                         'hyphen (-).')
PRODUCT_ID_VALIDATION_ERROR = ('Invalid product_id [{}]. ' +
                               PRODUCT_ID_VALIDATION)
_GCS_PATH_ERROR_MESSAGE = (
    'The {object} path [{data}] is not a properly formatted URI for a remote '
    '{object}. URI must be a Google Cloud Storage image URI, in '
    'the form `gs://bucket_name/object_name`. Please double-check your input '
    'and try again.')

BOUNDING_POLY_ERROR = ('vertices must be a list of coordinate pairs '
                       'representing the vertices of the bounding polygon '
                       'e.g. [x1:y1, x2:y2, x3:y3,...]. Received [{}]: {}')


def GetApiClient(version=PRODUCTS_VERSION):
  return apis.GetClientInstance(PRODUCTS_API, version)


def GetApiMessages(version=PRODUCTS_VERSION):
  return apis.GetMessagesModule(PRODUCTS_API, version)


class Error(exceptions.Error):
  """Error for gcloud ml product commands."""


class GcsPathError(Error):
  """Error if an fcs path is improperly formatted."""


class ProductIdError(Error):
  """Error if a ReferenceImage product_id is malformed."""


class ProductImportError(Error):
  """Raised if there is an error."""


class InvalidBoundsError(Error):
  """Raised if invalid arguments passed to BuildBoundingPoly."""


class ProductSearchException(Error):
  """Raised if the image product search resulted in an error."""


def GetImageFromPath(path):
  """Builds an Image message from a path.

  Args:
    path: the path arg given to the command.

  Raises:
    ImagePathError: if the image path does not exist and does not seem to be
        a remote URI.

  Returns:
    alpha_vision_v1_messages.Image: an image message containing information
      for the API on the image to analyze.
  """
  messages = GetApiMessages(PRODUCTS_SEARCH_VERSION)
  image = messages.Image()
  if os.path.isfile(path):
    with open(path, 'rb') as content_file:
      image.content = content_file.read()
  elif re.match(GCS_URI_FORMAT, path):
    image.source = messages.ImageSource(imageUri=path)
  else:
    GcsPathError(_GCS_PATH_ERROR_MESSAGE.format(object='image', data=path))
  return image


class ProductsClient(object):
  """Wrapper for the Cloud Alpha_Vision (Product Search) API client classes."""

  def __init__(self):
    self.version = PRODUCTS_VERSION
    self.client = GetApiClient()
    self.messages = GetApiMessages()

    # Add message module and client that are used for interacting
    # with the operations service and search services
    # (requires different version).
    self.search_client = GetApiClient(PRODUCTS_SEARCH_VERSION)
    self.search_messages = GetApiMessages(PRODUCTS_SEARCH_VERSION)
    self._ShortenMessages()

  def _ShortenMessages(self):
    """Shorten variables for convenience/line length."""
    # ReferenceImages
    self.ref_image_msg = self.messages.ReferenceImage
    self.image_category_enum = self.ref_image_msg.CategoryValueValuesEnum
    self.ref_image_create_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsReferenceImagesCreateRequest)
    self.ref_image_delete_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsReferenceImagesDeleteRequest)
    self.ref_image_get_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsReferenceImagesGetRequest)
    self.ref_image_list_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsReferenceImagesListRequest)
    self.ref_image_list_resp = self.messages.ListReferenceImagesResponse
    self.ref_image_service = (self.client.
                              productSearch_catalogs_referenceImages)

    # Catalogs
    self.delete_catalog_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsDeleteRequest)
    self.list_catalogs_msg = (
        self.messages.AlphaVisionProductSearchCatalogsListRequest)
    self.list_catalogs_resp = self.messages.ListCatalogsResponse
    self.delete_catalog_images_msg = (
        self.messages.
        AlphaVisionProductSearchCatalogsDeleteReferenceImagesRequest)
    self.catalog_service = self.client.productSearch_catalogs

    # Catalogs Import
    self.import_catalog_msg = self.messages.ImportCatalogsRequest
    self.import_catalog_resp = self.messages.ImportCatalogsResponse
    self.import_catalog_config = self.messages.ImportCatalogsInputConfig
    self.import_catalog_src = self.messages.ImportCatalogsGcsSource

    # Search
    self.search_request_msg = self.search_messages.AnnotateImageRequest
    self.search_response = self.search_messages.AnnotateImageResponse
    self.search_params_msg = self.search_messages.ProductSearchParams
    self.search_context = self.search_messages.ImageContext
    self.search_results = self.search_messages.ProductSearchResults
    self.search_image_msg = self.search_messages.Image  # Target Image
    self.search_feature_enum = (
        self.search_messages.Feature.TypeValueValuesEnum.PRODUCT_SEARCH)
    self.products_search_service = self.search_client.images  # Annotate

  # Reference Image Management
  def BuildBoundingPoly(self, vertex_list):
    """Builds a BoundingPoly Message for a RefrenceImage.

    Convert list of image coordinates into a BoundingPoly message.

    Args:
      vertex_list: [int:int] - List of string integer pairs representing the
      vertices of the BoundingPoly

    Returns:
      BoundingPoly message

    Raises:
      InvalidBoundsError: vertex_list contains fewer than 3 vertices OR format
        of vertex_list is incorrect.
    """
    if not vertex_list:
      return None
    vertices = []
    if len(vertex_list) < 3:
      raise InvalidBoundsError(
          BOUNDING_POLY_ERROR.format(vertex_list,
                                     'Too few vertices. '
                                     'Must specify at least 3.'))
    try:
      for coord_pair in vertex_list:
        x_coord, y_coord = coord_pair.split(':')
        vertices.append(self.messages.Vertex(x=int(x_coord), y=int(y_coord)))
    except (TypeError, ValueError) as e:
      raise InvalidBoundsError(BOUNDING_POLY_ERROR.format(vertex_list, e))
    if vertices:
      return self.messages.BoundingPoly(vertices=vertices)

    return None

  def _ValidateProductId(self, product_id):
    """Validates ReferenceImage product_id."""
    productid_re = re.compile(PRODUCT_ID_FORMAT)
    return len(product_id) < 256 and productid_re.match(product_id)

  def BuildRefImage(self, product_id, image_path,
                    bounds=None, product_category=None):
    """Build ReferenceImage Message.

    Args:
      product_id: string, A user-defined ID for the product identified by the
        reference image. Restricted to 255 characters matching the regular
        expression `[a-zA-Z0-9_-]+`
      image_path: The Google Cloud Storage URI of the reference image.
      bounds: BoundingPoly message, optional bounding polygon for the image
        annotation. Inferred by the backend service if not provided.
      product_category: string, optional category for the product identified by
        the reference image. Inferred by the backend service if not specified.

    Returns:
      ReferenceImage message

    Raises:
      GcsPathError: if the image path does not exist and does not seem to be
        a remote URI.
      ProductIdError: if the product_id is invalid.
      ValueError: bounds is invalid.
    """
    if product_id and not self._ValidateProductId(product_id):
      raise ProductIdError(PRODUCT_ID_VALIDATION_ERROR.format(
          product_id, PRODUCT_ID_FORMAT))

    if not re.match(GCS_URI_FORMAT, image_path):
      raise GcsPathError(_GCS_PATH_ERROR_MESSAGE.format(object='image',
                                                        data=image_path))

    if bounds and not isinstance(bounds, self.messages.BoundingPoly):
      raise TypeError('bounds must be a valid BoundingPoly message.')

    return self.messages.ReferenceImage(imageUri=image_path,
                                        productCategory=product_category,
                                        productId=product_id,
                                        boundingPoly=bounds)

  def CreateRefImage(self, input_image, catalog_ref):
    """Creates a ReferenceImage in the specified Catalog."""
    image_create_request = self.ref_image_create_msg(
        parent=catalog_ref, referenceImage=input_image)
    return self.ref_image_service.Create(image_create_request)

  def DescribeRefImage(self, image_name):
    """Describe a ReferenceImage."""
    return self.ref_image_service.Get(
        self.ref_image_get_msg(name=image_name))

  def DeleteRefImage(self, image_name):
    """Delete a ReferenceImage."""
    return self.ref_image_service.Delete(
        self.ref_image_delete_msg(name=image_name))

  def ListRefImages(self, catalog_name, product_id=None,
                    page_size=10, limit=None):
    """List all ReferenceImages in a Catalog."""

    return list_pager.YieldFromList(self.ref_image_service,
                                    self.ref_image_list_msg(
                                        parent=catalog_name,
                                        productId=product_id),
                                    field='referenceImages',
                                    limit=limit,
                                    batch_size=page_size,
                                    batch_size_attribute='pageSize')

  # Catalog Management
  def CreateCatalog(self):
    """Create Catalog."""
    return self.catalog_service.Create(self.messages.Catalog())

  def DeleteCatalog(self, catalog_name):
    """Delete a Catalog."""
    self.catalog_service.Delete(self.delete_catalog_msg(name=catalog_name))
    return catalog_name

  def ListCatalogs(self):
    """List all Catalogs."""
    # Alpha API has no paging for catalog list request e.g. page_size and limit
    # not supported
    list_response = self.catalog_service.List(self.list_catalogs_msg())
    return getattr(list_response, 'catalogs', None)

  def DeleteProductCatalogImages(self, catalog_name, product_id):
    """Delete all ReferenceImages for a product from a Catalog."""
    delete_images_req = self.delete_catalog_images_msg(
        parent=catalog_name, productId=product_id)
    return self.catalog_service.DeleteReferenceImages(delete_images_req)

  def ImportCatalog(self, catalog_file_uri):
    """Imports Catalog from CSV file in a GCS Bucket.

    Args:
      catalog_file_uri: string, The Google Cloud Storage URI of the input csv
      file. The format of the input csv file should be one reference image
      per line.

    Returns:
      Response: messages.ImportCatalogsResponse, result of the Import request.

    Raises:
      GcsPathError: If CSV file path is not a valid GCS URI.
    """
    if not re.match(GCS_URI_FORMAT, catalog_file_uri):
      raise GcsPathError(_GCS_PATH_ERROR_MESSAGE.format(
          object='catalog csv file', data=catalog_file_uri))

    import_config = self.import_catalog_config(
        gcsSource=self.import_catalog_src(csvFileUri=catalog_file_uri))
    import_op = self.catalog_service.Import(self.import_catalog_msg(
        inputConfig=import_config))
    operation_ref = resources.REGISTRY.Parse(
        import_op.name,
        collection='alpha_vision.operations')
    op_response = self.WaitOperation(operation_ref)
    import_response = encoding.JsonToMessage(
        self.messages.ImportCatalogsResponse,
        encoding.MessageToJson(op_response))
    return import_response

  # Misc
  def WaitOperation(self, operation_ref):
    """Waits for a long-running operation.

    Args:
      operation_ref: the operation reference.

    Raises:
      waiter.OperationError: if the operation contains an error.

    Returns:
      messages.AnnotateVideoResponse, the final result of the operation.
    """
    message = 'Waiting for operation [{}] to complete'.format(
        operation_ref.RelativeName())
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.search_client.operations,
            # TODO(b/62478975): remove this workaround when operation resources
            # are compatible with gcloud parsing.
            get_name_func=lambda x: x.RelativeName()),
        operation_ref,
        message,
        exponential_sleep_multiplier=2.0,
        sleep_ms=500,
        wait_ceiling_ms=20000)
