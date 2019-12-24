# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Helpers for assets related operations in Cloud Category Manager."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib.category_manager import utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import resources
from googlecloudsdk.core.credentials import http
from googlecloudsdk.core.util import encoding as core_encoding
import six
from six.moves import range  # pylint: disable=redefined-builtin

_MAX_ASSET_LIMIT = 1000000000
_HEADERS = {'Content-Type': 'application/json'}
_DELETE_TAG_NAME_PATTERN = '{}/annotationTag'
_SEARCH_NAME_FORMAT = '{}assets:search?{}'
_HTTP_ERROR_FORMAT = ('HTTP request failed with status code {}. '
                      'Response content: {}')


class MessageDecodeError(core_exceptions.Error):
  """Error raised when a failure to decode a message occurs."""
  pass


def GetHeaders():
  return _HEADERS


def GetHttpErrorFormat():
  return _HTTP_ERROR_FORMAT


def GetDeleteTagNamePattern():
  return _DELETE_TAG_NAME_PATTERN


def ListAssetAnnotationTags(asset_resource):
  """Gets all annotation tags associated with an asset.

  Args:
    asset_resource: A category_manager.assets core.Resource asset object.

  Returns:
    A ListAnnotationTagsResponse message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsAnnotationTagsListRequest(
      name=asset_resource.RelativeName(url_escape=True))
  return utils.GetClientInstance().assets_annotationTags.List(request=req)


def ApplyAnnotationTag(asset_resource, annotation_resource, sub_asset=None):
  """Applies an annotation tag to an asset.

  Args:
    asset_resource: A category_manager.assets core.Resource asset object.
    annotation_resource: A category_manager.taxonomies.annotations
      core.Resource asset object.
    sub_asset: A string representing the asset's sub-asset, if any.

  Returns:
    AnnotationTag response message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsApplyAnnotationTagRequest(
      name=asset_resource.RelativeName(url_escape=True),
      applyAnnotationTagRequest=messages.ApplyAnnotationTagRequest(
          annotation=annotation_resource.RelativeName(), subAsset=sub_asset))
  return utils.GetClientInstance().assets.ApplyAnnotationTag(request=req)


def DeleteAnnotationTag(asset_resource, annotation_resource, sub_asset=None):
  """Delete an annotation tag on an asset.

  Args:
    asset_resource: A category_manager.assets core.Resource asset object.
    annotation_resource: A category_manager.taxonomies.annotations
      core.Resource asset object.
    sub_asset: A string representing the asset's sub-asset, if any.

  Returns:
    DeleteAnnotationTag response message.
  """
  messages = utils.GetMessagesModule()
  # Set url_escape=True because the resource name of the asset must be escaped.
  req = messages.CategorymanagerAssetsDeleteAnnotationTagRequest(
      name=_DELETE_TAG_NAME_PATTERN.format(
          asset_resource.RelativeName(url_escape=True)),
      annotation=annotation_resource.RelativeName(),
      subAsset=sub_asset)
  return utils.GetClientInstance().assets.DeleteAnnotationTag(request=req)


def SearchAssets(annotations, show_only_annotatable, match_child_annotations,
                 query_filter, page_size, limit):
  """Performs backend call to search for assets given a set of constraints.

  Args:
    annotations: Array of annotation strings of the annotations to be looked up.
    show_only_annotatable: A boolean indicating whether or not to exclude
      assets that are not annotatable.
    match_child_annotations: A boolean value which if set to true
    indicates that for any annotation with child annotations, also list assets
      that are annotated by those child annotations.
    query_filter: A filter string that includes additional predicates for assets
    page_size: The request page size.
    limit: The maximum number of assets returned.

  Yields:
    A generator of Asset objects matching the given set of constraints.

  Raises:
    HttpRequestFailError: An HTTP request error if backend call fails.
    MessageDecodeError: An error indicating that the received server payload
      could not be decoded into a valid response.

  Notes:
    This method is doing the HTTP request to search assets manually because the
    generated python apitools API does not support '.' characters in the query
    params, see b/31244944.

    Furthermore, this method does not support multiple retries on failure. The
    issue with implementing retries appears to be that using a generator saves
    the function's state and prevents resetting the generator to enable the
    function to be called again.
  """
  asset_limit = limit or _MAX_ASSET_LIMIT
  # A page size of None will use the default page size set by the server.
  if page_size is not None:
    page_size = min(page_size, asset_limit)

  query_params = [
      ('query.filter', query_filter),  # pylint: disable=ugly-g4-fix-formatting
      ('query.annotatable_only', show_only_annotatable),
      ('query.include_annotated_by_group', match_child_annotations),
      ('pageSize', page_size),
  ]

  for annotation in annotations:
    query_params.append(('query.annotations', annotation))

  # Filter away query params which have not been specified.
  query_params = [(k, v) for k, v in query_params if v is not None]

  base_url = utils.GetClientInstance().BASE_URL + utils.API_VERSION + '/'
  endpoint_base_url = resources.GetApiBaseUrl(utils.API_NAME, utils.API_VERSION)
  # Override the base url if another endpoint is explicitly set.
  if endpoint_base_url is not None:
    base_url = endpoint_base_url

  search_response_class = utils.GetMessagesModule().SearchAssetsResponse

  while asset_limit > 0:
    url = _SEARCH_NAME_FORMAT.format(
        base_url, six.moves.urllib.parse.urlencode(query_params))
    response, raw_content = http.Http().request(uri=url, headers=_HEADERS)
    content = core_encoding.Decode(raw_content)

    status_code = response['status']
    if status_code != '200':
      msg = _HTTP_ERROR_FORMAT.format(status_code, content)
      raise exceptions.HttpException(msg)

    try:
      search_response = encoding.JsonToMessage(search_response_class, content)
    except ValueError as e:
      err_msg = ('Failed receiving proper response from server, cannot'
                 'parse received assets. Error details: ' + str(e))
      raise MessageDecodeError(err_msg)

    for asset in search_response.assets:
      yield asset

    next_token = getattr(search_response, 'nextPageToken', None)
    if next_token is None:
      return
    _AddPageTokenQueryParam(query_params, next_token)

    asset_limit -= len(search_response.assets)


def _AddPageTokenQueryParam(query_params, next_token):
  """Add page token query param or replace previous token."""
  page_token_query_param = ('pageToken', next_token)
  for i in range(len(query_params)):
    query_param, _ = query_params[i]
    if query_param == 'pageToken':
      query_params[i] = page_token_query_param
      return
  query_params.append(page_token_query_param)
