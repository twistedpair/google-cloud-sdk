# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Shared utilities for access the CloudAsset API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import exceptions as api_exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.command_lib.asset import utils as asset_utils
from googlecloudsdk.command_lib.util.args import repeated
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.credentials import http
from googlecloudsdk.core.util import encoding as core_encoding
from googlecloudsdk.core.util import times

import six

API_NAME = 'cloudasset'
DEFAULT_API_VERSION = 'v1'
V1P4ALPHA1_API_VERSION = 'v1p4alpha1'
V1P5ALPHA1_API_VERSION = 'v1p5alpha1'
BASE_URL = 'https://cloudasset.googleapis.com'
_HEADERS = {'Content-Type': 'application/json', 'X-HTTP-Method-Override': 'GET'}
_HTTP_ERROR_FORMAT = ('HTTP request failed with status code {}. '
                      'Response content: {}')


class MessageDecodeError(core_exceptions.Error):
  """Error raised when a failure to decode a message occurs."""


def GetMessages(version=DEFAULT_API_VERSION):
  """Import and return the cloudasset messages module.

  Args:
    version: the API version

  Returns:
    cloudasset message module.
  """
  return apis.GetMessagesModule(API_NAME, version)


def GetClient(version=DEFAULT_API_VERSION):
  """Import and return the cloudasset client module.

  Args:
    version: the API version

  Returns:
    cloudasset API client module.
  """
  return apis.GetClientInstance(API_NAME, version)


def ContentTypeTranslation(content_type):
  if content_type == 'resource':
    return 'RESOURCE'
  if content_type == 'iam-policy':
    return 'IAM_POLICY'
  if content_type == 'org-policy':
    return 'ORG_POLICY'
  if content_type == 'access-policy':
    return 'ACCESS_POLICY'
  return 'CONTENT_TYPE_UNSPECIFIED'


def MakeGetAssetsHistoryHttpRequests(args, api_version=DEFAULT_API_VERSION):
  """Manually make the get assets history request."""
  http_client = http.Http()
  query_params = [
      ('assetNames', asset_name) for asset_name in args.asset_names or []
  ]
  query_params.extend([('contentType',
                        ContentTypeTranslation(args.content_type)),
                       ('readTimeWindow.startTime',
                        times.FormatDateTime(args.start_time))])
  if args.IsSpecified('end_time'):
    query_params.extend([('readTimeWindow.endTime',
                          times.FormatDateTime(args.end_time))])
  parent = asset_utils.GetParentNameForGetHistory(args.organization,
                                                  args.project)
  url_base = '{0}/{1}/{2}:{3}'.format(BASE_URL, api_version, parent,
                                      'batchGetAssetsHistory')
  url_query = six.moves.urllib.parse.urlencode(query_params)
  url = '?'.join([url_base, url_query])
  response, raw_content = http_client.request(uri=url, headers=_HEADERS)

  content = core_encoding.Decode(raw_content)

  if response['status'] != '200':
    http_error = api_exceptions.HttpError(response, content, url)
    raise exceptions.HttpException(http_error)

  response_message_class = GetMessages(
      api_version).BatchGetAssetsHistoryResponse
  try:
    history_response = encoding.JsonToMessage(response_message_class, content)
  except ValueError as e:
    err_msg = ('Failed receiving proper response from server, cannot'
               'parse received assets. Error details: ' + six.text_type(e))
    raise MessageDecodeError(err_msg)

  for asset in history_response.assets:
    yield asset


def MakeAnalyzeIamPolicyHttpRequests(args, api_version=V1P4ALPHA1_API_VERSION):
  """Manually make the get assets history request."""
  http_client = http.Http()

  parent = asset_utils.GetParentNameForAnalyzeIamPolicy(args.organization)
  url_base = '{0}/{1}/{2}:{3}'.format(BASE_URL, api_version, parent,
                                      'analyzeIamPolicy')

  params = []
  if args.IsSpecified('full_resource_name'):
    params.extend([('resourceSelector.fullResourceName',
                    args.full_resource_name)])

  if args.IsSpecified('identity'):
    params.extend([('identitySelector.identity', args.identity)])

  if args.IsSpecified('roles'):
    params.extend([('accessSelector.roles', r) for r in args.roles])
  if args.IsSpecified('permissions'):
    params.extend([('accessSelector.permissions', p) for p in args.permissions])

  if args.IsSpecified('expand_groups'):
    params.extend([('options.expandGroups', args.expand_groups)])
  if args.IsSpecified('expand_resources'):
    params.extend([('options.expandResources', args.expand_resources)])
  if args.IsSpecified('expand_roles'):
    params.extend([('options.expandRoles', args.expand_roles)])

  if args.IsSpecified('output_resource_edges'):
    params.extend([('options.outputResourceEdges', args.output_resource_edges)])
  if args.IsSpecified('output_group_edges'):
    params.extend([('options.outputGroupEdges', args.output_group_edges)])
  if args.IsSpecified('output_partial_result_before_timeout'):
    params.extend([('options.outputPartialResultBeforeTimeout',
                    args.output_partial_result_before_timeout)])

  url_query = six.moves.urllib.parse.urlencode(params)
  url = '?'.join([url_base, url_query])
  response, raw_content = http_client.request(uri=url, headers=_HEADERS)

  content = core_encoding.Decode(raw_content)

  if response['status'] != '200':
    http_error = api_exceptions.HttpError(response, content, url)
    raise exceptions.HttpException(http_error)

  response_message_class = GetMessages(api_version).AnalyzeIamPolicyResponse
  try:
    response = encoding.JsonToMessage(response_message_class, content)
  except ValueError as e:
    err_msg = ('Failed receiving proper response from server, cannot'
               'parse received assets. Error details: ' + six.text_type(e))
    raise MessageDecodeError(err_msg)

  return response


class AssetExportClient(object):
  """Client for export asset."""

  def __init__(self, parent, api_version=DEFAULT_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).v1

  def Export(self, args):
    """Export assets with the asset export method."""
    content_type = ContentTypeTranslation(args.content_type)
    content_type = getattr(
        self.message_module.ExportAssetsRequest.ContentTypeValueValuesEnum,
        content_type)
    if args.output_path or args.output_path_prefix:
      output_config = self.message_module.OutputConfig(
          gcsDestination=self.message_module.GcsDestination(
              uri=args.output_path, uriPrefix=args.output_path_prefix))
    else:
      source_ref = args.CONCEPTS.bigquery_table.Parse()
      output_config = self.message_module.OutputConfig(
          bigqueryDestination=self.message_module.BigQueryDestination(
              dataset='projects/' + source_ref.projectId + '/datasets/' +
              source_ref.datasetId,
              table=source_ref.tableId,
              force=args.force_))
    snapshot_time = None
    if args.snapshot_time:
      snapshot_time = times.FormatDateTime(args.snapshot_time)
    export_assets_request = self.message_module.ExportAssetsRequest(
        assetTypes=args.asset_types,
        contentType=content_type,
        outputConfig=output_config,
        readTime=snapshot_time)
    request_message = self.message_module.CloudassetExportAssetsRequest(
        parent=self.parent, exportAssetsRequest=export_assets_request)
    operation = self.service.ExportAssets(request_message)
    return operation


class AssetFeedClient(object):
  """Client for asset feed."""

  def __init__(self, parent, api_version=DEFAULT_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).feeds

  def Create(self, args):
    """Create a feed."""
    content_type = ContentTypeTranslation(args.content_type)
    content_type = getattr(self.message_module.Feed.ContentTypeValueValuesEnum,
                           content_type)
    feed_output_config = self.message_module.FeedOutputConfig(
        pubsubDestination=self.message_module.PubsubDestination(
            topic=args.pubsub_topic))
    feed = self.message_module.Feed(
        assetNames=args.asset_names,
        assetTypes=args.asset_types,
        contentType=content_type,
        feedOutputConfig=feed_output_config)
    create_feed_request = self.message_module.CreateFeedRequest(
        feed=feed, feedId=args.feed)
    request_message = self.message_module.CloudassetFeedsCreateRequest(
        parent=self.parent, createFeedRequest=create_feed_request)
    return self.service.Create(request_message)

  def Describe(self, args):
    """Describe a feed."""
    request_message = self.message_module.CloudassetFeedsGetRequest(
        name='{}/feeds/{}'.format(self.parent, args.feed))
    return self.service.Get(request_message)

  def Delete(self, args):
    """Delete a feed."""
    request_message = self.message_module.CloudassetFeedsDeleteRequest(
        name='{}/feeds/{}'.format(self.parent, args.feed))
    self.service.Delete(request_message)

  def List(self):
    """List feeds under a parent."""
    request_message = self.message_module.CloudassetFeedsListRequest(
        parent=self.parent)
    return self.service.List(request_message)

  def Update(self, args):
    """Update a feed."""
    update_masks = []
    content_type = ContentTypeTranslation(args.content_type)
    content_type = getattr(self.message_module.Feed.ContentTypeValueValuesEnum,
                           content_type)
    feed_name = '{}/feeds/{}'.format(self.parent, args.feed)
    if args.content_type or args.clear_content_type:
      update_masks.append('content_type')
    if args.pubsub_topic:
      update_masks.append('feed_output_config.pubsub_destination.topic')
    asset_names, asset_types = self.UpdateAssetNamesAndTypes(
        args, feed_name, update_masks)
    update_mask = ','.join(update_masks)
    feed_output_config = self.message_module.FeedOutputConfig(
        pubsubDestination=self.message_module.PubsubDestination(
            topic=args.pubsub_topic))
    feed = self.message_module.Feed(
        assetNames=asset_names,
        assetTypes=asset_types,
        contentType=content_type,
        feedOutputConfig=feed_output_config)
    update_feed_request = self.message_module.UpdateFeedRequest(
        feed=feed, updateMask=update_mask)
    request_message = self.message_module.CloudassetFeedsPatchRequest(
        name=feed_name, updateFeedRequest=update_feed_request)
    return self.service.Patch(request_message)

  def UpdateAssetNamesAndTypes(self, args, feed_name, update_masks):
    """Get Updated assetNames and assetTypes."""
    feed = self.service.Get(
        self.message_module.CloudassetFeedsGetRequest(name=feed_name))
    asset_names = repeated.ParsePrimitiveArgs(args, 'asset_names',
                                              lambda: feed.assetNames)
    if asset_names is not None:
      update_masks.append('asset_names')
    else:
      asset_names = []
    asset_types = repeated.ParsePrimitiveArgs(args, 'asset_types',
                                              lambda: feed.assetTypes)
    if asset_types is not None:
      update_masks.append('asset_types')
    else:
      asset_types = []
    return asset_names, asset_types


class AssetListClient(object):
  """Client for list assets."""

  def __init__(self, parent, api_version=V1P5ALPHA1_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).assets

  def List(self, args):
    """List assets with the asset list method."""
    snapshot_time = None
    if args.snapshot_time:
      snapshot_time = times.FormatDateTime(args.snapshot_time)
    content_type = ContentTypeTranslation(args.content_type)
    list_assets_request = self.message_module.CloudassetAssetsListRequest(
        parent=self.parent,
        contentType=getattr(
            self.message_module.CloudassetAssetsListRequest
            .ContentTypeValueValuesEnum, content_type),
        assetTypes=args.asset_types,
        readTime=snapshot_time)
    return list_pager.YieldFromList(
        self.service,
        list_assets_request,
        field='assets',
        limit=args.limit,
        batch_size=args.page_size,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')


class AssetOperationClient(object):
  """Client for operations."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.service = GetClient(api_version).operations
    self.message = GetMessages(api_version).CloudassetOperationsGetRequest

  def Get(self, name):
    request = self.message(name=name)
    return self.service.Get(request)
